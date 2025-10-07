---
title: "SecFlow — Error Handling, Fault Tolerance & Recovery Architecture"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 18 — Error Handling, Fault Tolerance & Recovery Architecture

## 🧭 Overview

SecFlow is designed to operate in unpredictable environments — remote APIs, external security tools, local sandboxes, and asynchronous task queues.  
This chapter defines the **resilience layer** of the platform, ensuring that the system can **detect, contain, recover, and self-heal** from errors without compromising data integrity or user experience.

---

## 🧱 Core Resilience Principles

| Principle | Description |
|------------|-------------|
| **Isolation** | Failures in one tool or workflow should not cascade. |
| **Retryability** | Transient failures should automatically reattempt. |
| **Idempotency** | Repeated executions must produce consistent outcomes. |
| **Observability** | Every error must be traceable with full context. |
| **Graceful Degradation** | System continues partially even under partial failure. |

---

## ⚙️ Error Taxonomy

Errors are classified to determine handling strategy:

| Type | Example | Recovery Strategy |
|-------|----------|-------------------|
| **Transient** | Network timeout, rate-limit, temporary unavailability | Retry with exponential backoff |
| **Permanent** | Invalid config, missing file, malformed schema | Fail fast, log, require user fix |
| **External Tool** | Nuclei crash, Feroxbuster exit code ≠ 0 | Capture stdout/stderr, mark node failed |
| **Internal Logic** | Python exception, schema mismatch | Rollback transaction, log critical |
| **Security Violation** | Sandbox breakout, unauthorized access | Immediate isolation + alert |
| **User Abort** | Manual workflow stop | Graceful cancellation, cleanup resources |

---

## 🧩 Error Handling Architecture

```yaml
+------------------------------------------+
|              Workflow Engine             |
| - Retry Controller                       |
| - Error Propagation Manager              |
| - Compensation Handlers                  |
| - Dead Letter Queue                      |
+------------------------------------------+
      │
      ▼
+------------------------------------------+
|     Observability & Audit Log            |
+------------------------------------------+
```python

---

## 🧠 Exception Handling Model

All SecFlow components use a unified exception hierarchy:

```python
class SecFlowError(Exception):
    """Base class for all SecFlow exceptions."""

class TransientError(SecFlowError):
    """Recoverable error, eligible for retry."""

class PermanentError(SecFlowError):
    """Non-recoverable error, must be logged and halted."""

class SecurityError(SecFlowError):
    """Unauthorized or unsafe action detected."""
```python

Every operation that might fail is wrapped in a retry-safe decorator.

## 🔁 Retry Logic & Tenacity Integration

SecFlow uses the Tenacity library for intelligent retries.

```python
from tenacity import retry, wait_exponential, stop_after_attempt

@retry(
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda r: log_error(r)
)
def run_tool(tool_name, args):
    return subprocess.run(args, check=True)
```python

### Retry Rules
| Context | Max Retries | Delay Type |
|---------|-------------|------------|
| API HTTP Requests | 5 | Exponential |
| CVE Enrichment Queries | 3 | Linear |
| Worker Tasks | 3 | Exponential |
| File System Operations | 2 | Immediate |
| PoC Sandbox Launch | 1 | No retry (for safety) |

## 🧱 Circuit Breaker Pattern

SecFlow prevents repeated failures from overloading systems via circuit breakers.

### Implementation Example
```python
class CircuitBreaker:
    def __init__(self, threshold=5, timeout=60):
        self.failures = 0
        self.opened_at = None
        self.threshold = threshold
        self.timeout = timeout

    def record_failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = datetime.utcnow()

    def can_execute(self):
        if not self.opened_at:
            return True
        return (datetime.utcnow() - self.opened_at).seconds > self.timeout
```python

Used for:
- Remote API (NVD, OSV, Exploit-DB)
- File I/O saturation
- Tool wrappers under repeated crashes

## 🧩 Dead Letter Queue (DLQ)

