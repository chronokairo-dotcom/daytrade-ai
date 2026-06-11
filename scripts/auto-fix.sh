#!/usr/bin/env bash
set -euo pipefail
# Auto-fix: reads morning report, fixes open items, validates, commits.
# Designed to run standalone (e.g. cron after main pipeline).

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LACIELS="node /tmp/chronokairo-multiagente/bin/laciels.mjs"
LOG="$ROOT/logs/auto-fix.log"
mkdir -p "$ROOT/logs"

# Load secrets
OPENROUTER_ENV="${OPENROUTER_ENV:-/root/.openclaw/workspace/secrets/openrouter.env}"
if [ -f "$OPENROUTER_ENV" ]; then
  set -a
  . "$OPENROUTER_ENV"
  set +a
fi

log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }
die() { log "FATAL: $*"; exit 1; }

VENV_PYTHON="$ROOT/.venv/bin/python"

# ── Step 0: Ensure venv ──────────────────────────────────────────────
if [ ! -f "$VENV_PYTHON" ]; then
  log "creating venv..."
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install --quiet --upgrade pip wheel
  "$ROOT/.venv/bin/pip" install --quiet -e ".[dev]"
fi

# ── Step 1: Quality gates ────────────────────────────────────────────
log "=== Step 1: Quality gates ==="
lint_ok=false; typecheck_ok=false; test_ok=false

if "$VENV_PYTHON" -m ruff check . --quiet && "$VENV_PYTHON" -m ruff format --check . --quiet 2>/dev/null; then
  lint_ok=true; log "  lint: OK"
else
  log "  lint: FAIL"
fi

if "$VENV_PYTHON" -m mypy src/ --no-error-summary 2>/dev/null; then
  typecheck_ok=true; log "  typecheck: OK"
else
  log "  typecheck: FAIL"
fi

if "$VENV_PYTHON" -m pytest -q --tb=short 2>/dev/null; then
  test_ok=true; log "  test: OK"
else
  log "  test: FAIL"
fi

# ── Step 2: Fix quality gate failures ────────────────────────────────
log "=== Step 2: Fix quality gate failures ==="

fix_with_laciels() {
  local scenario="$1"
  local title="$2"
  local prompt="$3"
  log "  fixing $title ($scenario)..."
  $LACIELS run "$scenario" "$prompt" 2>&1 | tee -a "$LOG" || {
    log "  [warn] laciels failed for: $title"
    return 1
  }
}

if [ "$lint_ok" = false ]; then
  log "  fixing lint..."
  fix_with_laciels small-fix \
    "Fix ruff lint errors" \
    "Fix all ruff lint errors in $ROOT. Run 'ruff check .' and fix all issues. Keep fixes minimal and idiomatic." || true
  if "$VENV_PYTHON" -m ruff check . --quiet && "$VENV_PYTHON" -m ruff format --check . --quiet 2>/dev/null; then
    lint_ok=true; log "  lint: fixed"
  else
    log "  lint: still failing after fix"
  fi
fi

if [ "$typecheck_ok" = false ]; then
  log "  fixing typecheck..."
  fix_with_laciels small-fix \
    "Fix mypy type errors" \
    "Fix all mypy type errors in $ROOT/src/. Run 'mypy src/' and fix all issues found. Add type annotations where missing." || true
  if "$VENV_PYTHON" -m mypy src/ --no-error-summary 2>/dev/null; then
    typecheck_ok=true; log "  typecheck: fixed"
  else
    log "  typecheck: still failing after fix"
  fi
fi

if [ "$test_ok" = false ]; then
  log "  fixing tests..."
  fix_with_laciels test-authoring \
    "Fix failing tests" \
    "Fix failing pytest tests in $ROOT/tests/. Run 'pytest -q --tb=long' and fix all failures. Do not delete or skip tests." || true
  if "$VENV_PYTHON" -m pytest -q --tb=short 2>/dev/null; then
    test_ok=true; log "  test: fixed"
  else
    log "  test: still failing after fix"
  fi
fi

# ── Step 3: Read morning report for open items ───────────────────────
log "=== Step 3: Parse morning report ==="

