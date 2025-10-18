PY := python
PIP := pip

.PHONY: setup install lint type imports test unit contracts docs health quick-test eod _eod_local_coverage scaffold-package coverage-dashboard coverage-html coverage-xml test-unit test-integration test-e2e test-security test-workflow test-plugin test-coverage test-all

setup:
	$(PIP) install -e ".[dev]"

install:
	pip install -r requirements.txt || poetry install --no-root

lint:
	ruff check .

type:
	pyright

imports:
	lint-imports

unit:
	pytest -q

coverage:
	coverage run -m pytest -q && coverage report -m

# Coverage targets for M1
coverage-dashboard:
	python scripts/coverage_dashboard.py

coverage-html:
	pytest --cov=. --cov-report=html -q

coverage-xml:
	pytest --cov=. --cov-report=xml -q

# Test categories for M1
test-unit:
	pytest -m unit -q

test-integration:
	pytest -m integration -q

test-e2e:
	pytest -m e2e -q

test-security:
	pytest -m security -q

test-workflow:
	pytest -m workflow -q

test-plugin:
	pytest -m plugin -q

test-coverage:
	pytest --cov=. --cov-report=term-missing --cov-report=xml -q

# Demo targets for M1
demo-setup:
	python scripts/m1_demo_tools.py setup

demo-workflow:
	python scripts/m1_demo_tools.py workflow security_scan --target https://example.com

demo-plugin:
	python scripts/m1_demo_tools.py plugin http_scanner

demo-benchmark:
	python scripts/m1_demo_tools.py benchmark

demo-menu:
	python scripts/m1_demo_tools.py menu

demo-status:
	python scripts/m1_demo_tools.py status

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

# Shared-state report helper
report:
	python3 tools/compile_daily_report.py $(PERIOD)