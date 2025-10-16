# Workflow Engine Package - M1 Implementation

## Overview

The Workflow Engine is the core orchestration component of SecFlow, responsible for executing multi-tool workflows defined as YAML recipes. This M1 implementation provides comprehensive workflow definition, validation, and execution capabilities with retry/backoff logic and plugin integration.

## Status

- **M0**: ✅ Complete - Basic scaffolding and import architecture
- **M1**: ✅ Complete - Enhanced validation, orchestration, and execution
- **M3**: 🔄 Planned - Full plugin integration and concurrent execution

## Architecture Compliance

### ✅ Implemented Features (M1)

| Feature | Status | Description |
|---------|--------|-------------|
| **YAML Recipe Parsing** | ✅ Complete | Pydantic-based parsing with comprehensive validation |
| **DAG Validation** | ✅ Complete | Cycle detection and topological ordering |
| **Reference Validation** | ✅ Complete | Input/output consistency checking |
| **Node Type Validation** | ✅ Complete | Known type validation with configuration checks |
| **Sequential Execution** | ✅ Complete | Topological order execution with dependency resolution |
| **Retry/Backoff Logic** | ✅ Complete | Configurable retry with exponential backoff |
| **Error Handling** | ✅ Complete | Graceful failure handling with partial execution support |
| **State Management** | ✅ Partial | Configuration parsing (checkpointing deferred to M3) |
| **Plugin Integration** | ✅ Partial | Stub implementations with golden sample data |
| **Dry-Run Capability** | ✅ Complete | Workflow analysis without execution |

### 🔄 Planned Features (M3)

| Feature | Status | Description |
|---------|--------|-------------|
| **Concurrent Execution** | 🔄 Planned | Parallel node execution where dependencies allow |
| **Event System** | 🔄 Planned | Real-time event publishing and monitoring |
| **Caching** | 🔄 Planned | Intermediate result caching and persistence |
| **Monitoring** | 🔄 Planned | Metrics collection and workflow observability |
| **Plugin Registry** | 🔄 Planned | Dynamic plugin discovery and loading |

## Usage

### Basic Workflow Definition

Create a YAML recipe file (e.g., `my-workflow.yaml`):

```yaml
version: "1.0"
name: "Security Scan Workflow"
description: "End-to-end security scanning workflow"

nodes:
  - id: "discovery"
    type: "discovery.ferox"
    config:
      wordlist: "res://wordlists/dirb:latest"
      threads: 50
      timeout: 300
    outputs: ["urls"]

  - id: "scan"
    type: "scan.nuclei"
    inputs: ["urls"]
    config:
      templates: "res://templates/owasp-top10:latest"
      rate_limit: 150
      timeout: 600
    outputs: ["findings"]

  - id: "enrich"
    type: "enrich.cve"
    inputs: ["findings"]
    config:
      sources: ["nvd", "osv", "exploitdb"]
      timeout: 120
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

### Validation

Validate your workflow recipe:

```bash
# Validate a recipe file
python tools/validate_recipe.py my-workflow.yaml

# Test with built-in valid recipe
python tools/validate_recipe.py --test-valid

# Test with built-in invalid recipe
python tools/validate_recipe.py --test-invalid

# Verbose output
python tools/validate_recipe.py my-workflow.yaml --verbose

# JSON output
python tools/validate_recipe.py my-workflow.yaml --json
```

### Execution

Execute your workflow:

```bash
# Dry-run (analyze without execution)
python tools/run_workflow.py my-workflow.yaml --dry-run

# Actual execution
python tools/run_workflow.py my-workflow.yaml --execute

# Test with sample workflow
python tools/run_workflow.py --test-sample

# Verbose output
python tools/run_workflow.py my-workflow.yaml --execute --verbose
```

### Programmatic Usage

```python
from packages.workflow_engine.executor import WorkflowExecutor
from packages.workflow_engine.validate_recipe import RecipeValidator

# Validate recipe
validator = RecipeValidator()
result = validator.validate_file("my-workflow.yaml")
if not result["ok"]:
    print(f"Validation failed: {result['errors']}")
    exit(1)

# Execute workflow
executor = WorkflowExecutor()
workflow = executor.load_workflow_from_yaml("my-workflow.yaml")
execution_result = executor.execute_workflow(workflow)

