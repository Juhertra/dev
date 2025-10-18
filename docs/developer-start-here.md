# Developer Start Here

## Quick Setup

- Clone repo, install Poetry, `poetry install --no-root`
- Branching: trunk-based; feature branches `feat/...`; PR ≤400 LOC or 2 approvals
- Run locally: `make test` ; fast loop: `make quick-test`
- Docs: `mkdocs serve` (local), `make health` before committing docs
- Read: `docs/architecture/00-index.md`, storage contracts, finding schema
- DoD checklist is in PR template; paste validation evidence in PRs

## Essential Reading

> **Read this first: [Governance & Engineering Standards](governance/engineering-standards.md)**

This page contains the complete Definition of Done checklist, branching rules, CI pipeline order, coverage requirements, and documentation health gates that all contributors must follow.

> **Development Practices: [Development Conventions](governance/development-conventions.md)**

This page covers daily development workflows, SOD/EOD rituals, branch naming conventions, PR rules, and CI fast-fail order that every developer needs to follow.

## Getting Started

### Prerequisites

- **Python 3.11+** (3.14 compatibility under testing)
- **Poetry** for dependency management
- **Git** for version control
- **Docker** (optional, for containerized testing)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/secflow.git
cd secflow

# Install dependencies
poetry install --no-root

# Verify installation
poetry run python -c "import secflow; print('SecFlow installed successfully')"
```

### M1 Features Overview

**M1 Implementation Status**: ✅ **Complete** - Plugin system, workflow engine, and storage framework delivered.

#### Plugin System
- **Plugin Loader**: Dynamic plugin discovery and loading
- **Security Framework**: Signature verification and sandboxing
- **Stub Implementations**: CVEMapper, FeroxStub, NucleiStub plugins
- **StoragePort Integration**: Findings persistence via StoragePort

#### Workflow Engine
- **Sequential Execution**: Nodes execute in topological order
- **YAML Recipes**: Declarative workflow definition
- **Retry Logic**: Configurable retry with exponential backoff
- **Timeout Handling**: Per-node timeout enforcement

#### Storage Framework
- **StoragePort Interface**: Protocol-based storage abstraction
- **In-Memory Adapter**: Thread-safe in-memory storage
- **Finding Schema**: JSON Schema validation (v1.0.0)
- **Project Isolation**: Separate storage per project

## Quick Tutorial: Running Your First Workflow

### 1. Validate a Workflow Recipe

```bash
# Validate the sample workflow
python tools/validate_recipe.py workflows/sample-linear.yaml

# Expected output:
# ✅ YAML syntax valid: workflows/sample-linear.yaml
# ✅ Schema validation passed: Linear Security Scan
# ✅ DAG validation passed: 3 nodes
# ✅ RecipeValidator validation passed
# 🎯 Recipe validation successful: Linear Security Scan
```

### 2. Execute a Workflow (Dry Run)

```bash
# Dry-run the workflow (analyze without execution)
python tools/run_workflow.py workflows/sample-linear.yaml --dry-run

# Expected output:
# 🔍 DRY RUN: Linear Security Scan
# 📝 Description: Simple linear workflow: discovery → scan → enrichment
# 📊 Nodes: 3
#   1. discovery (discovery.ferox)
#   2. scan (scan.nuclei)
#   3. enrich (enrich.cve)
# ✅ Dry run completed - no actual execution performed
```

### 3. Execute a Workflow (Actual Execution)

```bash
# Execute the workflow with M1 stub implementations
python tools/run_workflow.py workflows/sample-linear.yaml --execute

# Expected output:
# 🚀 EXECUTING: Linear Security Scan
# [2025-10-14 12:01:02] Workflow started
# [2025-10-14 12:01:05] Node discovery.ferox completed (urls=356)
# [2025-10-14 12:01:07] Node scan.nuclei completed (findings=112)
# [2025-10-14 12:01:10] Node enrich.cve completed (enriched_findings=112)
# [2025-10-14 12:01:10] Workflow completed successfully
```

### 4. View Results

```bash
# Check findings stored via StoragePort
python tools/list_findings.py --project-id sample-project

# Expected output:
# 📊 Findings for project: sample-project
# Total findings: 112
# By severity:
#   - Critical: 5
#   - High: 23
#   - Medium: 45
#   - Low: 32
#   - Info: 7
```

## Plugin Development Guide

### Creating a New Plugin

#### 1. Plugin Structure

```python
# packages/plugins/stubs/my_plugin.py
from packages.plugins.loader import PluginInterface, PluginMetadata
from packages.runtime_core.storage.storage_port import StoragePort
from typing import Dict, Any

