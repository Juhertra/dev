# API Documentation

## Overview

This section contains comprehensive API documentation for SecFlow. The API documentation is generated from source code using mkdocstrings and will be fully implemented in M6.

## Current Status

- **M0-M5**: Manual API documentation
- **M6+**: Automated API documentation with mkdocstrings

## API Structure

### Core APIs
- **Analytics Core**: Metrics and telemetry APIs
- **Detection Engine**: Pattern matching and vulnerability detection
- **Storage Layer**: Data persistence and retrieval
- **Workflow Engine**: Task orchestration and execution

### Integration APIs
- **Nuclei Integration**: External tool integration
- **ModSecurity Integration**: Security rule processing
- **Plugin System**: Extensible architecture APIs

## Documentation Standards

### Code Documentation
- All public APIs must have comprehensive docstrings
- Type hints required for all parameters and return values
- Examples provided for complex APIs
- Error conditions documented

### API Design Principles
- RESTful design where applicable
- Consistent error handling and response formats
- Versioning strategy for breaking changes
- Rate limiting and authentication requirements

## Future Implementation (M6)

The following mkdocstrings configuration will be enabled in M6:

```yaml
# mkdocs.yml additions (commented until M6)
# plugins:
#   - mkdocstrings:
#       handlers:
#         python:
#           paths: [.]
#           options:
#             docstring_style: google
#             show_source: true
#             show_root_heading: true
#             show_root_toc_entry: true
#             show_signature_annotations: true
#             show_signature_return_annotations: true
#             separate_signature: true
#             heading_level: 2
#             filters: ["!^_"]
#             members_order: source
#             merge_init_into_class: true
```

## Manual Documentation (M0-M5)

Until M6, API documentation will be maintained manually in this directory:

- `core-apis.md` - Core system APIs
- `integration-apis.md` - External integration APIs
- `plugin-apis.md` - Plugin system APIs
- `examples/` - Code examples and usage patterns

## Contributing

When adding new APIs:

1. Follow the documentation standards above
2. Add manual documentation until M6
3. Ensure all public methods have docstrings
4. Include type hints and examples
5. Update this README if adding new API categories

## Links

- [Development Conventions](../governance/development-conventions.md) - API development standards
- [Architecture Overview](../architecture/00-index.md) - System architecture
- [Plugin System](../architecture/06-plugin-system.md) - Plugin architecture
