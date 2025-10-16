# SecFlow Plugin System

## Overview

The SecFlow Plugin System provides a standardized way to integrate external security tools and services into the SecFlow workflow engine. This system allows for modular, extensible security tooling that can be dynamically loaded and executed.

## Architecture

### Core Components

- **PluginInterface**: Abstract base class defining the standard plugin contract
- **PluginLoader**: Core loader that discovers, loads, and manages plugins
- **PluginRegistry**: Registry for managing loaded plugins and their manifests
- **PluginManifest**: Container for plugin metadata and configuration schemas

### Plugin Types

1. **Discovery Plugins**: Tools that discover endpoints, services, or assets
   - Example: Feroxbuster (directory discovery)
   - Output: List of discovered URLs/endpoints

2. **Scan Plugins**: Tools that perform vulnerability scanning
   - Example: Nuclei (vulnerability scanner)
   - Output: List of security findings

3. **Enricher Plugins**: Tools that enrich findings with additional data
   - Example: CVE Mapper (CVE information enrichment)
   - Output: Enriched findings with additional metadata

## Directory Structure

```
packages/plugins/
├── __init__.py
├── loader.py                 # Core plugin loader
├── discovery/
│   ├── __init__.py
│   └── ferox.py             # Feroxbuster discovery plugin
├── scan/
│   ├── __init__.py
│   └── nuclei.py            # Nuclei vulnerability scanner
└── enrichers/
    ├── __init__.py
    └── cve_mapper.py        # CVE mapping enricher
```

## Plugin Interface

All plugins must implement the `PluginInterface` abstract base class:

```python
class PluginInterface(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Return the plugin name."""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Return the plugin version."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Return list of plugin capabilities."""
        pass
    
    @abstractmethod
    def get_manifest(self) -> Dict[str, Any]:
        """Return the plugin manifest."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        pass
    
    @abstractmethod
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the plugin with given configuration."""
        pass
```

## Plugin Manifest

Each plugin must provide a manifest containing:

```json
{
  "name": "plugin_name",
  "version": "1.0.0",
  "type": "discovery|scan|enricher",
  "capabilities": ["capability1", "capability2"],
  "description": "Plugin description",
  "config_schema": {
    "type": "object",
    "properties": {
      "required_field": {"type": "string", "description": "Field description"}
    },
    "required": ["required_field"]
  }
}
```

## Usage Examples

### Loading and Executing Plugins

```python
from packages.plugins.loader import execute_plugin, list_available_plugins

# List available plugins
plugins = list_available_plugins()
print(plugins)

# Execute discovery plugin
result = execute_plugin("discovery.ferox", {
    "target": "https://example.com"
})

# Execute scan plugin
result = execute_plugin("scan.nuclei", {
    "targets": ["https://example.com"]
})

# Execute enricher plugin
result = execute_plugin("enricher.cve_mapper", {
    "findings": [{"id": "finding1", "title": "Test Finding"}]
})
```

### Direct Plugin Loader Usage

```python
from packages.plugins.loader import get_plugin_loader

loader = get_plugin_loader()

# Get plugin information
plugin_info = loader.get_available_plugins()

# Execute plugin with detailed results
result = loader.execute_plugin("discovery.ferox", {
    "target": "https://example.com"
})

print(f"Success: {result['success']}")
print(f"Output: {result['output']}")
```

## Built-in Plugins

### Feroxbuster Discovery Plugin (`discovery.ferox`)

**Purpose**: Directory and endpoint discovery using Feroxbuster

**Configuration**:
```json
{
  "target": "https://example.com",
  "wordlist": "/path/to/wordlist.txt",
  "threads": 50,
  "timeout": 10
}
```

**Output**:
```json
{
  "plugin": "feroxbuster",
  "type": "discovery",
  "results": {
    "urls": [
      {
        "url": "https://example.com/api/users",
        "status_code": 200,
        "content_length": 1024,
        "method": "GET",
        "source": "feroxbuster",
        "confidence": 85
      }
    ],
    "total_discovered": 1,
    "execution_time_ms": 1500,
    "status": "completed"
  }
}
```

### Nuclei Vulnerability Scanner (`scan.nuclei`)

**Purpose**: Vulnerability scanning using Nuclei templates

**Configuration**:
```json
{
  "targets": ["https://example.com"],
  "templates": "res://templates/nuclei:latest",
  "threads": 25,
  "rate_limit": 150,
  "severity": ["critical", "high", "medium"]
}
```

**Output**:
```json
{
  "plugin": "nuclei",
  "type": "scan",
  "results": {
    "findings": [
      {
        "id": "nuclei_ssl_cert_12345",
        "title": "SSL Certificate Information Disclosure",
        "severity": "low",
        "path": "https://example.com",
        "detector_id": "nuclei",
        "evidence": {"template-id": "ssl-cert"},
        "confidence": 90,
        "status": "open"
      }
    ],
    "total_findings": 1,
    "execution_time_ms": 3000,
    "status": "completed"
  }
}
```

### CVE Mapper Enricher (`enricher.cve_mapper`)

**Purpose**: Enrich findings with CVE information and severity data

**Configuration**:
```json
{
  "findings": [
    {
      "id": "finding1",
      "title": "Test Finding",
      "severity": "low",
      "evidence": {"template-id": "ssl-cert"}
    }
  ],
  "severity_threshold": "low"
}
```

