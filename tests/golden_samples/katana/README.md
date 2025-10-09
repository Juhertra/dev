# Katana Golden Samples

This directory contains golden sample outputs from Katana web crawler for parser contract testing.

## Version Policy

- **Current Version**: `v1.0.x/` - Latest stable Katana output format
- **N-1 Version**: `v0.0.x/` - Previous major version for backward compatibility testing
- **Legacy Versions**: Historical versions for migration testing

## Directory Structure

```
katana/
├── v1.0.x/
│   ├── output.json          # Standard JSON output sample
│   ├── output-verbose.json  # Verbose output with metadata
│   └── output-error.json    # Error case sample
├── v0.0.x/
│   ├── output.json
│   └── output-verbose.json
└── README.md
```

## Sample Requirements

Each version directory should contain:
- `output.json`: Standard crawl output (50-200 endpoints)
- `output-verbose.json`: Verbose output with full metadata
- `output-error.json`: Error case (tool failure, timeout, etc.)
- `metadata.json`: Sample metadata (tool version, crawl duration, depth, etc.)

## Usage

Parser contract tests validate that wrappers can parse outputs from all supported versions without breaking changes.

```python
@pytest.mark.parametrize("version", ["v1.0.x", "v0.0.x"])
def test_katana_parser_contract(version):
    sample = load_golden_sample(f"katana/{version}/output.json")
    endpoints = KatanaWrapper().parse_output(sample)
    assert len(endpoints) > 0
    assert all(e.type == "endpoint" for e in endpoints)
```

## Maintenance

- Update samples when Katana releases new major versions
- Remove samples for versions no longer supported
- Validate samples against current parser implementation
