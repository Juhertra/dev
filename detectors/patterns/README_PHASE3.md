# Phase 3: Enhanced Pattern Engine

## Overview

Phase 3 implements comprehensive improvements to the pattern detection engine, focusing on higher-quality detection with reduced false positives and enhanced evidence capture.

## Key Features

### 1. Enhanced Pattern Validation

#### Comprehensive Field Validation
- **Required Fields**: `id`, `title`, `regex` are mandatory
- **ID Validation**: Must be alphanumeric with hyphens/underscores only
- **Title Validation**: 3-200 characters, descriptive
- **Regex Validation**: Compilation test with detailed error reporting

#### CWE Format Normalization
- Automatically converts `"79"` → `"CWE-79"`
- Validates CWE numbers (1-9999 range)
- Consistent format across all patterns

#### CVSS Validation
- Score range: 0.0-10.0
- Automatic severity mapping from CVSS scores
- Validation of numeric format

#### Confidence Scoring
- Range: 0-100
- Warnings for very low (<30) or very high (>90) confidence
- Context-aware confidence adjustments

### 2. Enhanced Evidence Capture

#### Comprehensive Match Data
```json
{
  "matched_fragment": "exact matched text",
  "context_snippet": "100 chars before and after match",
  "request_snippet": "relevant request data",
  "match_position": 1234,
  "match_length": 25,
  "response_status": 200,
  "content_type": "application/json",
  "request_method": "POST",
  "request_url": "https://api.example.com/users"
}
```

#### Request Context
- Extracts relevant request snippets based on `where` field
- Captures request body, headers, URL, parameters
- Links findings back to original request data

#### Response Context
- Response status codes
- Content-type information
- Response size and structure

### 3. False-Positive Reducers

#### Context Gates
- **Length Gates**: Skip matches >1000 characters (likely not user input)
- **Pattern Gates**: Skip UUIDs, hashes, system-generated data
- **Alphanumeric Gates**: Skip long alphanumeric strings

#### Content-Type Gates
- **Binary Content**: Skip image/video/audio files by default
- **Minified JavaScript**: Skip minified JS unless explicitly allowed
- **Large Responses**: Skip responses >1MB unless allowed

#### Status Gates
- **Error Responses**: Skip 4xx/5xx responses unless allowed
- **Redirects**: Skip 3xx responses unless allowed
- **Success Bias**: Prefer 2xx responses for reliability

#### Pattern-Specific Gates
- **XSS**: Must look like user input
- **SQL Injection**: Skip generic SQL keywords
- **Path Traversal**: Must contain path separators (`../`, `..\\`)

### 4. Enhanced Confidence Scoring

#### Base Confidence
- Starts with pattern-defined confidence (default: 60)

#### Context Adjustments
- **Parameter Reflection**: +15 confidence if match appears in request
- **Response Status**: +5 for 2xx, -10 for 4xx+
- **Content Type**: +5 for JSON, -5 for HTML
- **Match Length**: +10 for short matches, -15 for very long

#### Quality Gates
- **Minified Content**: -20 confidence for minified responses
- **User Input Likelihood**: Context-aware scoring
- **System Data Detection**: Reduced confidence for system patterns

## Pattern Configuration

### Enhanced Pattern Format

```json
{
  "id": "pattern-id",
  "title": "Descriptive Pattern Title",
  "where": ["response.body", "response.headers"],
  "regex": "pattern\\(s\\)",
  "cwe": "CWE-79",
  "cvss": 6.1,
  "confidence": 75,
  "severity": "medium",
  "tags": ["xss", "reflected"],
  
  // False-positive reducer settings
  "context_gate": true,
  "content_type_gate": true,
  "minified_gate": true,
  "status_gate": true,
  
  // Gate overrides
  "allow_binary_content": false,
  "allow_minified_content": false,
  "allow_error_responses": false,
  "allow_redirects": false,
  "allow_large_responses": false
}
```

### Gate Configuration

#### Default Behavior
- All gates are **enabled by default**
- Conservative approach to reduce false positives
- Explicit opt-in for edge cases

#### Gate Overrides
- `allow_binary_content`: Allow detection in binary files
- `allow_minified_content`: Allow detection in minified content
- `allow_error_responses`: Allow detection in error responses
- `allow_redirects`: Allow detection in redirect responses
- `allow_large_responses`: Allow detection in large responses

## Usage Examples

### Basic Pattern
```json
{
  "id": "xss-basic",
  "title": "Basic XSS Detection",
  "regex": "<script[^>]*>.*?</script>",
  "cwe": "79",
  "confidence": 60
}
```

### Enhanced Pattern with Gates
```json
{
  "id": "xss-enhanced",
  "title": "Enhanced XSS Detection",
  "regex": "<script[^>]*>.*?\\{\\{.*?\\}\\}.*?</script>",
  "cwe": "CWE-79",
  "confidence": 75,
  "context_gate": true,
  "content_type_gate": true,
  "allow_minified_content": false
}
```

### High-Confidence Pattern
```json
{
  "id": "sql-injection-high-conf",
  "title": "SQL Injection with High Confidence",
  "regex": "SQL syntax error.*mysql_fetch_array",
  "cwe": "CWE-89",
  "confidence": 90,
  "severity": "high",
  "allow_error_responses": true
}
```

## Performance Considerations

### Regex Optimization
- Compiled regex caching
- Performance warnings for patterns >500 characters
- Anchoring recommendations for broad patterns

### Memory Management
- Limited snippet sizes (2048 chars for evidence, 500 for context)
- Response size limits (1MB default)
- Efficient text field extraction

### Validation Performance
- Pattern validation on load, not runtime
- Comprehensive error reporting
- Graceful handling of invalid patterns

## Migration Guide

### Existing Patterns
- Existing patterns continue to work unchanged
- New features are opt-in via configuration
- Default behavior is conservative (fewer false positives)

### Upgrading Patterns
1. Add `cwe` field in `CWE-XXX` format
2. Add `severity` field if not using CVSS
3. Add gate configuration as needed
4. Test with enhanced validation

### Validation Errors
- Check pattern validation output
- Fix regex compilation errors
- Normalize CWE formats
- Adjust confidence scores

## Best Practices

### Pattern Design
- Use specific, anchored regex patterns
- Avoid overly broad patterns (`.*`)
- Include context in pattern matching
- Test patterns against real data

### Confidence Scoring
- Start with moderate confidence (60-70)
- Use context gates to reduce false positives
- Adjust based on real-world testing
- Document confidence rationale

### Gate Configuration
- Enable gates by default
- Only disable gates for specific use cases
- Test patterns with gates enabled/disabled
- Monitor false positive rates

## Monitoring and Metrics

### Pattern Statistics
- Total patterns loaded
- Patterns by pack type
- Patterns by severity
- Patterns by confidence level
- Enabled/disabled counts

### Detection Metrics
- Matches per pattern
- False positive rates
- Confidence distributions
- Gate effectiveness

### Performance Metrics
- Pattern compilation time
- Detection runtime
- Memory usage
- Cache hit rates

## Future Enhancements

### Phase 4 Considerations
- Nuclei template integration
- ModSecurity CRS import
- Machine learning confidence scoring
- Pattern performance profiling
- Community pattern validation

### Advanced Features
- Pattern versioning
- A/B testing for patterns
- Dynamic confidence adjustment
- Pattern effectiveness scoring
- Automated pattern optimization
