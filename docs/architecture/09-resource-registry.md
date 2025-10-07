---
title: "SecFlow — Resource Registry"
author: "Hernan Trajtemberg, Lead Security Engineer"
codename: "SecFlow"
version: "1.0"
date: "2025-10-06"
---

# 09 — Resource Registry

## 🧭 Overview

The **Resource Registry** is SecFlow's shared data layer for managing **reusable assets** such as:

- Wordlists  
- Templates (Nuclei, ZAP, custom YAML)  
- Headers and payload sets  
- Configurations and schema files  
- CVE/CWE enrichment databases  

This registry provides unified access to all resources, manages versioning and scope isolation, and acts as the single source of truth for both CLI and API workflows.

---

## 🧱 Design Goals

| Goal | Description |
|------|--------------|
| **Centralized** | One consistent repository for all reusable data. |
| **Scoped** | Resources may be global, group-specific, or project-specific. |
| **Versioned** | Immutable artifacts with hash-based versioning. |
| **Queryable** | Searchable by tags, type, or metadata. |
| **Cacheable** | Local caching for fast re-use and offline execution. |
| **Auditable** | Every modification is logged in the audit trail. |

---

## 🧩 Architecture Overview

```yaml
+----------------------------------------------------+
|                Resource API                        |
| - Resource Manager                                  |
| - Indexer / Search Engine                          |
| - Version Resolver                                 |
| - Storage Adapter (File, DB, Remote)               |
+---------------------------┬------------------------+
                            |
                            ▼
                +---------------+
                | Resource Blob |
                +---------------+
                            |
                            ▼
                +---------------+
                | Local Cache   |
                +---------------+
```python

---

## ⚙️ Resource Model

```python
# core-lib/models/resource.py
from typing import Literal, Optional
from datetime import datetime
from pydantic import BaseModel

class Resource(BaseModel):
    id: str
    name: str
    type: Literal["wordlist", "templates", "headers", "payloads", "configs", "schema"]
    version: str
    hash: str
    scope: Literal["global", "group", "project"]
    owner: Optional[str]
    blob_uri: str
    metadata: dict
    created_at: datetime
    updated_at: datetime
    usage_count: int
    last_used: Optional[datetime]
```yaml

## 🧩 Scope Hierarchy

| Level | Description | Example Path |
|-------|-------------|--------------|
| **Global** | Available across all users and projects. | `res://wordlists/common.txt` |
| **Group** | Shared among specific teams. | `res://group/redteam/headers.json` |
| **Project** | Private to a specific pentest or client project. | `res://project/acme/templates/custom.yaml` |

### Precedence Rules
1. Run-level override
2. Node-level override
3. Project default
4. Group default
5. Global default

### Example:
If project-A has a custom wordlist `res://project/acme/dirb.yaml`, it overrides `res://wordlists/dirb:latest`.

## 🧩 Example Registry Entry

```yaml
id: "res://wordlists/dirb:1.2.0"
name: "Dirbuster Common"
type: "wordlist"
version: "1.2.0"
hash: "sha256:ea13f3b4c8d9e2f1a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8"
scope: "global"
metadata:
  tags: ["web", "discovery"]
  size: 24312
  license: "GPL-3.0"
  source: "https://github.com/digination/dirbuster"
created_at: "2025-08-01T12:32:00Z"
updated_at: "2025-08-15T09:21:00Z"
```python

## 🧱 Storage Backends

The Resource Registry supports multiple backends:

| Backend | Usage | Notes |
|---------|-------|-------|
| **Local Filesystem** | Default for developer use. | Fast, no dependencies. |
| **SQLite / Postgres** | Production database. | Metadata stored in DB, blob on disk. |
| **S3 / MinIO** | Remote multi-tenant storage. | Ideal for distributed environments. |
| **Git-backed Repository** | Version-controlled registry. | Enables audit and rollback. |

## 🧩 Resource Manager Interface

