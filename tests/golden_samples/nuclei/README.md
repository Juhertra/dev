# Nuclei Golden Samples

This directory contains golden sample outputs from Nuclei scanner for parser contract testing.

## Version Policy

- **Current Version**: `v3.0.x/` - Latest stable Nuclei output format
- **N-1 Version**: `v2.9.x/` - Previous major version for backward compatibility testing
- **Legacy Versions**: `v2.8.x/`, `v2.7.x/` - Historical versions for migration testing

## Directory Structure

```
nuclei/
├── v3.0.x/
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
- `output.json`: Standard scan output (10-50 findings)
- `output-verbose.json`: Verbose output with full metadata
- `output-error.json`: Error case (tool failure, timeout, etc.)
- `metadata.json`: Sample metadata (tool version, scan duration, etc.)

## Usage

Parser contract tests validate that wrappers can parse outputs from all supported versions without breaking changes.

```python
@pytest.mark.parametrize("version", ["v3.0.x", "v2.9.x"])
def test_nuclei_parser_contract(version):
    sample = load_golden_sample(f"nuclei/{version}/output.json")
    findings = NucleiWrapper().parse_output(sample)
    assert len(findings) > 0
    assert all(f.detector_id == "nuclei" for f in findings)
```

## Maintenance

- Update samples when Nuclei releases new major versions
- Remove samples for versions no longer supported
- Validate samples against current parser implementation
