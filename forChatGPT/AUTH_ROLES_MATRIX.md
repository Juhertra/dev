# Authentication & Roles Matrix

## Role Definitions

| Role | Description | Access Level |
|------|-------------|--------------|
| **Viewer** | Read-only access to project data | Can view findings, runs, sitemap |
| **Analyst** | Can triage findings and view reports | Viewer + triage findings, export data |
| **Admin** | Full project management | Analyst + manage projects, run scans |

## Route Access Matrix

### Project Management Routes

| Route | Viewer | Analyst | Admin | Enforcement Hook | Storage Method |
|-------|--------|---------|-------|------------------|----------------|
| `GET /p/<pid>/sitemap` | ✔ | ✔ | ✔ | `@require_auth` | Flask session |
| `POST /p/create` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `POST /p/<pid>/rename` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `DELETE /p/<pid>` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |

### Drawer Routes

| Route | Viewer | Analyst | Admin | Enforcement Hook | Storage Method |
|-------|--------|---------|-------|------------------|----------------|
| `POST /p/<pid>/sitemap/endpoint-preview` | ✔ | ✔ | ✔ | `@require_project_access()` | Session + project membership |
| `POST /p/<pid>/sitemap/endpoint-runs` | ✔ | ✔ | ✔ | `@require_project_access()` | Session + project membership |
| `POST /p/<pid>/queue/item_details` | ✔ | ✔ | ✔ | `@require_project_access()` | Session + project membership |

### Scanning & Execution Routes

| Route | Viewer | Analyst | Admin | Enforcement Hook | Storage Method |
|-------|--------|---------|-------|------------------|----------------|
| `POST /p/<pid>/nuclei/scan` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `GET /p/<pid>/nuclei/stream` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `POST /p/<pid>/queue_add_override` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `POST /p/<pid>/send_now_override` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |

### Findings Management Routes

| Route | Viewer | Analyst | Admin | Enforcement Hook | Storage Method |
|-------|--------|---------|-------|------------------|----------------|
| `GET /p/<pid>/findings` | ✔ | ✔ | ✔ | `@require_project_access()` | Session + project membership |
| `GET /p/<pid>/findings/<idx>` | ✔ | ✔ | ✔ | `@require_project_access()` | Session + project membership |
| `POST /p/<pid>/findings/triage` | ✖ | ✔ | ✔ | `@require_role('analyst')` | JWT token |
| `POST /p/<pid>/findings/triage-group` | ✖ | ✔ | ✔ | `@require_role('analyst')` | JWT token |
| `POST /p/<pid>/findings/clear` | ✖ | ✖ | ✔ | `@require_role('admin')` | JWT token |
| `GET /p/<pid>/findings/export` | ✖ | ✔ | ✔ | `@require_role('analyst')` | JWT token |

### API Routes

| Route | Viewer | Analyst | Admin | Enforcement Hook | Storage Method |
|-------|--------|---------|-------|------------------|----------------|
| `GET /api/v1/metrics` | ✖ | ✖ | ✔ | `@require_api_key + @require_role('admin')` | API key + JWT |
| `GET /api/v1/findings` | ✖ | ✔ | ✔ | `@require_api_key + @require_role('analyst')` | API key + JWT |
| `POST /api/v1/findings` | ✖ | ✖ | ✔ | `@require_api_key + @require_role('admin')` | API key + JWT |

## Implementation Hooks

### Authentication Middleware (`app/middleware/auth_middleware.py` - create)

```python
from functools import wraps
from flask import request, session, jsonify
import jwt

def require_auth(f):
    """Require user to be authenticated"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role):
    """Require specific role level"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({"error": "Authentication required"}), 401
            
            user_role = session.get('role', 'viewer')
            role_hierarchy = {'viewer': 1, 'analyst': 2, 'admin': 3}
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                return jsonify({"error": "Insufficient permissions"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_project_access(f):
    """Require access to specific project"""
    @wraps(f)
    def decorated_function(pid, *args, **kwargs):
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        
        # Check if user has access to project
        user_projects = session.get('accessible_projects', [])
        if pid not in user_projects:
            return jsonify({"error": "Project access denied"}), 403
        
        return f(pid, *args, **kwargs)
    return decorated_function
```

### JWT Token Structure

```json
{
  "user_id": "user-123e4567-e89b-12d4-a716-446655440000",
  "email": "analyst@example.com",
  "role": "analyst",
  "accessible_projects": ["proj-1", "proj-2"],
  "exp": 1640995200,
  "iat": 1640908800
}
```

### Session Storage (`app/session_config.py` - create)

```python
from flask import Flask
import os

def configure_session(app: Flask):
    """Configure Flask session for authentication"""
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-me')
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'security_toolkit:'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
```

## User Management Integration Points

### User Storage (`storage/users.py` - create)

```python
from typing import Dict, List, Optional
import json
import os

def get_user_by_id(user_id: str) -> Optional[Dict]:
    """Get user by ID from storage"""
    users_file = os.path.join("storage", "users.json")
    if os.path.exists(users_file):
        users = json.load(open(users_file))
        return users.get(user_id)
    return None

def get_user_projects(user_id: str) -> List[str]:
    """Get projects accessible to user"""
    user = get_user_by_id(user_id)
    if user:
        return user.get('accessible_projects', [])
    return []

def validate_user_credentials(email: str, password: str) -> Optional[Dict]:
    """Validate user credentials (integrate with your auth system)"""
    # This would integrate with your existing auth system
    # For now, return mock data
    return {
        "user_id": "user-123",
        "email": email,
        "role": "analyst",
        "accessible_projects": ["proj-1", "proj-2"]
    }
```

### Project Access Control (`storage/project_access.py` - create)

```python
def check_project_access(user_id: str, project_id: str) -> bool:
    """Check if user has access to project"""
    user_projects = get_user_projects(user_id)
    return project_id in user_projects

def add_user_to_project(user_id: str, project_id: str, role: str = "viewer"):
    """Add user to project with specified role"""
    # Implementation for adding user to project
    pass

def remove_user_from_project(user_id: str, project_id: str):
    """Remove user from project"""
    # Implementation for removing user from project
    pass
```

## Security Considerations

### CSRF Protection
- All state-changing operations require CSRF tokens
- Tokens are included in forms and validated server-side

### Session Security
- Sessions are signed and encrypted
- Session timeout after 1 hour of inactivity
- Secure cookies in production (HTTPS only)

### API Key Management
- API keys are hashed before storage
- Rate limiting per API key
- Key rotation capability

### Audit Logging
- All authentication events logged
- Failed access attempts tracked
- Role changes audited
