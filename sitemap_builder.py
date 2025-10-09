# server/sitemap_builder.py
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple, TypedDict

# Stage 4: Light caching
# Try to import cache decorator with fallback
try:
    from cache import cached, invalidate_cache
except ImportError:
    # Fallback decorator if cache is not available
    def cached(ttl_seconds=60):
        def decorator(func):
            return func
        return decorator
    def invalidate_cache(pattern=None):
        pass

SEG_RE = re.compile(r'[/{]+')

def _normalize_path(path: str) -> str:
    """Normalize root and slashes, preserving parameterized paths."""
    p = path.strip()
    if not p:
        return "/"
    
    # Don't normalize parameterized paths - keep them as-is
    if '{' in p and '}' in p:
        return p
    
    # For non-parameterized paths, normalize slashes
    p = "/" + "/".join(s for s in SEG_RE.split(p) if s)
    return p if p else "/"

def _split_segments(path: str) -> List[str]:
    """Split path into segments, preserving {param} segments and the root /."""
    p = path.strip()
    if not p or p == '/': 
        return ['/']
    if not p.startswith('/'):
        p = '/' + p
    # keep {param} segments intact; no trimming of braces
    return [seg for seg in p.split('/') if seg != '']


def _paths_match(actual_path: str, spec_path: str) -> bool:
    """Check if an actual path matches a spec path (including parameterized paths)."""
    if actual_path == spec_path:
        return True
    
    # Handle parameterized paths like /pet/{petId}
    if '{' in spec_path and '}' in spec_path:
        # Split both paths into segments
        actual_segments = actual_path.strip('/').split('/')
        spec_segments = spec_path.strip('/').split('/')
        
        # Must have same number of segments
        if len(actual_segments) != len(spec_segments):
            return False
        
        # Check each segment
        for actual_seg, spec_seg in zip(actual_segments, spec_segments):
            # If spec segment is a parameter (starts with { and ends with })
            if spec_seg.startswith('{') and spec_seg.endswith('}'):
                # Any actual segment matches a parameter
                continue
            # Otherwise, segments must match exactly
            elif actual_seg != spec_seg:
                return False
        
        return True
    
    return False

class VulnCounts(TypedDict, total=False):
    total: int
    critical: int
    high: int
    medium: int
    low: int

class EndpointInfo(TypedDict, total=False):
    method: str
    path: str
    full_url: Optional[str]
    base: Optional[str]
    spec_id: str
    index: int
    status: Optional[int]
    vulns: Optional[VulnCounts]
    retired: Optional[Dict[str, str]]  # Retirement status info

class NodeStats(TypedDict):
    endpoints: int
    untested: int
    vulns: int

class SiteMapNode(TypedDict):
    segment: str
    children: List['SiteMapNode']
    endpoints: List[EndpointInfo]
    stats: NodeStats

def _calculate_node_stats(node: Dict[str, Any]) -> NodeStats:
    """Calculate stats for a node including all its descendants."""
    # Start with direct endpoints
    direct_endpoints = len(node["endpoints"])
    direct_tested = len([e for e in node["endpoints"] if e.get("status") is not None])
    direct_untested = direct_endpoints - direct_tested
    direct_vulns = sum(e["vulns"]["total"] if e.get("vulns") and isinstance(e["vulns"], dict) else 0 for e in node["endpoints"])
    
    # Add stats from children
    child_endpoints = 0
    child_untested = 0
    child_vulns = 0
    
    for child in node["children"]:
        child_stats = _calculate_node_stats(child)
        child_endpoints += child_stats["endpoints"]
        child_untested += child_stats["untested"]
        child_vulns += child_stats["vulns"]
    
    return {
        "endpoints": direct_endpoints + child_endpoints,
        "untested": direct_untested + child_untested,
        "vulns": direct_vulns + child_vulns
    }

