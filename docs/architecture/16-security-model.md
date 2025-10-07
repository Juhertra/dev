---
title: "SecFlow — Security Model (RBAC, Authentication, and Sandboxing)"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 16 — Security Model (RBAC, Authentication, and Sandboxing)

## 🧭 Overview

Security is a **first-class design goal** in the SecFlow architecture.  
Every user action, process execution, and data mutation is subject to authentication, authorization, and sandboxing.

This model ensures:
- **Strict access separation** between users, projects, and data.  
- **Controlled execution** of potentially dangerous tools or PoCs.  
- **Immutable auditability** of all operations.  
- **Zero-trust posture** inside the orchestration environment.

---

## 🧩 Layers of the Security Model

| Layer | Scope | Mechanism |
|--------|--------|------------|
| **Authentication** | User identity verification | JWT / OAuth2 tokens |
| **Authorization (RBAC)** | Access control | Role-based & scope-aware |
| **Execution Sandboxing** | Process isolation | Containerized runners |
| **Secrets Management** | API keys, credentials | Encrypted vault |
| **Audit Logging** | Accountability | Immutable append-only logs |

---

## 🧠 Authentication Architecture

SecFlow supports two auth models:
1. **Local Auth (default):** For standalone or on-premise deployments.  
2. **Federated Auth (optional):** OAuth2/OpenID Connect integration (GitHub, Google, Azure AD).

### Token Model
```json
{
  "sub": "hernan",
  "role": "admin",
  "exp": 1738783200,
  "projects": ["proj-01", "proj-02"]
}
```json

### Token Flow Diagram
```text
[User Login] → [Auth Provider] → [JWT Issued] → [API Gateway] → [SecFlow Web/API]
```text

Each request to `/api/*` must include:
```text
Authorization: Bearer <token>
```text

Tokens are verified by the API middleware using RS256 signature validation.

## 🧩 Role-Based Access Control (RBAC)

Roles define the scope of capabilities across the platform.

| Role | Permissions |
|------|-------------|
| **Admin** | Full control — manage tools, users, projects, retention, policies. |
| **Analyst** | Execute workflows, triage findings, view reports, limited editing. |
| **Viewer** | Read-only access to results and dashboards. |
| **Automation (Service)** | Used by background tasks (limited scoped tokens). |

### Example permission matrix:

| Action | Admin | Analyst | Viewer | Service |
|--------|-------|---------|--------|---------|
| Run workflow | ✅ | ✅ | ❌ | ✅ |
| Modify tool config | ✅ | ❌ | ❌ | ❌ |
| View findings | ✅ | ✅ | ✅ | ✅ |
| Delete project | ✅ | ❌ | ❌ | ❌ |
| Access PoCs | ✅ | ✅ | ❌ | ❌ |
| Run GC tasks | ✅ | ❌ | ❌ | ✅ |

## ⚙️ Policy Enforcement

Every endpoint and command passes through an Access Policy Filter:

```python
def authorize(action: str, user: User, project: Optional[str] = None):
    if not user.has_permission(action, project):
        raise HTTPException(403, detail=f"Forbidden: {action}")
```python

### Example route decorator:
```python
@app.get("/api/v1/findings")
@require_role(["admin", "analyst", "viewer"])
def list_findings():
    def authorize(self, action: str, user: User, project: Optional[str] = None) -> bool:
        """Check if user is authorized for action."""
        return user.has_permission(action, project)
```python

## 🧱 Secrets Management

### Secret Types
- API tokens for external tools (e.g., Shodan, Vulners)
- Private SSH keys for remote scans
- Encrypted credentials for authenticated targets

### Storage Backend
All secrets are stored in the SecFlow Vault, an encrypted JSON database backed by Fernet (AES-256).

```python
class SecretVault:
    def __init__(self, keyfile: Path):
        self.key = load_key(keyfile)
    def store(self, id: str, data: dict):
        enc = fernet_encrypt(json.dumps(data), self.key)
        write_file(f"/vault/{id}.enc", enc)
```python

### Secrets CLI
```bash
SecFlow secrets add nuclei_api --value "TOKEN123"
SecFlow secrets list
SecFlow secrets remove nuclei_api
```yaml

All access is scoped by user and project context.

