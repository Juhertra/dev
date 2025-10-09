.PHONY: install lint type test unit contracts docs health quick-test eod _eod_local_coverage

install:
	pip install -r requirements.txt || poetry install --no-root

lint:
	ruff check --fix .

type:
	pyright --warnings

unit:
	pytest -q --maxfail=1

coverage:
	pytest -q --cov=. --cov-report=term-missing

test: type unit

# placeholder; wired in P5
docs:
	mkdocs build -q || true

# placeholder; wired in P5
health:
	python scripts/mermaid_parity_gate.py && python scripts/ascii_html_blocker_gate.py

quick-test:
	pytest -q -k 'not slow'

eod:
	@./scripts/eod_report.sh

# Fallback coverage target used by the script (local; read-only)
_eod_local_coverage:
	@command -v poetry >/dev/null 2>&1 && poetry run pytest -q --cov=. --cov-report=term \
	 || (command -v pytest >/dev/null 2>&1 && python -c "import pytest_cov" 2>/dev/null && pytest -q --cov=. --cov-report=term \
	 || echo "Coverage not available (pytest-cov not installed)")