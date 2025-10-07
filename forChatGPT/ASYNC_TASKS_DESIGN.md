# Async Tasks Design - Current Sync → Future Queue

## Current Synchronous Task Seam

### Task Contract (`tasks/__init__.py:15-35`)

```python
@dataclass
class ScanPlan:
    run_id: str
    project_id: str
    endpoints: List[str]
    templates: List[str]
    severity_levels: List[str]
    priority: int = 5

@dataclass
class ScanResult:
    run_id: str
    success: bool
    endpoint_count: int
    finding_count: int
    duration_ms: int
    error: Optional[str] = None

def submit_scan(plan: ScanPlan) -> ScanResult:
    """Current synchronous task execution"""
    # Phase 3: Direct execution
    return execute_nuclei_pipeline(plan)
```

### Current Implementation (`tasks/nuclei.py:45-65`)

```python
def execute_nuclei_pipeline(run_id: str, severity_levels: List[str], 
                           templates: List[str], endpoints: List[str], 
                           project_id: str) -> Dict[str, Any]:
    """Synchronous Nuclei execution"""
    logger = logging.getLogger('tasks.nuclei')
    
    # Build endpoints from queue
    endpoints_data = _build_endpoints_from_queue(project_id)
    
    # Execute Nuclei
    result = nuclei_wrapper.scan_endpoints(endpoints_data, templates, severity_levels)
    
    # Process results
    findings = nuclei_integration.to_internal_findings(result)
    findings.append_findings(project_id, findings)
    
    return {
        'run_id': run_id,
        'success': True,
        'findings_count': len(findings),
        'endpoints_scanned': len(endpoints_data),
        'duration_ms': result.get('duration_ms', 0)
    }
```

## Future Async Queue Design

### Task Queue Interface (`tasks/queue_interface.py` - create)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class TaskQueue(ABC):
    """Abstract task queue interface"""
    
    @abstractmethod
    def submit_task(self, task_type: str, payload: Dict[str, Any], 
                   priority: int = 5) -> str:
        """Submit task to queue, return task ID"""
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get current task status"""
        pass
    
    @abstractmethod
    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task result if completed"""
        pass
    
    @abstractmethod
    def cancel_task(self, task_id: str) -> bool:
        """Cancel pending/running task"""
        pass

class RQTaskQueue(TaskQueue):
    """Redis Queue implementation"""
    
    def __init__(self, redis_url: str):
        import redis
        from rq import Queue, Worker
        
        self.redis_conn = redis.from_url(redis_url)
        self.queue = Queue('security_scans', connection=self.redis_conn)
    
    def submit_task(self, task_type: str, payload: Dict[str, Any], 
                   priority: int = 5) -> str:
        """Submit scan task to Redis Queue"""
        job = self.queue.enqueue(
            'tasks.workers.execute_scan_task',
            payload,
            priority=priority,
            timeout='1h',
            job_id=payload.get('run_id')
        )
        return job.id
    
    def get_task_status(self, task_id: str) -> TaskStatus:
        """Get task status from Redis"""
        job = self.queue.fetch_job(task_id)
        if not job:
            return TaskStatus.FAILED
        
        if job.is_finished:
            return TaskStatus.COMPLETED
        elif job.is_failed:
            return TaskStatus.FAILED
        elif job.is_started:
            return TaskStatus.RUNNING
        else:
            return TaskStatus.PENDING
```

### Idempotency Rules

**Task Key Generation**:
```python
def generate_task_key(plan: ScanPlan) -> str:
    """Generate idempotent task key"""
    key_parts = [
        plan.project_id,
        plan.run_id,
        hashlib.md5(','.join(sorted(plan.endpoints)).encode()).hexdigest()[:8],
        hashlib.md5(','.join(sorted(plan.templates)).encode()).hexdigest()[:8]
    ]
    return f"scan:{':'.join(key_parts)}"

def check_existing_task(plan: ScanPlan) -> Optional[str]:
    """Check if identical task already exists"""
    task_key = generate_task_key(plan)
    existing_job = redis_conn.get(f"task_key:{task_key}")
    return existing_job.decode() if existing_job else None
```

**Idempotency Implementation**:
```python
def submit_scan_async(plan: ScanPlan) -> str:
    """Submit scan with idempotency check"""
    # Check for existing identical task
    existing_task_id = check_existing_task(plan)
    if existing_task_id:
        logger.info(f"Found existing task for same scan: {existing_task_id}")
        return existing_task_id
    
    # Generate idempotent key
    task_key = generate_task_key(plan)
    
    # Submit to queue
    task_id = queue.submit_task('scan', {
        'run_id': plan.run_id,
        'project_id': plan.project_id,
        'endpoints': plan.endpoints,
        'templates': plan.templates,
        'severity_levels': plan.severity_levels,
        'task_key': task_key
    }, priority=plan.priority)
    
    # Store task key mapping
    redis_conn.setex(f"task_key:{task_key}", 3600, task_id)
    
    return task_id
```

### Retry Strategy

**Exponential Backoff**:
```python
from rq import Retry