## 🔒 Execution Sandboxing

All scanner and PoC executions run inside restricted containers or subprocess jails.

### Isolation Techniques
| Mechanism | Purpose |
|-----------|---------|
| Namespaces (PID, NET, MNT) | Process isolation |
| Seccomp Filters | Syscall restriction |
| cgroups v2 | CPU/memory limits |
| No-root UID mapping | Drops privileges |
| AppArmor profiles | File access control |
| Read-only FS | Prevents persistence |

### Example
```bash
docker run --rm --cap-drop=ALL \
  --security-opt=no-new-privileges \
  --read-only -m 512m --cpus=1 \
  SecFlow-runner:latest nuclei -t /templates
```python

## 🧩 Network & Data Security

| Channel | Encryption | Notes |
|---------|------------|-------|
| API <-> UI | HTTPS (TLS 1.3) | Strict transport enforced |
| Worker <-> API | Mutual TLS | Each worker has its own cert |
| File Sync | AES-256 encrypted | Optional compression |
| Database | At-rest encryption | SQLite: SEE, Postgres: TDE |
| Audit Logs | Signed + timestamped | Prevents tampering |

## 🧠 Secure Inter-Process Communication

Internal apps communicate via ZeroMQ or Redis queues over TLS.

Each message includes a signed envelope:

```json
{
  "msg_id": "uuid",
  "issuer": "worker-1",
  "signature": "HMAC-SHA256",
  "payload": {"data": "encrypted_content"}
}
```json

This ensures authenticity and non-repudiation.

## 🧩 Security Hooks & Middleware

SecFlow injects middleware for:
- Request validation (pydantic schemas)
- JWT token expiry verification
- Role validation (fast-path lookup)
- Audit log writing after each mutating operation

### Example:
```python
@app.middleware("http")
async def audit_request(request, call_next):
    response = await call_next(request)
    if request.method in ("POST", "DELETE", "PATCH"):
        log_audit(request, response)
    return response
```yaml

## 🔐 Audit Trail & Tamper Resistance

### Log Format
```json
{
  "timestamp": "2025-10-06T09:40:00Z",
  "user": "hernan",
  "action": "workflow_run",
  "project": "api-audit",
  "status": "success",
  "hash": "sha256:0a3b1c2d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2"
}
```json

### Storage & Verification
- Logs stored as JSON lines under `/audit/`
- Each file signed with an HMAC chain:

```python
H_i = HMAC(H_prev + log_i, key)
```yaml

Immutable and verifiable chain-of-trust.

## 🧠 Security Monitoring

| Metric | Description |
|--------|-------------|
| auth_failures_total | Failed login attempts |
| sandbox_executions_total | Containers spawned |
| policy_violations_total | Unauthorized actions |
| vault_accesses_total | Secret retrievals |
| audit_events_total | Log entries recorded |

## ⚙️ Compliance Framework Alignment

SecFlow's security architecture aligns with:

| Framework | Compliance Area |
|-----------|-----------------|
| **NIST SP 800-53** | Access control, auditing, system protection |
| **ISO/IEC 27001** | Information security management |
| **OWASP SAMM** | Secure software development lifecycle |
| **MITRE ATT&CK** | Mapping detection behaviors |
| **GDPR Art. 32** | Data confidentiality and integrity |

## 🔒 Key Rotation & Secrets Expiry

- Secrets have explicit TTLs (default: 180 days).
- Vault rotation command:

```bash
SecFlow vault rotate
```text

Rotation regenerates the encryption key and re-encrypts all entries.

## 🧩 Example Access Workflow

```text
[Analyst] → [Login via OIDC] → [JWT Issued]
→ [UI/API Gateway] → [RBAC Policy Check]
→ [Worker Executes Workflow in Sandbox]
→ [Findings Logged + Audit Entry Created]
```

## 🔮 Future Enhancements

- Hardware-backed encryption (YubiKey / TPM) for Vault keys.
- FIPS-compliant container sandbox.
- Behavior-based anomaly detection on audit logs.
- Single Sign-On (SSO) with just-in-time role provisioning.
- Runtime policy engine (OPA / Rego integration).

---

**Next:** [Observability, Logging & Metrics](17-observability-logging-and-metrics.md)
