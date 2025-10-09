# Feroxbuster Golden Samples

This directory contains golden sample outputs from Feroxbuster directory discovery tool for parser contract testing.

## Version Policy

- **Current Version**: `v2.10.x/` - Latest stable Feroxbuster output format
- **N-1 Version**: `v2.9.x/` - Previous major version for backward compatibility testing
- **Legacy Versions**: `v2.8.x/`, `v2.7.x/` - Historical versions for migration testing

## Directory Structure

```
feroxbuster/
├── v2.10.x/
│   ├── output.json          # Standard JSON output sample
│   ├── output-verbose.json  # Verbose output with metadata
│   └── output-error.json    # Error case sample
├── v2.9.x/
│   ├── output.json
│   └── output-verbose.json
└── README.md
```

## Sample Requirements

Each version directory should contain:
- `output.json`: Standard directory discovery output (20-100 endpoints)
- `output-verbose.json`: Verbose output with full metadata
- `output-error.json`: Error case (tool failure, timeout, etc.)
- `metadata.json`: Sample metadata (tool version, scan duration, wordlist used)

## Usage

Parser contract tests validate that wrappers can parse outputs from all supported versions without breaking changes.

```python
@pytest.mark.parametrize("version", ["v2.10.x", "v2.9.x"])
def test_feroxbuster_parser_contract(version):
    sample = load_golden_sample(f"feroxbuster/{version}/output.json")
    endpoints = FeroxWrapper().parse_output(sample)
    assert len(endpoints) > 0
    assert all(e.type == "endpoint" for e in endpoints)
```

## Maintenance

- Update samples when Feroxbuster releases new major versions
- Remove samples for versions no longer supported
- Validate samples against current parser implementation
