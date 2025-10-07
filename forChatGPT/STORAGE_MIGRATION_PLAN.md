# Storage Migration Plan - JSON → SQLite/PostgreSQL

## Current JSON Storage Structure

### File-Based Storage (`ui_projects/<pid>/`)
```
ui_projects/
├── projects.json                    # Project index
├── <pid>/
│   ├── <pid>.json                  # Project runtime state
│   ├── runs.json                   # Scan run history
│   ├── findings.json               # Security findings
│   ├── queue.json                  # Test queue state
│   └── endpoints/
│       ├── GET_https_api_com_users.json
│       └── POST_https_api_com_auth.json
```

## Proposed Database Schema

### SQLite Schema (`migrations/schema.sql`)

```sql
-- Projects table
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    settings JSON,
    metadata JSON
);

-- Endpoints table
CREATE TABLE endpoints (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    path TEXT NOT NULL,
    canonical_key TEXT UNIQUE NOT NULL,
    first_seen TIMESTAMP NOT NULL,
    last_seen TIMESTAMP,
    retired BOOLEAN DEFAULT FALSE,
    risk_score REAL DEFAULT 0.0,
    tags JSON,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Runs table
CREATE TABLE runs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    finished_at TIMESTAMP,
    findings_count INTEGER DEFAULT 0,
    worst_severity TEXT,
    templates TEXT,  -- comma-separated
    templates_count INTEGER DEFAULT 0,
    endpoints_scanned INTEGER DEFAULT 0,
    artifact_path TEXT,
    duration_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Findings table
CREATE TABLE findings (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    run_id TEXT,
    detector_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    path TEXT NOT NULL,
    title TEXT NOT NULL,
    subcategory TEXT,
    cwe TEXT,
    owasp TEXT,
    confidence INTEGER NOT NULL,
    status TEXT DEFAULT 'open',
    req_data JSON,
    res_data JSON,
    match_text TEXT,
    param TEXT,
    created_at TIMESTAMP NOT NULL,
    triaged_at TIMESTAMP,
    triaged_by TEXT,
    triage_notes TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

-- Endpoint dossiers (denormalized for performance)
CREATE TABLE endpoint_dossiers (
    endpoint_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    total_runs INTEGER DEFAULT 0,
    latest_run_id TEXT,
    latest_findings INTEGER DEFAULT 0,
    latest_worst TEXT,
    latest_finished_at TIMESTAMP,
    history JSON,  -- Array of run summaries
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (latest_run_id) REFERENCES runs(id) ON DELETE SET NULL
);

-- Indexes for performance
CREATE INDEX idx_endpoints_project ON endpoints(project_id);
CREATE INDEX idx_endpoints_canonical_key ON endpoints(canonical_key);
CREATE INDEX idx_runs_project ON runs(project_id);
CREATE INDEX idx_runs_started_at ON runs(started_at);
CREATE INDEX idx_findings_project ON findings(project_id);
CREATE INDEX idx_findings_run ON findings(run_id);
CREATE INDEX idx_findings_severity ON findings(severity);
CREATE INDEX idx_findings_status ON findings(status);
CREATE INDEX idx_findings_created_at ON findings(created_at);
```

### PostgreSQL Schema (Production)

```sql
-- Same as SQLite but with PostgreSQL-specific features
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Use UUID for primary keys
ALTER TABLE projects ALTER COLUMN id TYPE UUID USING id::UUID;
ALTER TABLE endpoints ALTER COLUMN id TYPE UUID USING id::UUID;
ALTER TABLE runs ALTER COLUMN id TYPE UUID USING id::UUID;
ALTER TABLE findings ALTER COLUMN id TYPE UUID USING id::UUID;

-- Add full-text search
CREATE INDEX idx_findings_title_fts ON findings USING gin(to_tsvector('english', title));
CREATE INDEX idx_findings_description_fts ON findings USING gin(to_tsvector('english', req_data->>'body'));

-- Add partitioning for large datasets
CREATE TABLE findings_2024 PARTITION OF findings
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

## Migration Script Outline

### One-Shot Migration (`migrations/migrate_json_to_db.py`)

```python
import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, List, Any