print(f"Workflow status: {execution_result['status']}")
print(f"Completed nodes: {execution_result['completed_nodes']}")
```

## Node Types

### Discovery Nodes

| Type | Description | Required Config | Optional Config |
|------|-------------|----------------|-----------------|
| `discovery.ferox` | Directory/file discovery | `wordlist` | `threads`, `timeout` |
| `discovery.katana` | Subdomain discovery | `domain` | `threads`, `timeout` |

### Scanning Nodes

| Type | Description | Required Config | Optional Config |
|------|-------------|----------------|-----------------|
| `scan.nuclei` | Vulnerability scanning | `templates` | `rate_limit`, `timeout` |
| `scan.nmap` | Port scanning | `targets` | `ports`, `timeout` |

### Enrichment Nodes

| Type | Description | Required Config | Optional Config |
|------|-------------|----------------|-----------------|
| `enrich.cve` | CVE enrichment | - | `sources`, `timeout` |
| `enrich.owasp` | OWASP categorization | - | `timeout` |

### Utility Nodes

| Type | Description | Required Config | Optional Config |
|------|-------------|----------------|-----------------|
| `echo` | Debug/logging | - | `message` |

## Configuration Validation

### Feroxbuster Configuration

```yaml
config:
  wordlist: "res://wordlists/dirb:latest"  # Required: string
  threads: 50                              # Optional: integer 1-100
  timeout: 300                            # Optional: integer 1-3600
```

### Nuclei Configuration

```yaml
config:
  templates: "res://templates/owasp-top10:latest"  # Required: string
  rate_limit: 150                                   # Optional: integer 1-1000
  timeout: 600                                      # Optional: integer 1-3600
```

### CVE Enrichment Configuration

```yaml
config:
  sources: ["nvd", "osv", "exploitdb"]  # Optional: list of valid sources
  timeout: 120                          # Optional: integer 1-3600
```

Valid sources: `nvd`, `osv`, `exploitdb`, `cve-mitre`

## Error Handling

### Retry Configuration

```yaml
retry:
  max_attempts: 3      # Maximum retry attempts (1-10)
  backoff_factor: 2.0  # Exponential backoff factor (1.0-10.0)
  base_delay: 5.0      # Base delay in seconds (0.0-300.0)
```

### State Management

```yaml
state:
  checkpoint_interval: 30    # Checkpoint interval in seconds (0-3600)
  resume_on_failure: true     # Continue execution after node failure
  cache_intermediate: true    # Cache intermediate results
```

### Execution Modes

- **`completed`**: All nodes executed successfully
- **`failed`**: Workflow failed (node failure with `resume_on_failure: false`)
- **`partial`**: Some nodes failed but execution continued (`resume_on_failure: true`)

## Testing

### Unit Tests

```bash
# Run all workflow tests
pytest tests/workflow/ -v

# Run specific test file
pytest tests/workflow/test_workflow_scaffolding.py -v

# Run integration tests
pytest tests/workflow/test_workflow_integration.py -v
```

### Test Coverage

The workflow engine includes comprehensive test coverage:

- **Recipe Validation**: Schema, DAG, reference, and configuration validation
- **Workflow Execution**: Sequential execution, retry logic, error handling
- **Plugin Integration**: Stub implementations with golden sample data
- **Error Handling**: Edge cases, file not found, YAML parsing errors
- **Golden Sample Integration**: Reading from golden sample files

## Import Rules

The workflow engine follows strict import rules:

- ✅ **May import from**: `runtime_core`, `findings`
- ✅ **May be imported by**: Other packages
- ❌ **May NOT import from**: `wrappers`, `parsers`

## Integration Points

### Storage Integration

The workflow engine integrates with the StoragePort interface for data persistence:

```python
from packages.runtime_core.storage.storage_port import StoragePort
from packages.storage.adapters.memory import InMemoryStorageAdapter

executor = WorkflowExecutor(storage=InMemoryStorageAdapter())
```

### Plugin Integration

M1 provides stub implementations that read from golden sample data. M3 will integrate with actual plugin loaders:

```python
# M1: Stub execution with golden samples
result = executor._execute_node_stub(node)

# M3: Real plugin execution (planned)
plugin = plugin_loader.load(node.type)
result = plugin.run(node.inputs, node.config)
```

## Future Enhancements

### M3 Planned Features

1. **Concurrent Execution**: Parallel node execution where dependencies allow
2. **Event System**: Real-time event publishing for monitoring and UI updates
3. **Caching**: Intermediate result caching with StoragePort integration
4. **Monitoring**: Comprehensive metrics collection and workflow observability
5. **Plugin Registry**: Dynamic plugin discovery and loading system

### Architecture Compliance

This implementation fully complies with the Source of Truth architecture document (`docs/architecture/05-orchestration-and-workflow-engine.md`) for M1 scope, with clear plans for M3 enhancements.

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure `packages/workflow_engine` is in Python path
2. **Validation Failures**: Check YAML syntax and required fields
3. **Execution Failures**: Verify node types and configuration
4. **Golden Sample Issues**: Ensure golden sample files exist in `tests/golden_samples/`

### Debug Mode

Enable verbose logging for debugging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Support

For issues and questions, refer to:
- Architecture documentation: `docs/architecture/05-orchestration-and-workflow-engine.md`
- Integration tests: `tests/workflow/test_workflow_integration.py`
- Sample workflows: `workflows/sample-linear.yaml`