def pick_server(spec: Dict) -> Optional[str]:
    """Extract server URL from spec."""
    # Try different ways to get the base URL
    if "base_url" in spec:
        return spec["base_url"]
    
    servers = spec.get("servers", [])
    if servers:
        return servers[0].get("url", "")
    
    # Try to get from the spec itself
    if "url" in spec:
        return spec["url"]
    
    return None

def iter_operations(spec: Dict, resolver=None) -> List[Dict]:
    """Extract operations from spec."""
    operations = []
    paths = spec.get("paths", {})
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
                operations.append({
                    "method": method.upper(),
                    "path": path,
                    "operation": operation
                })
    
    return operations

@cached(ttl_seconds=300)  # Cache for 5 minutes
def build_site_map(pid: str) -> List[SiteMapNode]:
    """Build complete site map from specs and findings."""
    from findings import get_findings
    from store import get_runtime, get_sends
    
    session, SPECS, QUEUE = get_runtime(pid)
    findings = get_findings(pid)
    sends = get_sends(pid)
    
    # Create a lookup for endpoint status from sends and findings
    endpoint_status = {}
    
    # First, get status from sends
    for send in sends:
        method = send.get("method", "")
        url = send.get("url", "")
        status = send.get("status")
        
        # Extract path from URL for matching
        if url:
            # Try to extract path from URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                full_path = parsed.path
                
                # Try to match against all possible base URLs
                for spec_id, spec in SPECS.items():
                    base_url = pick_server(spec)
                    if base_url:
                        # Extract path from base_url
                        base_parsed = urlparse(base_url)
                        base_path = base_parsed.path
                        
                        if full_path.startswith(base_path):
                            # Remove base path to get the endpoint path
                            endpoint_path = full_path[len(base_path):]
                            
                            # Try to match against spec operations (including parameterized ones)
                            matched = False
                            for op in spec.get("ops", []):
                                spec_path = op.get("path", "")
                                if _paths_match(endpoint_path, spec_path):
                                    key = (method, spec_path)  # Use spec path, not actual path
                                    endpoint_status[key] = status
                                    matched = True
                                    break
                            
                            if matched:
                                break
            except:
                pass
    
    # Then, get status from findings (as fallback for endpoints not in sends)
    for finding in findings:
        method = finding.get("method", "")
        url = finding.get("url", "")
        status = finding.get("status")
        
        # Extract path from URL for matching
        if url:
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                full_path = parsed.path
                
                # Try to match against all possible base URLs
                for spec_id, spec in SPECS.items():
                    base_url = pick_server(spec)
                    if base_url:
                        # Extract path from base_url
                        base_parsed = urlparse(base_url)
                        base_path = base_parsed.path
                        
                    if full_path.startswith(base_path):
                        # Remove base path to get the endpoint path
                        endpoint_path = full_path[len(base_path):]
                        
                        # Try to match against spec operations (including parameterized ones)
                        matched = False
                        for op in spec.get("ops", []):
                            spec_path = op.get("path", "")
                            if _paths_match(endpoint_path, spec_path):
                                key = (method, spec_path)  # Use spec path, not actual path
                                # Only add if not already in endpoint_status (sends take priority)
                                if key not in endpoint_status:
                                    endpoint_status[key] = status
                                matched = True
                                break
                        
                        if matched:
                            break
            except:
                pass
    
    # Index vulnerabilities by method+path with deduplication
    vix: Dict[Tuple[str, str], VulnCounts] = defaultdict(lambda: {"total": 0, "critical": 0, "high": 0, "medium": 0, "low": 0})
    
    # Group findings by endpoint and vulnerability type to deduplicate
    endpoint_vulns: Dict[Tuple[str, str], Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
    
    for f in findings:
        # Handle different finding structures
        method = f.get("method", "")
        url = f.get("url", "")
        
        if not url:
            continue  # Skip findings without URL
            
        # Extract path from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            full_path = parsed.path
            
            # Try to match against all possible base URLs
            for spec_id, spec in SPECS.items():
                base_url = pick_server(spec)
                if base_url:
                    # Extract path from base_url
                    base_parsed = urlparse(base_url)
                    base_path = base_parsed.path
                    
                    if full_path.startswith(base_path):
                        # Remove base path to get the endpoint path
                        endpoint_path = full_path[len(base_path):]
                        
                        # Try to match against spec operations (including parameterized ones)
                        matched = False
                        for op in spec.get("ops", []):
                            spec_path = op.get("path", "")
                            if _paths_match(endpoint_path, spec_path):
                                endpoint_key = (method, spec_path)  # Use spec path, not actual path
                                
                                # Create a unique vulnerability key based on title, detector, and severity
                                vuln_key = (
                                    f.get("title", ""),
                                    f.get("detector_id", ""),
                                    f.get("severity", "low")
                                )
                                
                                # Only count unique vulnerabilities (deduplicate)
                                if vuln_key not in endpoint_vulns[endpoint_key]:
                                    endpoint_vulns[endpoint_key][vuln_key] = f
                                    vix[endpoint_key]["total"] += 1
                                    severity = f.get("severity", "low")
                                    if severity in vix[endpoint_key]:
                                        vix[endpoint_key][severity] += 1
                                matched = True
                                break
                        
                        if matched:
                            break
        except:
            continue  # Skip if URL parsing fails
    
    roots: List[SiteMapNode] = []

    for spec_id, spec in SPECS.items():
        base = pick_server(spec) or "unknown"
        base_node: SiteMapNode = {
            "segment": base,
            "children": [],
            "endpoints": [],
            "stats": {"endpoints": 0, "untested": 0, "vulns": 0},
        }

        # Get operations from spec
        operations = spec.get("ops", [])
        
        # Build hierarchical structure with proper deduplication
        path_groups = {}
        seen_endpoints = set()  # Dedupe by method + normalized_path + base_url
        
        for idx, op in enumerate(operations):
            method = op.get("method", "")
            path = _normalize_path(op.get("path", ""))
            segs = _split_segments(path)
            
            # Create deduplication key
            dedupe_key = (method, path, base)
            if dedupe_key in seen_endpoints:
                continue
            seen_endpoints.add(dedupe_key)
            
            # Create a simple grouping key
            if not segs:
                group_key = "/"
            else:
                group_key = f"/{segs[0]}"
            
            if group_key not in path_groups:
                path_groups[group_key] = []
            
            key = (method, path)
            
            # Check for retirement status from dossier
            retired_info = None
            try:
                from utils.endpoints import endpoint_key
                canonical_key = endpoint_key(method, base, path)
                from utils.dossier_management import load_endpoint_dossier
                dossier = load_endpoint_dossier(pid, canonical_key)
                if dossier and dossier.get("retired"):
                    retired_info = dossier["retired"]
            except Exception:
                pass
            
            ep: EndpointInfo = {
                "method": method,
                "path": path,
                "full_url": f"{base}{path}" if base and path else None,
                "base": base,
                "spec_id": str(spec_id),
                "index": idx,  # Add the operation index
                "status": endpoint_status.get(key),  # Get status from sends data
                "vulns": vix.get(key) or None,
                "retired": retired_info,
            }
            path_groups[group_key].append(ep)
        
        # Create child nodes for each path group
        for group_path, endpoints in path_groups.items():
            child_node: SiteMapNode = {
                "segment": group_path,
                "children": [],
                "endpoints": endpoints,
                "stats": {"endpoints": 0, "untested": 0, "vulns": 0},
            }
            
            # Calculate stats for this child node
            child_node["stats"] = _calculate_node_stats(child_node)
            base_node["children"].append(child_node)
        
        # Calculate stats for base node using recursive calculation
        base_node["stats"] = _calculate_node_stats(base_node)
        
        roots.append(base_node)

    return roots