class MyPlugin(PluginInterface):
    """Example plugin implementation."""
    
    def get_name(self) -> str:
        return "my-plugin"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="my-plugin",
            version="1.0.0",
            description="Example plugin for SecFlow",
            author="Your Name",
            category="detector",  # or "enricher" or "analytics"
            entrypoint="packages.plugins.stubs.my_plugin:MyPlugin"
        )
    
    def run(self, inputs: Dict[str, Any], config: Dict[str, Any], 
            context: ExecutionContext) -> Dict[str, Any]:
        """Execute plugin logic."""
        # Your plugin logic here
        findings = []
        
        # Process inputs and generate findings
        for item in inputs.get("data", []):
            finding = {
                "finding_schema_version": "1.0.0",
                "id": generate_uuid(),
                "project_id": context.project_id,
                "detector_id": "my-plugin",
                "title": "Example finding",
                "severity": "medium",
                "resource": item.get("url", ""),
                "evidence": {"raw_data": item},
                "created_at": datetime.utcnow().isoformat() + "Z"
            }
            findings.append(finding)
        
        return {"findings": findings}
```

#### 2. Plugin Manifest

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Example plugin for SecFlow",
  "author": "Your Name",
  "category": "detector",
  "entrypoint": "packages.plugins.stubs.my_plugin:MyPlugin",
  "dependencies": ["requests"],
  "config_schema": {
    "timeout": {
      "type": "integer",
      "default": 30
    }
  },
  "code_hash": "sha256:abc123...",
  "signature": "sha256:def456...",
  "created_at": "2025-10-14T10:00:00Z",
  "expires_at": "2026-10-14T10:00:00Z"
}
```

#### 3. Plugin Registration

```python
# packages/plugins/registry.py
from packages.plugins.stubs.my_plugin import MyPlugin

# Register your plugin
PluginRegistry.register("my-plugin", MyPlugin)
```

### Plugin Security

#### Signature Verification (M1)

```python
# M1: Basic hash-based verification
def verify_plugin_signature(manifest: PluginManifest, plugin_path: str) -> bool:
    """Verify plugin signature using SHA256 hash."""
    expected_hash = manifest.code_hash
    actual_hash = calculate_file_hash(plugin_path)
    return expected_hash == actual_hash

# M2+: Full cryptographic verification (planned)
def verify_plugin_signature_crypto(manifest: PluginManifest, plugin_path: str) -> bool:
    """Verify plugin signature using RSA/ECDSA."""
    # Implementation planned for M2
    pass
```

#### Sandbox Execution

```python
# Plugin execution in sandboxed environment
def execute_plugin_secure(plugin: PluginInterface, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """Execute plugin in sandboxed environment."""
    with sandbox_context():
        return plugin.run(inputs, config, context)
```

## Workflow Development

### YAML Recipe Format

```yaml
version: "1.0"
name: "My Custom Workflow"
description: "Custom workflow for specific testing"

nodes:
  - id: "discovery"
    type: "discovery.ferox"
    config:
      wordlist: "res://wordlists/custom:latest"
      threads: 25
      timeout: 600
    outputs: ["urls"]

  - id: "scan"
    type: "scan.nuclei"
    inputs: ["urls"]
    config:
      templates: "res://templates/custom:latest"
      rate_limit: 100
      timeout: 900
    outputs: ["findings"]

  - id: "enrich"
    type: "enrich.cve"
    inputs: ["findings"]
    config:
      sources: ["nvd", "osv"]
      timeout: 60
    outputs: ["enriched_findings"]

# Retry configuration
retry:
  max_attempts: 3
  backoff_factor: 2.0
  base_delay: 5.0

# State management
state:
  checkpoint_interval: 30
  resume_on_failure: true
  cache_intermediate: true
```

### Programmatic Workflow Execution

```python
from packages.workflow_engine.executor import WorkflowExecutor
from packages.workflow_engine.validate_recipe import RecipeValidator
from packages.storage.adapters.memory import InMemoryStorageAdapter

# Validate recipe
validator = RecipeValidator()
result = validator.validate_file("my-workflow.yaml")
if not result["ok"]:
    print(f"Validation failed: {result['errors']}")
    exit(1)

# Execute workflow
storage = InMemoryStorageAdapter()
executor = WorkflowExecutor(storage=storage)
workflow = executor.load_workflow_from_yaml("my-workflow.yaml")
execution_result = executor.execute_workflow(workflow)

print(f"Workflow status: {execution_result['status']}")
print(f"Completed nodes: {execution_result['completed_nodes']}")
```

## Storage Integration

### Using StoragePort

```python
from packages.runtime_core.storage.storage_port import StoragePort
from packages.storage.adapters.memory import InMemoryStorageAdapter

# Initialize storage
storage: StoragePort = InMemoryStorageAdapter()

# Save a finding
finding = {
    "finding_schema_version": "1.0.0",
    "id": "uuid-here",
    "project_id": "project-123",
    "detector_id": "scan.nuclei",
    "title": "SQL Injection Vulnerability",
    "severity": "high",
    "resource": "https://example.com/login",
    "evidence": {"payload": "admin' OR '1'='1"},
    "created_at": "2025-10-14T10:30:00Z"
}

storage.save_finding(finding)

# List findings
findings = storage.list_findings("project-123")
print(f"Found {len(findings)} findings")
```