# Use Python to extract open items (❌ Open) with their titles
OPEN_ITEMS=$("$VENV_PYTHON" -c "
import re, sys
from pathlib import Path

report = Path('$ROOT/reports/morning-report.md')
if not report.exists():
    sys.exit(0)

text = report.read_text()

# Extract all items with priority, title, and status
# Pattern: ### 🔴 P0 — Title [✅ Fixed] or ### 🔴 P0 — Title [❌ Open]
items = []
for line in text.splitlines():
    m = re.match(r'^### (🔴.*?|🟡.*?|🟢.*?) — (.+?) \[(.+?)\]$', line)
    if m:
        prio_tag = m.group(1)
        title = m.group(2)
        status = m.group(3)
        if status == '❌ Open':
            # Determine priority level
            if 'P0' in prio_tag:
                prio = 'P0'
            elif 'P1' in prio_tag:
                prio = 'P1'
            else:
                prio = 'P2'
            items.append((prio, title))

if not items:
    print('ALL_FIXED')
else:
    for prio, title in items:
        print(f'{prio}|{title}')
" 2>/dev/null) || OPEN_ITEMS="ALL_FIXED"

if [ "$OPEN_ITEMS" = "ALL_FIXED" ]; then
  log "  no open items — all ✅ Fixed"
elif [ -z "$OPEN_ITEMS" ]; then
  log "  no morning report found or empty"
else
  log "  open items found:"
  echo "$OPEN_ITEMS" | while IFS='|' read -r prio title; do
    log "    [$prio] $title"
  done

  # ── Step 4: Fix open items ──────────────────────────────────────────
  log "=== Step 4: Fix open report items ==="

  echo "$OPEN_ITEMS" | while IFS='|' read -r prio title; do
    log "  fixing [$prio] $title..."

    case "$prio" in
      P0)
        scenario="spec-implementation"
        ;;
      P1)
        scenario="codegen"
        ;;
      P2)
        scenario="codegen"
        ;;
    esac

    # Get the full item context from the morning report for the prompt
    CONTEXT=$("$VENV_PYTHON" -c "
import sys
from pathlib import Path
report = Path('$ROOT/reports/morning-report.md')
text = report.read_text()
lines = text.splitlines()
target = '$title'
capture = False
out = []
for line in lines:
    if target in line and ('P0' in line or 'P1' in line or 'P2' in line):
        capture = True
    if capture:
        out.append(line)
        if line.strip() == '' and len(out) > 10:
            break
print('\n'.join(out))
" 2>/dev/null)

    fix_with_laciels "$scenario" \
      "[$prio] $title" \
      "The daytrade-ai project at $ROOT has this open issue:

$CONTEXT

Implement the fix described in 'Change.' section. Follow the project's existing code patterns. Run 'make lint && make typecheck && make test' to verify after changes." || true
  done
fi

# ── Step 5: Re-run quality gates ─────────────────────────────────────
log "=== Step 5: Validate fixes ==="
if "$VENV_PYTHON" -m ruff check . --quiet && "$VENV_PYTHON" -m ruff format --check . --quiet 2>/dev/null; then
  log "  lint post-fix: OK"
else
  log "  lint post-fix: FAIL"
fi

if "$VENV_PYTHON" -m pytest -q --tb=short 2>/dev/null; then
  log "  test post-fix: OK"
else
  log "  test post-fix: FAIL"
fi

# ── Step 6: Rebuild morning report ───────────────────────────────────
log "=== Step 6: Rebuild morning report ==="
if "$VENV_PYTHON" scripts/build_morning_report.py 2>&1 | tee -a "$LOG"; then
  log "  morning report rebuilt"
else
  log "  [warn] morning report rebuild failed"
fi

# ── Step 7: Commit & push ───────────────────────────────────────────
log "=== Step 7: Commit & push ==="
if git diff --quiet && git diff --cached --quiet && test -z "$(git ls-files --others --exclude-standard)"; then
  log "  nothing to commit — all clean"
else
  git add -A 2>&1 | tee -a "$LOG"
  git commit -m "chore(auto-fix): $(date -u +%Y-%m-%d)" \
    -m "Automated fixes from auto-fix cron. Quality gates + open morning report items." \
    2>&1 | tee -a "$LOG" || true
  git push origin main 2>&1 | tee -a "$LOG" || {
    log "  [warn] push failed, retrying after pull..."
    git pull --rebase origin main 2>&1 | tee -a "$LOG"
    git push origin main 2>&1 | tee -a "$LOG" || die "push failed after retry"
  }
  log "  commit + push done"
fi

log "=== Auto-fix complete ==="
