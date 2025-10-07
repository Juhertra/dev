# Error Contract - API Response Standards

## Error Response Format

All error responses follow this structure:
```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": "Optional technical details",
  "request_id": "uuid-for-tracing"
}
```

## Route Error Specifications

### Drawer Routes

#### `POST /p/<pid>/sitemap/endpoint-preview`
- **400 Bad Request**: Missing required parameters
  ```json
  {
    "error": "Missing required parameter: url",
    "code": "MISSING_PARAMETER",
    "details": "url parameter is required"
  }
  ```
- **404 Not Found**: Project not found
  ```json
  {
    "error": "Project not found",
    "code": "PROJECT_NOT_FOUND",
    "details": "Project ID does not exist"
  }
  ```
- **500 Internal Server Error**: Dossier parsing failed
  ```json
  {
    "error": "Unable to load endpoint data",
    "code": "DOSSIER_PARSE_ERROR",
    "details": "Corrupted dossier file: GET_https_api_example_com_users.json"
  }
  ```

#### `POST /p/<pid>/sitemap/endpoint-runs`
- **400 Bad Request**: Invalid endpoint signature
  ```json
  {
    "error": "Invalid endpoint parameters",
    "code": "INVALID_ENDPOINT",
    "details": "url and method parameters required"
  }
  ```
- **404 Not Found**: Endpoint not found in dossiers
  ```json
  {
    "error": "No test history found for endpoint",
    "code": "ENDPOINT_NOT_FOUND",
    "details": "GET https://api.example.com/users has no recorded runs"
  }
  ```

#### `POST /p/<pid>/queue/item_details`
- **400 Bad Request**: Invalid queue item
  ```json
  {
    "error": "Invalid queue item reference",
    "code": "INVALID_QUEUE_ITEM",
    "details": "Queue item not found or malformed"
  }
  ```

### Action Routes

#### `POST /p/<pid>/nuclei/scan`
- **400 Bad Request**: Missing templates or empty queue
  ```json
  {
    "error": "No templates selected or empty test queue",
    "code": "INVALID_SCAN_REQUEST",
    "details": "Select at least one template and ensure queue has endpoints"
  }
  ```
- **503 Service Unavailable**: Nuclei binary not found
  ```json
  {
    "error": "Security scanner unavailable",
    "code": "NUCLEI_UNAVAILABLE",
    "details": "Nuclei binary not found at configured path"
  }
  ```

#### `GET /p/<pid>/nuclei/stream`
- **429 Too Many Requests**: Too many concurrent streams
  ```json
  {
    "error": "Too many active scan streams",
    "code": "RATE_LIMITED",
    "details": "Maximum 3 concurrent streams per project"
  }
  ```
- **500 Internal Server Error**: Nuclei execution failure
  ```json
  {
    "error": "Scan execution failed",
    "code": "NUCLEI_EXECUTION_ERROR",
    "details": "Nuclei process exited with code 1"
  }
  ```

### Findings Routes

#### `POST /p/<pid>/findings/triage`
- **400 Bad Request**: Invalid finding reference
  ```json
  {
    "error": "Invalid finding reference",
    "code": "INVALID_FINDING",
    "details": "Finding ID not found or malformed"
  }
  ```
- **422 Unprocessable Entity**: Invalid status value
  ```json
  {
    "error": "Invalid triage status",
    "code": "INVALID_STATUS",
    "details": "Status must be one of: open, accepted_risk, false_positive, fixed"
  }
  ```

#### `POST /p/<pid>/findings/clear`
- **403 Forbidden**: Insufficient permissions
  ```json
  {
    "error": "Insufficient permissions",
    "code": "FORBIDDEN",
    "details": "Only project owners can clear findings"
  }
  ```

### API Routes

#### `GET /api/v1/metrics`
- **401 Unauthorized**: Missing API key
  ```json
  {
    "error": "API key required",
    "code": "MISSING_API_KEY",
    "details": "X-API-Key header required"
  }
  ```
- **403 Forbidden**: Invalid API key
  ```json
  {
    "error": "Invalid API key",
    "code": "INVALID_API_KEY",
    "details": "API key not recognized"
  }
  ```

#### `GET /api/v1/findings`
- **400 Bad Request**: Invalid query parameters
  ```json
  {
    "error": "Invalid query parameters",
    "code": "INVALID_QUERY",
    "details": "severity must be one of: critical, high, medium, low, info"
  }
  ```

## Error Handling Implementation

**Server-Side Error Handler** (`app/error_handlers.py` - create):
```python
from flask import jsonify, request
import logging

logger = logging.getLogger('error_handler')

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "code": "BAD_REQUEST",
        "details": str(error),
        "request_id": getattr(request, 'request_id', None)
    }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "code": "NOT_FOUND", 
        "details": str(error),
        "request_id": getattr(request, 'request_id', None)
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal Server Error",
        "code": "INTERNAL_ERROR",
        "details": "An unexpected error occurred",
        "request_id": getattr(request, 'request_id', None)
    }), 500
```

**Client-Side Error Handling** (`static/main.js:120-140`):
```javascript
function handleApiError(xhr, status, error) {
    let errorData = {};
    try {
        errorData = JSON.parse(xhr.responseText);
    } catch (e) {
        errorData = { error: "Unknown error occurred" };
    }
    
    showToast(`Error: ${errorData.error}`, 'error');
    
    // Log for debugging
    console.error('API Error:', {
        status: status,
        code: errorData.code,
        details: errorData.details,
        request_id: errorData.request_id
    });
}
```
