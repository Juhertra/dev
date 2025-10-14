.PHONY: install lint type imports test unit contracts docs health quick-test eod _eod_local_coverage scaffold-package

install:
	pip install -r requirements.txt || poetry install --no-root

lint:
	ruff check --fix .

type:
	pyright --warnings

imports:
	@lint-imports

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

# Scaffold a new package with basic structure
scaffold-package:
	@echo "Usage: make scaffold-package PACKAGE_NAME=<name>"
	@if [ -z "$(PACKAGE_NAME)" ]; then \
		echo "Error: PACKAGE_NAME is required"; \
		exit 1; \
	fi
	@mkdir -p packages/$(PACKAGE_NAME)
	@echo '"""' > packages/$(PACKAGE_NAME)/__init__.py
	@echo "$(PACKAGE_NAME) Package" >> packages/$(PACKAGE_NAME)/__init__.py
	@echo "" >> packages/$(PACKAGE_NAME)/__init__.py
	@echo "This package contains..." >> packages/$(PACKAGE_NAME)/__init__.py
	@echo '"""' >> packages/$(PACKAGE_NAME)/__init__.py
	@echo "" >> packages/$(PACKAGE_NAME)/__init__.py
	@echo '__version__ = "0.1.0"' >> packages/$(PACKAGE_NAME)/__init__.py
	@echo "Created package: packages/$(PACKAGE_NAME)/"