Failed tasks that exceed retry limits are pushed into the DLQ for manual review.

```python
@app.task(bind=True, max_retries=3)
def run_scan(self, task_id):
    try:
        run_workflow(task_id)
    except Exception as e:
        if self.request.retries == self.max_retries:
            enqueue_dlq(task_id, str(e))
        raise self.retry(exc=e)
```text

### DLQ entries include:
- Task ID
- Workflow ID
- Exception message
- Retry count
- Timestamp

### Example DLQ record:
```json
{
  "task": "wf-1234-node-nuclei",
  "error": "Connection timeout to target",
  "retries": 3,
  "timestamp": "2025-10-06T10:22:00Z"
}
```text

## 🧠 Self-Healing Workflows

SecFlow supports automatic node rehydration — failed steps in a workflow can be restarted independently without restarting the entire pipeline.

### Rehydration Process
1. Detect failed node.
2. Mark upstream outputs as valid.
3. Restart failed node only.
4. Merge results into workflow graph.

### CLI example:
```bash
SecFlow workflow resume --node nuclei --project acme-api
```python

## 🧩 Transactional Integrity

Database operations are wrapped in ACID transactions using SQLModel context managers:

```python
from sqlmodel import Session

def save_finding(finding):
    with Session(engine) as session:
        try:
            session.add(finding)
            session.commit()
        except Exception:
            session.rollback()
            raise
```text

All cross-project mutations (findings, triage, cache) are transactional.

## 🧠 Error Event Logging & Correlation

Each exception generates an audit entry:

```json
{
  "event": "error",
  "component": "worker",
  "type": "TransientError",
  "workflow_id": "wf-abc123",
  "trace_id": "b73f0b7c-47f9-4bb3-9b9c-ffacbd1d6a67",
  "message": "Feroxbuster timeout",
  "retries": 3
}
```yaml

Errors are correlated with:
- Workflow Trace ID
- Finding UUID (if relevant)
- User and project context

This allows full replay and debugging via observability dashboards.

## ⚙️ Graceful Degradation

If a subsystem fails (e.g., enrichment API offline):
- Workflows continue with reduced functionality.
- Missing data marked as `"partial": true`.
- Users notified in the triage panel:

```text
⚠ CVE enrichment service temporarily unavailable — retry later.
```python

## 🧩 Alerting & Notification Hooks

- Integration with Prometheus Alertmanager for system errors.
- Optional Slack / Email webhook for high-severity failures.
- Rate-limited notifications to avoid alert fatigue.

### Example alert webhook payload:
```json
{
  "severity": "critical",
  "component": "sandbox",
  "message": "PoC execution timeout",
  "project": "api-audit",
  "trace_id": "a2c134b5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8"
}
```python

## 🧱 Recovery Strategies

| Context | Recovery Action |
|---------|-----------------|
| Sandbox crash | Auto-restart with clean container |
| API outage | Retry with backoff + circuit breaker |
| Tool misconfiguration | Disable tool temporarily, notify user |
| Cache corruption | Rebuild from source |
| Disk full | Trigger GC and alert |
| Worker crash | Celery task re-queued |
| DB lock contention | Exponential backoff retry |

## 🧠 Example Error Lifecycle

```text
[Error Detected] → [Retry 1/3] → [Retry 2/3] → [DLQ]
→ [Alert sent to Slack] → [Analyst re-runs workflow node] → [Recovered]
```text

## 🔒 Security Implications

- Sensitive stack traces are redacted before exposure.
- Error details logged internally only.
- External responses use generic safe messages:

```json
{"error": "Internal processing issue, please retry later."}
```

## 🔮 Future Enhancements

- Adaptive retry policies based on machine learning.
- AI-powered incident summarization for triage.
- Transactional outbox pattern for guaranteed task delivery.
- Fine-grained chaos testing integrated in CI/CD.

---

**Next:** [Risk Assessment & Scoring Framework](19-risk-assessment-framework.md)