```python
# core-lib/ports/resource_port.py
from typing import List
from .models import Resource

class ResourcePort(Protocol):
    def register(self, resource: Resource) -> None:
        """Register a new resource in the registry."""
        pass
    
    def list(self, scope: str) -> List[Resource]:
        """List resources within a scope."""
        pass
    
    def get(self, id: str) -> Resource:
        """Get a resource by ID."""
        pass
    
    def resolve(self, name: str, version: str) -> Resource:
        """Resolve a resource by name and version."""
        pass
    
    def increment_usage(self, id: str) -> None:
        """Increment usage counter for a resource."""
        pass
```python

### Example Adapter Implementation
```python
# storage/resource_repository.py
import json, os
from core_lib.models.resource import Resource

class FileResourceRepo:
    def __init__(self, base_path="~/.SecFlow/resources"):
        self.base = os.path.expanduser(base_path)

    def register(self, res: Resource):
        path = os.path.join(self.base, f"{res.id.replace('res://','')}.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(res.model_dump_json())

    def get(self, id):
        path = os.path.join(self.base, f"{id.replace('res://','')}.json")
        return Resource.parse_file(path)
```yaml

## 🧩 Resource Fetching & Caching

When a workflow references `res://wordlists/dirb:latest`:

1. The registry resolves the resource (global/group/project).
2. The manager checks the local cache.
3. If missing or outdated, it downloads or loads the file blob.
4. The reference is then injected into the tool configuration.

```python
resolved = ResourceManager.resolve("res://wordlists/dirb:latest")
path = CacheManager.fetch(resolved)
```yaml

## 🧠 Resource Versioning

Resources are immutable once published; updates produce new versions.

| Operation | Behavior |
|-----------|----------|
| **publish** | Adds new resource version, preserves old one. |
| **retire** | Marks resource as deprecated (kept for history). |
| **promote** | Moves a project resource to group/global scope. |

### Version Reference Syntax
```text
res://wordlists/dirb:1.2.0
res://templates/nuclei:latest
```text

## 🧩 Registry CLI Commands

```bash
# List all resources
SecFlow resources list

# Show details for a resource
SecFlow resources show res://wordlists/dirb:latest

# Add new resource
SecFlow resources add wordlist ./custom.txt --scope project

# Promote resource
SecFlow resources promote res://project/acme/dirb:latest --to global
```text

## 🧠 Integration with Tool Manager

Tools reference resources via symbolic URIs.
At runtime, the registry automatically resolves URIs into local paths.

### Example Nuclei config:
```yaml
templates: res://templates/nuclei:latest
wordlist: res://wordlists/dirb:latest
```

## 🔒 Security & Integrity

| Mechanism | Description |
|-----------|-------------|
| **Hash Validation** | SHA-256 hashes validated before use. |
| **Signed Resources** | Optional GPG signing for remote sources. |
| **Access Control** | Scoped permissions (Admin / Analyst / Viewer). |
| **Audit Trail** | Every fetch and publish event logged. |

## 🧩 Garbage Collection Policy

When a resource is deleted:
- Orphaned blob files are queued for cleanup by the `GarbageCollector`.
- The audit log retains metadata for traceability.
- Cached copies remain valid until TTL expiration.

## 🧠 Example Use Case

### Global Wordlist Shared by Tools

All tools can reference `res://wordlists/dirb:latest`:
- **Feroxbuster** uses it for directory brute-force.
- **Katana** can reuse it for crawl hints.
- **Nuclei** leverages it for parameter fuzzing.

Each tool can still override with its own wordlist if required.

## 🔮 Future Enhancements

- Remote Resource Index API (REST/GraphQL).
- Smart caching with usage-based prefetch.
- Resource metrics: "most used", "last updated", etc.
- Tag-based search and semantic discovery.
- Signed update feeds from verified community sources.

---

**Next:** [Wordlist & Output Sharing Rules](10-wordlist-and-output-sharing.md)
