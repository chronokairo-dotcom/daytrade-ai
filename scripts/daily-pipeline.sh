#!/usr/bin/env bash
set -euo pipefail
# daytrade-ai daily pipeline
# Orchestrates: data fetch → analysis → report → fix → commit → push

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Config
LACIELS="node /tmp/chronokairo-multiagente/bin/laciels.mjs"
LOG="$ROOT/logs/daily-pipeline.log"
mkdir -p "$ROOT/logs" "$ROOT/reports"

# Load secrets
OPENROUTER_ENV="${OPENROUTER_ENV:-/root/.openclaw/workspace/secrets/openrouter.env}"
if [ -f "$OPENROUTER_ENV" ]; then
  set -a
  . "$OPENROUTER_ENV"
  set +a
fi

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
die() { log "FATAL: $*"; exit 1; }

# ── Step 0: Ensure venv ──────────────────────────────────────────────
if [ ! -f .venv/bin/python ]; then
  log "creating venv..."
  python3 -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip wheel
  .venv/bin/pip install --quiet -e ".[dev]"
fi
VENV_PYTHON="$ROOT/.venv/bin/python"
VENV_PIP="$ROOT/.venv/bin/pip"

# ── Step 1: Pull latest ──────────────────────────────────────────────
log "=== Step 1: git pull ==="
git fetch origin main 2>&1 | tee -a "$LOG"
git reset --hard origin/main 2>&1 | tee -a "$LOG"
git clean -fd 2>&1 | tee -a "$LOG" || true

# ── Step 2: Run quality gates ────────────────────────────────────────
log "=== Step 2: Quality gates ==="
lint_ok=false; typecheck_ok=false; test_ok=false

if .venv/bin/ruff check . --quiet && .venv/bin/ruff format --check . --quiet; then
  lint_ok=true; log "  lint: OK"
else
  log "  lint: FAIL -- attempting auto-fix"
  .venv/bin/ruff format . 2>&1 | tee -a "$LOG"
  .venv/bin/ruff check --fix . 2>&1 | tee -a "$LOG" || true
fi

if .venv/bin/mypy src/ --no-error-summary 2>&1 | tee -a "$LOG"; then
  typecheck_ok=true; log "  typecheck: OK"
else
  log "  typecheck: FAIL"
fi

if .venv/bin/python -m pytest -q --tb=short 2>&1 | tee -a "$LOG"; then
  test_ok=true; log "  test: OK"
else
  log "  test: FAIL"
fi

# ── Step 3: GitHub research — buscar melhores soluções ──────────────────
log "=== Step 3: GitHub research ==="
RESEARCH_LOG="$ROOT/reports/daily-research.md"
echo "# daily-research $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RESEARCH_LOG"
echo "" >> "$RESEARCH_LOG"

# 3a — Check repo's own open issues
log "  checking repository issues..."
ISSUES=$(gh issue list --repo chronokairo-dotcom/daytrade-ai --state open --json number,title,labels --limit 20 2>/dev/null || echo "[]")
echo "## Open issues on repo" >> "$RESEARCH_LOG"
echo "$ISSUES" | python3 -c "
import sys, json
try:
    items = json.load(sys.stdin)
    if items:
        for i in items:
            labels = ', '.join([l['name'] for l in i.get('labels', [])]) if i.get('labels') else 'none'
            print(f'- #{i[\"number\"]} {i[\"title\"]} [{labels}]')
    else:
        print('- No open issues')
except:
    print('- Could not parse issues')
" >> "$RESEARCH_LOG" 2>/dev/null
echo "" >> "$RESEARCH_LOG"

# 3b — Search GitHub for relevant projects (trending trading bots)
log "  searching GitHub for trading bot improvements..."
for query in "python backtest framework best practices 2026" "trading bot paper trading github stars:>100" "python trading strategy optimizer"; do
  log "    searching: $query"
  echo "### Search: $query" >> "$RESEARCH_LOG"
  gh search repos "$query" --limit 5 --json fullName,description,stars,url,updatedAt 2>/dev/null | python3 -c "
import sys, json
try:
    items = json.load(sys.stdin)
    if items:
        for r in items:
            desc = (r.get('description') or '')[:120]
            print(f'- [{r[\"fullName\"]}]({r[\"url\"]}) ★{r.get(\"stars\",0)} — {desc}')
    else:
        print('- No results')
    print('')
except Exception as e:
    print(f'- Error: {e}')
" >> "$RESEARCH_LOG" 2>/dev/null || echo "  - search failed" >> "$RESEARCH_LOG"
done

# 3c — Check if repo has actions/workflow issues
log "  checking CI status..."
gh run list --repo chronokairo-dotcom/daytrade-ai --limit 5 --json conclusion,headBranch,createdAt,workflowName 2>/dev/null | python3 -c "
import sys, json
try:
    items = json.load(sys.stdin)
    if items:
        for r in items:
            print(f'- {r.get(\"workflowName\",\"?\")}: {r.get(\"conclusion\",\"?\")} ({r.get(\"headBranch\",\"?\")})')
    else:
        print('- No workflow runs found')
except:
    print('- Could not parse CI status')
" >> "$RESEARCH_LOG" 2>/dev/null || echo "  - CI check failed" >> "$RESEARCH_LOG"
echo "" >> "$RESEARCH_LOG"
log "  research log saved to $RESEARCH_LOG"