class JSONToDatabaseMigrator:
    def __init__(self, db_path: str, ui_projects_dir: str):
        self.db_path = db_path
        self.ui_projects_dir = Path(ui_projects_dir)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
    
    def migrate_all_projects(self):
        """Migrate all projects from JSON to database"""
        print("Starting JSON to Database migration...")
        
        # Create tables
        self.create_tables()
        
        # Migrate projects
        self.migrate_projects()
        
        # Migrate each project's data
        for project_dir in self.ui_projects_dir.iterdir():
            if project_dir.is_dir() and project_dir.name != '__pycache__':
                self.migrate_project_data(project_dir.name)
        
        print("Migration completed successfully!")
    
    def create_tables(self):
        """Create database tables"""
        with open('migrations/schema.sql', 'r') as f:
            schema = f.read()
        self.conn.executescript(schema)
        self.conn.commit()
    
    def migrate_projects(self):
        """Migrate projects.json to projects table"""
        projects_file = self.ui_projects_dir / "projects.json"
        if not projects_file.exists():
            return
        
        projects_data = json.load(projects_file)
        projects = projects_data.get('projects', [])
        
        for project in projects:
            self.conn.execute("""
                INSERT INTO projects (id, name, description, created_at, updated_at, settings, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                project['id'],
                project['name'],
                project.get('description', ''),
                project['created_at'],
                project.get('updated_at', project['created_at']),
                json.dumps(project.get('settings', {})),
                json.dumps(project.get('metadata', {}))
            ))
        
        self.conn.commit()
        print(f"Migrated {len(projects)} projects")
    
    def migrate_project_data(self, project_id: str):
        """Migrate individual project data"""
        project_dir = self.ui_projects_dir / project_id
        
        # Migrate endpoints from dossier files
        self.migrate_endpoints(project_id, project_dir)
        
        # Migrate runs
        self.migrate_runs(project_id, project_dir)
        
        # Migrate findings
        self.migrate_findings(project_id, project_dir)
        
        # Migrate endpoint dossiers
        self.migrate_endpoint_dossiers(project_id, project_dir)
    
    def migrate_endpoints(self, project_id: str, project_dir: Path):
        """Migrate endpoints from dossier files"""
        endpoints_dir = project_dir / "endpoints"
        if not endpoints_dir.exists():
            return
        
        endpoints_migrated = 0
        for dossier_file in endpoints_dir.glob("*.json"):
            with open(dossier_file, 'r') as f:
                dossier = json.load(f)
            
            # Extract endpoint info from canonical key
            endpoint_key = dossier['endpoint_key']
            method, url = endpoint_key.split(' ', 1)
            path = self.extract_path_from_url(url)
            
            self.conn.execute("""
                INSERT OR REPLACE INTO endpoints 
                (id, project_id, method, url, path, canonical_key, first_seen, last_seen, retired, risk_score, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.generate_endpoint_id(project_id, endpoint_key),
                project_id,
                method,
                url,
                path,
                endpoint_key,
                dossier.get('metadata', {}).get('first_seen', '2024-01-01T00:00:00Z'),
                dossier.get('metadata', {}).get('last_modified'),
                dossier.get('retired', False),
                dossier.get('metadata', {}).get('risk_score', 0.0),
                json.dumps(dossier.get('metadata', {}).get('tags', []))
            ))
            endpoints_migrated += 1
        
        self.conn.commit()
        print(f"Migrated {endpoints_migrated} endpoints for project {project_id}")
    
    def migrate_runs(self, project_id: str, project_dir: Path):
        """Migrate runs from runs.json"""
        runs_file = project_dir / "runs.json"
        if not runs_file.exists():
            return
        
        with open(runs_file, 'r') as f:
            runs = json.load(f)
        
        for run in runs:
            self.conn.execute("""
                INSERT OR REPLACE INTO runs 
                (id, project_id, started_at, finished_at, findings_count, worst_severity, 
                 templates, templates_count, endpoints_scanned, artifact_path, duration_ms, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run['run_id'],
                project_id,
                run['started_at'],
                run.get('finished_at'),
                run['findings'],
                run['worst'],
                run.get('templates', ''),
                run.get('templates_count', 0),
                run.get('endpoints_scanned', 0),
                run.get('artifact'),
                run.get('duration_ms'),
                True,  # Assume success if no error
                None
            ))
        
        self.conn.commit()
        print(f"Migrated {len(runs)} runs for project {project_id}")
    
    def migrate_findings(self, project_id: str, project_dir: Path):
        """Migrate findings from findings.json"""
        findings_file = project_dir / "findings.json"
        if not findings_file.exists():
            return
        
        with open(findings_file, 'r') as f:
            findings = json.load(f)
        
        for finding in findings:
            self.conn.execute("""
                INSERT OR REPLACE INTO findings 
                (id, project_id, run_id, detector_id, severity, method, url, path, title,
                 subcategory, cwe, owasp, confidence, status, req_data, res_data, 
                 match_text, param, created_at, triaged_at, triaged_by, triage_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                finding.get('id', self.generate_finding_id()),
                project_id,
                finding.get('run_id'),
                finding['detector_id'],
                finding['severity'],
                finding['method'],
                finding['url'],
                finding['path'],
                finding['title'],
                finding.get('subcategory'),
                finding.get('cwe'),
                finding.get('owasp'),
                finding['confidence'],
                finding.get('status', 'open'),
                json.dumps(finding.get('req', {})),
                json.dumps(finding.get('res', {})),
                finding.get('match'),
                finding.get('param'),
                finding['created_at'],
                finding.get('triage_info', {}).get('triaged_at'),
                finding.get('triage_info', {}).get('triaged_by'),
                finding.get('triage_info', {}).get('triage_notes')
            ))
        
        self.conn.commit()
        print(f"Migrated {len(findings)} findings for project {project_id}")
    
    def migrate_endpoint_dossiers(self, project_id: str, project_dir: Path):
        """Migrate endpoint dossiers"""
        endpoints_dir = project_dir / "endpoints"
        if not endpoints_dir.exists():
            return
        
        for dossier_file in endpoints_dir.glob("*.json"):
            with open(dossier_file, 'r') as f:
                dossier = json.load(f)
            
            endpoint_id = self.generate_endpoint_id(project_id, dossier['endpoint_key'])
            latest_run = dossier.get('latest_run', {})
            
            self.conn.execute("""
                INSERT OR REPLACE INTO endpoint_dossiers 
                (endpoint_id, project_id, total_runs, latest_run_id, latest_findings, 
                 latest_worst, latest_finished_at, history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                endpoint_id,
                project_id,
                dossier['total_runs'],
                latest_run.get('run_id'),
                latest_run.get('findings', 0),
                latest_run.get('worst'),
                latest_run.get('finished_at'),
                json.dumps(dossier.get('history', []))
            ))
        
        self.conn.commit()
        print(f"Migrated dossiers for project {project_id}")

# Usage
if __name__ == "__main__":
    migrator = JSONToDatabaseMigrator(
        db_path="security_toolkit.db",
        ui_projects_dir="ui_projects"
    )
    migrator.migrate_all_projects()
```

## Data Access Layer Migration

### New Storage Interface (`storage/database.py` - create)

```python
import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

class DatabaseStorage:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all projects"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_findings(self, project_id: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get findings with optional filters"""
        query = "SELECT * FROM findings WHERE project_id = ?"
        params = [project_id]
        
        if filters:
            if 'severity' in filters:
                query += " AND severity = ?"
                params.append(filters['severity'])
            if 'status' in filters:
                query += " AND status = ?"
                params.append(filters['status'])
        
        query += " ORDER BY created_at DESC"
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_endpoint_runs(self, project_id: str, canonical_key: str) -> List[Dict[str, Any]]:
        """Get runs for specific endpoint"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT r.* FROM runs r
                JOIN endpoint_dossiers ed ON r.id = ed.latest_run_id
                JOIN endpoints e ON ed.endpoint_id = e.id
                WHERE e.project_id = ? AND e.canonical_key = ?
                ORDER BY r.started_at DESC
            """, (project_id, canonical_key))
            return [dict(row) for row in cursor.fetchall()]