def execute_scan_task(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Worker function with retry logic"""
    try:
        # Execute scan
        result = execute_nuclei_pipeline(
            run_id=payload['run_id'],
            project_id=payload['project_id'],
            endpoints=payload['endpoints'],
            templates=payload['templates'],
            severity_levels=payload['severity_levels']
        )
        return result
        
    except NucleiBinaryError as e:
        # Fatal error - don't retry
        raise e
    except TemporaryError as e:
        # Retry with exponential backoff
        raise Retry(max_retries=3, interval=60)
    except Exception as e:
        # Unknown error - retry once
        raise Retry(max_retries=1, interval=300)
```

**Retry Configuration**:
```python
# RQ Worker configuration
worker = Worker(['security_scans'], connection=redis_conn, 
                retry_strategy={
                    'max_retries': 3,
                    'interval': 60,
                    'backoff': 'exponential'
                })
```

### Result Storage & Artifacts

**Task Result Storage**:
```python
def store_task_result(task_id: str, result: Dict[str, Any]):
    """Store task result with TTL"""
    redis_conn.setex(
        f"task_result:{task_id}",
        86400,  # 24 hour TTL
        json.dumps(result)
    )

def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve task result"""
    result_data = redis_conn.get(f"task_result:{task_id}")
    return json.loads(result_data) if result_data else None
```

**Artifact Storage**:
```python
def store_scan_artifacts(run_id: str, artifacts: Dict[str, Any]):
    """Store scan artifacts in persistent storage"""
    artifact_dir = f"ui_projects/{run_id}/artifacts"
    os.makedirs(artifact_dir, exist_ok=True)
    
    # Store Nuclei output
    with open(f"{artifact_dir}/nuclei_output.ndjson", "w") as f:
        for finding in artifacts.get('nuclei_output', []):
            f.write(json.dumps(finding) + "\n")
    
    # Store scan metadata
    with open(f"{artifact_dir}/scan_metadata.json", "w") as f:
        json.dump(artifacts.get('metadata', {}), f, indent=2)
    
    # Update run record with artifact paths
    update_run_artifacts(run_id, {
        'nuclei_output': f"{artifact_dir}/nuclei_output.ndjson",
        'metadata': f"{artifact_dir}/scan_metadata.json"
    })
```

## Migration Strategy

### Phase 1: Add Async Interface (Current)
```python
# Keep existing sync interface
def submit_scan(plan: ScanPlan) -> ScanResult:
    """Synchronous execution (current behavior)"""
    return execute_nuclei_pipeline(plan)

# Add async interface
def submit_scan_async(plan: ScanPlan) -> str:
    """Asynchronous execution (new)"""
    if ENABLE_ASYNC_TASKS:
        return submit_scan_async_impl(plan)
    else:
        # Fallback to sync
        result = submit_scan(plan)
        return result.run_id
```

### Phase 2: Gradual Migration
```python
# Feature flag controlled migration
ENABLE_ASYNC_TASKS = os.environ.get('ENABLE_ASYNC_TASKS', 'false').lower() == 'true'

def submit_scan(plan: ScanPlan) -> Union[ScanResult, str]:
    """Hybrid sync/async interface"""
    if ENABLE_ASYNC_TASKS:
        return submit_scan_async(plan)
    else:
        return execute_nuclei_pipeline(plan)
```

### Phase 3: Full Async (Future)
```python
# Remove sync interface, keep only async
def submit_scan(plan: ScanPlan) -> str:
    """Asynchronous scan submission"""
    return submit_scan_async(plan)

def get_scan_result(run_id: str) -> Optional[ScanResult]:
    """Get scan result by run ID"""
    return get_task_result(run_id)
```

## Queue Monitoring & Management

### Task Status Endpoint
```python
@app.route('/api/v1/tasks/<task_id>/status')
def get_task_status(task_id: str):
    """Get task status via API"""
    status = queue.get_task_status(task_id)
    result = queue.get_task_result(task_id) if status == TaskStatus.COMPLETED else None
    
    return jsonify({
        'task_id': task_id,
        'status': status.value,
        'result': result
    })
```

### Queue Health Monitoring
```python
@app.route('/api/v1/queue/health')
def queue_health():
    """Queue health check"""
    return jsonify({
        'queue_size': queue.size(),
        'active_workers': len(queue.workers),
        'failed_jobs': len(queue.failed_job_registry),
        'redis_connected': queue.connection.ping()
    })
```

## Configuration

### Environment Variables
```bash
# Queue configuration
TASK_QUEUE_TYPE=redis  # or 'sync' for current behavior
REDIS_URL=redis://localhost:6379/0
WORKER_CONCURRENCY=4
TASK_TIMEOUT=3600

# Feature flags
ENABLE_ASYNC_TASKS=true
ASYNC_SCAN_PRIORITY=5
```

### Worker Deployment
```bash
# Start RQ workers
rq worker security_scans --url redis://localhost:6379/0 --concurrency 4

# Or with supervisor
[program:security_toolkit_worker]
command=rq worker security_scans --url redis://localhost:6379/0
directory=/app
autostart=true
autorestart=true
```