**Output**:
```json
{
  "plugin": "cve_mapper",
  "type": "enrichment",
  "results": {
    "enriched_findings": [
      {
        "id": "finding1",
        "title": "Test Finding",
        "severity": "medium",
        "severity_source": "cve_enrichment",
        "cve_details": {
          "cve_id": "CVE-2021-3450",
          "severity": "medium",
          "description": "SSL certificate information disclosure vulnerability",
          "cvss_score": 5.3,
          "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-3450"],
          "enriched_by": "cve_mapper",
          "confidence": 85
        },
        "cwe_id": "CWE-200"
      }
    ],
    "statistics": {
      "total_findings": 1,
      "enriched_findings": 1,
      "cve_mapped": 1,
      "severity_upgraded": 1
    }
  }
}
```

## Adding New Plugins

### 1. Create Plugin Class

Create a new Python file in the appropriate plugin directory:

```python
# packages/plugins/scan/my_scanner.py
from packages.plugins.loader import PluginInterface

class MyScannerPlugin(PluginInterface):
    def get_name(self) -> str:
        return "my_scanner"
    
    def get_version(self) -> str:
        return "1.0.0"
    
    def get_capabilities(self) -> List[str]:
        return ["scan"]
    
    def get_manifest(self) -> Dict[str, Any]:
        return {
            "name": "my_scanner",
            "version": "1.0.0",
            "type": "scan",
            "capabilities": ["scan"],
            "description": "My custom scanner plugin"
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        return "target" in config
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Plugin implementation
        return {
            "plugin": "my_scanner",
            "type": "scan",
            "results": {"findings": []}
        }
```

### 2. Register Plugin

Add the plugin to the `PluginLoader._load_builtin_plugins()` method:

```python
def _load_builtin_plugins(self):
    # ... existing plugins ...
    
    # Register new plugin
    my_scanner_plugin = MyScannerPlugin()
    my_scanner_manifest = PluginManifest({
        'name': 'my_scanner',
        'version': '1.0.0',
        'type': 'scan',
        'capabilities': ['scan'],
        'description': 'My custom scanner plugin'
    })
    self.registry.register(my_scanner_plugin, my_scanner_manifest)
```

### 3. Test Plugin

```python
from packages.plugins.loader import execute_plugin

result = execute_plugin("scan.my_scanner", {
    "target": "https://example.com"
})
print(f"Success: {result['success']}")
```

## Security Considerations

### M1 Implementation (Current)

- **Simulation Mode**: All plugins run in simulation mode using golden sample data
- **No External Execution**: No actual tool binaries are executed
- **Sandboxed Environment**: Plugins run with limited permissions
- **Timeout Protection**: Built-in timeout protection for plugin execution

### Future Security Enhancements (M2+)

- **Sandbox Execution**: Plugins will run in isolated containers
- **Resource Limits**: CPU, memory, and network constraints
- **Permission Controls**: Fine-grained permission system
- **Audit Logging**: Comprehensive execution logging
- **Signature Verification**: Plugin signature validation

## Performance Considerations

### Current Performance

- **Fast Execution**: Simulation-based plugins execute quickly (< 5 seconds)
- **Memory Efficient**: Minimal memory footprint for stub implementations
- **Scalable Design**: Plugin interface designed for future async execution

### Future Optimizations (M2+)

- **Async Execution**: Non-blocking plugin execution
- **Streaming Results**: Incremental result processing
- **Caching**: Result caching for repeated operations
- **Parallel Processing**: Concurrent plugin execution

## Error Handling

### Plugin Execution Errors

```python
result = execute_plugin("discovery.ferox", {"target": "invalid"})

if not result['success']:
    print(f"Error: {result['error']}")
    print(f"Plugin: {result.get('plugin_id', 'unknown')}")
```

### Common Error Scenarios

1. **Plugin Not Found**: Plugin ID doesn't exist in registry
2. **Invalid Configuration**: Configuration validation fails
3. **Execution Failure**: Plugin execution throws exception
4. **Timeout**: Plugin execution exceeds timeout limit

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guidelines
- Use type hints for all function parameters and return values
- Include comprehensive docstrings
- Add logging for debugging and monitoring

### Testing

- Write unit tests for all plugin methods
- Test configuration validation
- Test error handling scenarios
- Test with various input configurations

### Documentation

- Document all configuration options
- Provide usage examples
- Include performance characteristics
- Document security considerations

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all plugin dependencies are installed
2. **Configuration Validation**: Check required fields in plugin configuration
3. **Golden Sample Missing**: Verify golden sample files exist in `tests/golden_samples/`
4. **Plugin Registration**: Ensure plugin is properly registered in loader

### Debug Mode

Enable debug logging to troubleshoot plugin issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Plugin execution will show detailed logs
result = execute_plugin("discovery.ferox", {"target": "https://example.com"})
```

## Future Roadmap

### M2 Enhancements

- Real tool binary integration
- Sandbox execution environment
- Advanced plugin discovery
- External plugin support

### M3+ Features

- Plugin marketplace
- Dynamic plugin loading
- Plugin versioning
- Cross-plugin communication

---

For more information, see the [SecFlow Architecture Documentation](../architecture/07-tools-integration-model.md).