```

## Rollback Strategy

### Backup Before Migration
```bash
#!/bin/bash
# backup_before_migration.sh

BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup JSON files
cp -r ui_projects "$BACKUP_DIR/"

# Backup database if exists
if [ -f "security_toolkit.db" ]; then
    cp security_toolkit.db "$BACKUP_DIR/"
fi

echo "Backup created in $BACKUP_DIR"
```

### Rollback Script
```python
# rollback_to_json.py
import shutil
import os

def rollback_to_json(backup_dir: str):
    """Rollback to JSON storage from backup"""
    if not os.path.exists(backup_dir):
        print(f"Backup directory {backup_dir} not found")
        return
    
    # Remove current ui_projects
    if os.path.exists("ui_projects"):
        shutil.rmtree("ui_projects")
    
    # Restore from backup
    shutil.copytree(f"{backup_dir}/ui_projects", "ui_projects")
    
    # Remove database
    if os.path.exists("security_toolkit.db"):
        os.remove("security_toolkit.db")
    
    print("Rollback completed successfully")
```

## Performance Considerations

### Indexing Strategy
- **Primary indexes**: All foreign keys
- **Query indexes**: Severity, status, created_at for findings
- **Search indexes**: Full-text search on title and description
- **Composite indexes**: (project_id, severity) for common queries

### Data Retention
```sql
-- Automatic cleanup of old data
CREATE TRIGGER cleanup_old_findings
AFTER INSERT ON findings
BEGIN
    DELETE FROM findings 
    WHERE created_at < datetime('now', '-90 days')
    AND status = 'fixed';
END;
```

### Connection Pooling
```python
# For PostgreSQL production
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/security_toolkit",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

## Migration Validation

### Data Integrity Checks
```python
def validate_migration(db_path: str, ui_projects_dir: str):
    """Validate migration integrity"""
    db_storage = DatabaseStorage(db_path)
    
    # Check project count
    db_projects = len(db_storage.list_projects())
    json_projects = count_json_projects(ui_projects_dir)
    assert db_projects == json_projects, f"Project count mismatch: {db_projects} vs {json_projects}"
    
    # Check findings count per project
    for project in db_storage.list_projects():
        db_findings = len(db_storage.get_findings(project['id']))
        json_findings = count_json_findings(ui_projects_dir, project['id'])
        assert db_findings == json_findings, f"Findings count mismatch for {project['id']}"
    
    print("Migration validation passed!")
```
