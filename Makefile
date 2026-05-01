PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: install test lint fmt typecheck backtest-demo clean

$(VENV)/bin/activate:
	$(PY) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip wheel
	$(BIN)/pip install -e ".[dev]"

install: $(VENV)/bin/activate ## install package + dev deps in venv

test: ## run pytest
	$(BIN)/pytest -q

lint: ## ruff check + format check
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

fmt: ## auto-format
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

typecheck: ## mypy strict
	$(BIN)/mypy src/

backtest-demo: ## run sma_cross backtest on bundled fixture
	$(BIN)/python -m daytrade_ai.cli backtest --strategy sma_cross --csv tests/fixtures/btc_sample.csv

clean:
	rm -rf $(VENV) build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