# ── Step 4: Fetch fresh data ─────────────────────────────────────────
log "=== Step 4: Fetch market data ==="
for symbol in BTC/USDT ETH/USDT SOL/USDT; do
  log "  fetching $symbol 1h..."
  $VENV_PYTHON -m daytrade_ai.cli fetch-data \
    --symbol "$symbol" --timeframe 1h --since 2023-01-01 \
    2>&1 | tee -a "$LOG" || log "  [warn] fetch failed for $symbol"
done

# ── Step 5: Pattern analysis ─────────────────────────────────────────
log "=== Step 5: Pattern analysis ==="
$VENV_PYTHON scripts/pattern_service.py --once \
  --symbol BTC/USDT --symbol ETH/USDT --symbol SOL/USDT \
  --timeframe 1h --lookback-bars 720 \
  2>&1 | tee -a "$LOG" || log "  [warn] pattern service had errors"

# ── Step 6: Backtest + walk-forward ──────────────────────────────────
log "=== Step 6: Backtest & walk-forward ==="
$VENV_PYTHON scripts/run_realdata_analysis.py \
  2>&1 | tee -a "$LOG" || log "  [warn] backtest analysis had errors"

# ── Step 7: Build morning report ─────────────────────────────────────
log "=== Step 7: Morning report ==="
$VENV_PYTHON scripts/build_morning_report.py \
  2>&1 | tee -a "$LOG" || log "  [warn] morning report had errors"

# ── Step 8: AI-powered fixes ─────────────────────────────────────────
log "=== Step 8: AI-driven fixes ==="
FIXES_LOG="$ROOT/reports/daily-fixes.log"
echo "# daily-fixes $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$FIXES_LOG"

fix_with_laciels() {
  local scenario="$1"
  local title="$2"
  local prompt="$3"
  log "  fixing $title ($scenario)..."
  echo "" >> "$FIXES_LOG"
  echo "## $title" >> "$FIXES_LOG"
  $LACIELS run "$scenario" "$prompt" 2>&1 | tee -a "$LOG" | tail -5 >> "$FIXES_LOG" || {
    log "  [warn] laciels failed for: $title"
    echo "  → FAILED" >> "$FIXES_LOG"
  }
}

# Fix lint issues if still failing
if [ "$lint_ok" = false ]; then
  fix_with_laciels small-fix \
    "Fix ruff lint errors" \
    "Fix all ruff lint errors in /root/.openclaw/workspace/daytrade-ai. Run 'ruff check .' and fix all issues. Keep fixes minimal and idiomatic."
fi

# Fix typecheck issues if failing
if [ "$typecheck_ok" = false ]; then
  fix_with_laciels small-fix \
    "Fix mypy type errors" \
    "Fix all mypy --strict type errors in /root/.openclaw/workspace/daytrade-ai/src/. Run 'mypy src/' and fix all issues found. Add type annotations where missing."
fi

# Fix test issues if failing
if [ "$test_ok" = false ]; then
  fix_with_laciels small-fix \
    "Fix failing tests" \
    "Fix failing pytest tests in /root/.openclaw/workspace/daytrade-ai/tests/. Run 'pytest -q --tb=long' and fix all failures."
fi

# Fix P0/P1 items from morning report
MORNING_REPORT="$ROOT/reports/morning-report.md"
if [ -f "$MORNING_REPORT" ]; then
  if grep -q "P0" "$MORNING_REPORT" 2>/dev/null; then
    log "  P0 items found — implementing fixes via laciels..."
    P0_TEXT=$(grep -A5 "P0" "$MORNING_REPORT" | head -30)
    fix_with_laciels spec-implementation \
      "Implement P0 fixes from morning report" \
      "The daytrade-ai project at /root/.openclaw/workspace/daytrade-ai has these critical (P0) issues from its morning report:

$P0_TEXT

Implement fixes for each P0 issue. Follow the project's existing code patterns. Run 'make lint && make typecheck && make test' to verify after changes."
  fi
fi

# ── Step 9: Re-run quality gates after fixes ─────────────────────────
log "=== Step 9: Validate fixes ==="
.venv/bin/ruff check . --quiet && .venv/bin/ruff format --check . --quiet && log "  lint post-fix: OK" || log "  lint post-fix: FAIL"
.venv/bin/python -m pytest -q --tb=short 2>&1 | tee -a "$LOG" && log "  test post-fix: OK" || log "  test post-fix: FAIL"

# ── Step 10: Commit & push ──────────────────────────────────────────
log "=== Step 10: Commit & push ==="
if git diff --quiet && git diff --cached --quiet && test -z "$(git ls-files --others --exclude-standard)"; then
  log "  nothing to commit — pipeline finished clean"
else
  git add -A 2>&1 | tee -a "$LOG"
  git commit -m "chore(daily): auto-pipeline $(date -u +%Y-%m-%d)" \
    -m "Automated daily pipeline. GitHub research, data fetch, analysis, morning report, AI-driven fixes." \
    2>&1 | tee -a "$LOG" || true
  git push origin main 2>&1 | tee -a "$LOG" || {
    log "  [warn] push failed, retrying after pull..."
    git pull --rebase origin main 2>&1 | tee -a "$LOG"
    git push origin main 2>&1 | tee -a "$LOG" || die "push failed after retry"
  }
  log "  commit + push done"
fi

log "=== Pipeline complete ==="
