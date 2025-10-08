.PHONY: validate serve build docs clean dag gates fence-hygiene

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

dag:
	python3 tools/workflow_to_mermaid.py workflows/recipe.yaml > docs/diagrams/recipe_dag.md

clean:
	rm -rf site/
	rm -rf docs/review/validation_report.md
	rm -f docs_snapshot_*.tgz

install-deps:
	pip install pyyaml mkdocs mkdocs-material pymdown-extensions

gates:
	make build
	python3 scripts/run_gates.py

fence-hygiene:
	python3 scripts/fence_hygiene.py

help:
	@echo "Available targets:"
	@echo "  validate        - Run automated validation + AI summary"
	@echo "  validate-summary - Generate AI validation summary only"
	@echo "  serve           - Start MkDocs development server"
	@echo "  build           - Build static documentation site"
	@echo "  docs            - Alias for build"
	@echo "  snapshot        - Build site and create timestamped archive"
	@echo "  dag             - Generate Mermaid DAG from workflow recipe"
	@echo "  gates           - Run documentation quality gates"
	@echo "  fence-hygiene   - Clean up markdown fences"
	@echo "  clean           - Clean build artifacts and reports"
	@echo "  install-deps    - Install required Python packages"
	@echo "  help            - Show this help message"

mermaid-parity:
	python scripts/mermaid_parity_gate.py

ascii-blocker:
	python scripts/ascii_html_blocker_gate.py

health:
	bash scripts/healthcheck.sh
