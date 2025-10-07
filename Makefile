.PHONY: validate serve build docs clean

validate:
	python3 docs/review/automated_validation.py
	python3 docs/review/ai_validation_summary.py

validate-summary:
	python3 docs/review/ai_validation_summary.py

serve:
	mkdocs serve

build:
	mkdocs build

docs: build

snapshot:
	make build
	tar czf docs_snapshot_$(shell date +%F).tgz site/

clean:
	rm -rf site/
	rm -rf docs/review/validation_report.md
	rm -f docs_snapshot_*.tgz

install-deps:
	pip install pyyaml mkdocs mkdocs-material mkdocs-mermaid2

help:
	@echo "Available targets:"
	@echo "  validate        - Run automated validation + AI summary"
	@echo "  validate-summary - Generate AI validation summary only"
	@echo "  serve           - Start MkDocs development server"
	@echo "  build           - Build static documentation site"
	@echo "  docs            - Alias for build"
	@echo "  snapshot        - Build site and create timestamped archive"
	@echo "  clean           - Clean build artifacts and reports"
	@echo "  install-deps    - Install required Python packages"
	@echo "  help            - Show this help message"