### Finding Schema Compliance

```python
# All findings must include these required fields:
required_fields = [
    "finding_schema_version",  # Must be "1.0.0"
    "id",                     # UUID format
    "project_id",             # UUID format
    "detector_id",            # Pattern: ^[A-Za-z0-9_.-]+$
    "title",                  # Non-empty string
    "severity",               # Enum: info, low, medium, high, critical
    "resource",               # String (URL or identifier)
    "created_at"              # ISO 8601 timestamp with Z suffix
]

# Optional fields:
optional_fields = [
    "evidence",               # Object with additional properties
    "cwe",                    # Integer (CWE ID)
    "owasp",                  # Pattern: ^A\d{2}$ (OWASP Top 10)
    "cve_ids",                # Array of CVE identifiers
    "enrichment"              # Object with enrichment data
]
```

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run quick tests (unit tests only)
make quick-test

# Run specific test file
pytest tests/workflow/test_workflow_executor.py -v

# Run with coverage
pytest --cov=packages tests/
```

### Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_plugin_loader.py
│   ├── test_workflow_executor.py
│   └── test_storage_adapter.py
├── integration/             # Integration tests
│   ├── test_workflow_execution.py
│   └── test_plugin_integration.py
├── contracts/               # Contract tests
│   ├── test_storage_port.py
│   └── test_finding_schema.py
└── golden_samples/          # Test data
    ├── ferox_output.json
    ├── nuclei_output.json
    └── cve_data.json
```

## Observability & Debugging

### Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Plugin execution logs
logger = logging.getLogger(__name__)
logger.info(f"Plugin {plugin_name} executed successfully")
logger.error(f"Plugin {plugin_name} failed: {error}")
```

### Metrics Collection

```python
# M1: In-memory metrics collection
# M5: Prometheus metrics (planned)

def collect_plugin_metrics(plugin_name: str, duration: float, success: bool):
    """Collect plugin execution metrics."""
    metrics = {
        "plugin_name": plugin_name,
        "duration_ms": duration * 1000,
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    # Store metrics via StoragePort
    storage.save_metrics(metrics)
```

### Debug Mode

```bash
# Enable verbose logging
python tools/run_workflow.py workflows/sample-linear.yaml --execute --verbose

# Debug plugin loading
python tools/validate_recipe.py workflows/sample-linear.yaml --debug
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `packages/` is in Python path
2. **Validation Failures**: Check YAML syntax and required fields
3. **Execution Failures**: Verify node types and configuration
4. **Plugin Load Failures**: Check plugin manifest and signature
5. **Storage Errors**: Verify finding schema compliance

### Debug Commands

```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Validate finding schema
python tools/validate_finding.py --file finding.json

# Check plugin registry
python tools/list_plugins.py

# Test storage adapter
python tools/test_storage.py --adapter memory
```

## Next Steps

1. **Read Architecture Docs**: Start with `docs/architecture/00-index.md`
2. **Explore Examples**: Check `workflows/sample-linear.yaml` and plugin stubs
3. **Run Tests**: Execute `make test` to verify your setup
4. **Create Plugin**: Follow the plugin development guide above
5. **Build Workflow**: Create your own YAML recipe
6. **Contribute**: Follow the governance guidelines for PRs

## Resources

- **Architecture Documentation**: `docs/architecture/`
- **API Reference**: `docs/api/` (M6: mkdocstrings integration)
- **Sample Workflows**: `workflows/`
- **Plugin Examples**: `packages/plugins/stubs/`
- **Test Examples**: `tests/`

---

**Ready to start developing?** Check out the [Architecture Index](architecture/00-index.md) for detailed technical documentation.

1. **Poetry**: Install Poetry for dependency management
2. **Git**: For version control and branching
3. **Make**: For running build commands

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd secflow

# Install dependencies (without root package)
poetry install --no-root
```

### Development Workflow

#### Branching Strategy
- **Trunk-based development**: Main branch is the source of truth
- **Feature branches**: Use `feat/...` prefix for new features
- **Pull Request limits**: ≤400 LOC or require 2 approvals

#### Testing
- **Full test suite**: `make test`
- **Quick iteration**: `make quick-test` for faster feedback

#### Documentation
- **Local development**: `mkdocs serve` to preview docs locally
- **Health checks**: Run `make health` before committing documentation changes

### Essential Reading

1. **Architecture Overview**: Start with `docs/architecture/00-index.md`
2. **Storage Contracts**: Understand data persistence patterns
3. **Finding Schema**: Review the findings data model

### Definition of Done

The DoD checklist is available in the PR template. Always paste validation evidence in your pull requests to demonstrate compliance.

## Next Steps

After completing the setup, explore the architecture documentation to understand the system design and begin contributing to the project.
