#!/usr/bin/env python3
"""
P6 - Analytics & Metrics Layer

Data aggregation and metrics computation for findings analytics and reporting.
"""

import json
import logging
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Import findings module
try:
    from findings import get_findings
except ImportError:
    # Fallback for testing
    def get_findings(pid: str) -> List[Dict[str, Any]]:
        return []


def get_metrics(pid: str) -> Dict[str, Any]:
    """
    Aggregate findings metrics for a given project ID.
    
    Args:
        pid: Project ID
        
    Returns:
        Dictionary containing computed metrics
    """
    try:
        # Check cache first
        cache_file = f"ui_projects/{pid}/indexes/metrics_summary.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached_metrics = json.load(f)
                # Check if cache is recent (within 1 hour)
                cache_time = cached_metrics.get('_cache_timestamp', 0)
                if time.time() - cache_time < 3600:  # 1 hour
                    logger.info(f"METRICS_CACHE_HIT pid={pid}")
                    return cached_metrics
            except (json.JSONDecodeError, KeyError):
                logger.warning(f"METRICS_CACHE_CORRUPT pid={pid}")
        
        # Compute fresh metrics
        logger.info(f"METRICS_COMPUTE_START pid={pid}")
        metrics = _compute_metrics(pid)
        
        # Cache the results
        metrics['_cache_timestamp'] = time.time()
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"METRICS_COMPUTE_OK pid={pid} total={metrics.get('total_findings', 0)}")
        return metrics
        
    except Exception as e:
        logger.error(f"METRICS_COMPUTE_ERROR pid={pid} error={str(e)}")
        return _get_default_metrics()


def _compute_metrics(pid: str) -> Dict[str, Any]:
    """Compute metrics from findings data."""
    try:
        from findings import get_findings
        
        # Get all findings for the project
        findings = get_findings(pid)
        
        if not findings:
            return _get_default_metrics()
        
        # Initialize counters
        total_findings = len(findings)
        active_count = 0
        resolved_count = 0
        false_positives_count = 0
        risk_accepted_count = 0
        suppressed_count = 0
        
        severity_counts = defaultdict(int)
        tag_counts = Counter()
        owner_counts = Counter()
        fix_times = []
        
        # Process each finding
        for finding in findings:
            triage = finding.get('triage', {})
            status = triage.get('status', 'open')
            
            # Check if suppressed
            suppress = triage.get('suppress', {})
            is_suppressed = _is_suppressed(suppress)
            
            if is_suppressed:
                suppressed_count += 1
                continue  # Skip suppressed findings in other counts
            
            # Count by status
            if status in ['open', 'in_progress']:
                active_count += 1
            elif status == 'resolved':
                resolved_count += 1
            elif status == 'false_positive':
                false_positives_count += 1
            elif status == 'risk_accepted':
                risk_accepted_count += 1
            
            # Severity breakdown
            severity = finding.get('severity', 'info')
            severity_counts[severity] += 1
            
            # Tags
            tags = triage.get('tags', [])
            for tag in tags:
                tag_counts[tag] += 1
            
            # Owner tracking
            owner = triage.get('owner')
            if owner:
                owner_counts[owner] += 1
            
            # Fix time calculation (for resolved findings)
            if status == 'resolved':
                fix_time = _calculate_fix_time(finding)
                if fix_time is not None:
                    fix_times.append(fix_time)
        
        # Compute derived metrics
        avg_fix_time_days = sum(fix_times) / len(fix_times) if fix_times else 0
        
        # Top tags (limit to 5)
        most_common_tags = [{'tag': tag, 'count': count} for tag, count in tag_counts.most_common(5)]
        
        # Top owners (by active findings)
        top_owners = []
        for owner in owner_counts:
            owner_active = sum(1 for f in findings 
                             if f.get('triage', {}).get('owner') == owner 
                             and f.get('triage', {}).get('status') in ['open', 'in_progress']
                             and not _is_suppressed(f.get('triage', {}).get('suppress', {})))
            if owner_active > 0:
                top_owners.append({'owner': owner, 'active': owner_active, 'total': owner_counts[owner]})
        
        top_owners.sort(key=lambda x: x['active'], reverse=True)
        
        # 30-day trend
        trend_30d = _compute_trend_30d(findings)
        
        # Severity breakdown (formatted)
        severity_breakdown = {
            'critical': severity_counts.get('critical', 0),
            'high': severity_counts.get('high', 0),
            'medium': severity_counts.get('medium', 0),
            'low': severity_counts.get('low', 0),
            'info': severity_counts.get('info', 0)
        }
        
        return {
            'total_findings': total_findings,
            'active': active_count,
            'resolved': resolved_count,
            'false_positives': false_positives_count,
            'risk_accepted': risk_accepted_count,
            'suppressed': suppressed_count,
            'avg_fix_time_days': round(avg_fix_time_days, 1),
            'most_common_tags': most_common_tags,
            'top_owners': top_owners[:5],  # Top 5 owners
            'trend_30d': trend_30d,
            'severity_breakdown': severity_breakdown,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"METRICS_COMPUTE_ERROR pid={pid} error={str(e)}")
        return _get_default_metrics()


def _is_suppressed(suppress: Dict[str, Any]) -> bool:
    """Check if a finding is currently suppressed."""
    if not suppress:
        return False
    
    until = suppress.get('until')
    if until:
        try:
            suppress_until = datetime.fromisoformat(until.replace('Z', '+00:00'))
            return suppress_until > datetime.now(timezone.utc)
        except ValueError:
            return False
    else:
        # No until date means permanent suppression
        return True


def _calculate_fix_time(finding: Dict[str, Any]) -> Optional[float]:
    """Calculate fix time in days for a resolved finding."""
    try:
        created_at = finding.get('created_at')
        if not created_at:
            return None
        
        # Look for resolution timestamp in notes
        notes = finding.get('triage', {}).get('notes', [])
        resolution_time = None
        
        for note in reversed(notes):  # Check most recent notes first
            if 'resolved' in note.get('text', '').lower():
                try:
                    resolution_time = datetime.fromisoformat(note['at'].replace('Z', '+00:00'))
                    break
                except ValueError:
                    continue
        
        if not resolution_time:
            # Fallback to finding creation time
            resolution_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        
        created_time = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        fix_time = (resolution_time - created_time).total_seconds() / (24 * 3600)  # Convert to days
        
        return fix_time if fix_time >= 0 else None
        
    except (ValueError, KeyError):
        return None


def _calculate_avg_fix_time(findings: List[Dict[str, Any]]) -> float:
    """Calculate average fix time for a list of findings."""
    fix_times = []
    for finding in findings:
        fix_time = _calculate_fix_time(finding)
        if fix_time is not None:
            fix_times.append(fix_time)
    
    if not fix_times:
        return 0.0
    
    return sum(fix_times) / len(fix_times)


def _compute_trend_30d(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compute 30-day trend data."""
    try:
        # Get date range (last 30 days)
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=29)
        
        # Initialize daily counters
        daily_data = {}
        current_date = start_date
        while current_date <= end_date:
            daily_data[current_date.isoformat()] = {'created': 0, 'resolved': 0}
            current_date += timedelta(days=1)
        
        # Process findings
        for finding in findings:
            created_at = finding.get('created_at')
            if not created_at:
                continue
            
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                if start_date <= created_date <= end_date:
                    daily_data[created_date.isoformat()]['created'] += 1
            except ValueError:
                continue
            
            # Check for resolution
            status = finding.get('triage', {}).get('status')
            if status == 'resolved':
                notes = finding.get('triage', {}).get('notes', [])
                for note in notes:
                    if 'resolved' in note.get('text', '').lower():
                        try:
                            resolved_date = datetime.fromisoformat(note['at'].replace('Z', '+00:00')).date()
                            if start_date <= resolved_date <= end_date:
                                daily_data[resolved_date.isoformat()]['resolved'] += 1
                            break
                        except ValueError:
                            continue
        
        # Convert to list format
        trend_data = []
        for day, counts in sorted(daily_data.items()):
            trend_data.append({
                'day': day,
                'created': counts['created'],
                'resolved': counts['resolved']
            })
        
        return trend_data
        
    except Exception as e:
        logger.error(f"TREND_COMPUTE_ERROR error={str(e)}")
        return []


def _get_default_metrics() -> Dict[str, Any]:
    """Return default metrics when computation fails."""
    return {
        'total_findings': 0,
        'active': 0,
        'resolved': 0,
        'false_positives': 0,
        'risk_accepted': 0,
        'suppressed': 0,
        'avg_fix_time_days': 0,
        'most_common_tags': [],
        'top_owners': [],
        'trend_30d': [],
        'severity_breakdown': {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0,
            'info': 0
        },
        'last_updated': datetime.now(timezone.utc).isoformat()
    }


def rebuild_metrics_cache(pid: str) -> None:
    """
    Recompute and persist metrics summary for a given project.
    
    Args:
        pid: Project ID
    """
    try:
        logger.info(f"METRICS_REBUILD_START pid={pid}")
        
        # Force recomputation by deleting cache
        cache_file = f"ui_projects/{pid}/indexes/metrics_summary.json"
        if os.path.exists(cache_file):
            os.remove(cache_file)
        
        # Recompute metrics
        metrics = get_metrics(pid)
        
        logger.info(f"METRICS_REBUILD_OK pid={pid} total={metrics.get('total_findings', 0)}")
        
    except Exception as e:
        logger.error(f"METRICS_REBUILD_FAIL pid={pid} error={str(e)}")


def get_filtered_metrics(pid: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get metrics with applied filters.
    
    Args:
        pid: Project ID
        filters: Dictionary of filters (status, owner, since, tag)
        
    Returns:
        Filtered metrics
    """
    try:
        findings = get_findings(pid)
        
        # Apply filters
        filtered_findings = []
        for finding in findings:
            # Status filter
            if 'status' in filters:
                triage_status = finding.get('triage', {}).get('status', 'open')
                if triage_status != filters['status']:
                    continue
            
            # Owner filter
            if 'owner' in filters:
                triage_owner = finding.get('triage', {}).get('owner')
                if triage_owner != filters['owner']:
                    continue
            
            # Date filter
            if 'since' in filters:
                created_at = finding.get('created_at')
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                        since_date = datetime.fromisoformat(filters['since']).date()
                        if created_date < since_date:
                            continue
                    except ValueError:
                        continue
            
            # Tag filter
            if 'tag' in filters:
                tags = finding.get('triage', {}).get('tags', [])
                if filters['tag'] not in tags:
                    continue
            
            filtered_findings.append(finding)
        
        # Compute metrics for filtered findings
        # This is a simplified version - in production you might want to cache filtered results
        return _compute_metrics_from_findings(filtered_findings)
        
    except Exception as e:
        logger.error(f"FILTERED_METRICS_ERROR pid={pid} error={str(e)}")
        return _get_default_metrics()


def _compute_metrics_from_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute metrics from a specific list of findings."""
    if not findings:
        return _get_default_metrics()
    
    # Basic counts
    total_findings = len(findings)
    active = sum(1 for f in findings if f.get('triage', {}).get('status') == 'open')
    resolved = sum(1 for f in findings if f.get('triage', {}).get('status') == 'resolved')
    false_positives = sum(1 for f in findings if f.get('triage', {}).get('status') == 'false_positive')
    risk_accepted = sum(1 for f in findings if f.get('triage', {}).get('status') == 'risk_accepted')
    suppressed = sum(1 for f in findings if _is_suppressed(f))
    
    # Calculate average fix time
    avg_fix_time_days = _calculate_avg_fix_time(findings)
    
    # Tag aggregation
    tag_counts = Counter()
    for finding in findings:
        tags = finding.get('triage', {}).get('tags', [])
        for tag in tags:
            tag_counts[tag] += 1
    
    most_common_tags = [{'tag': tag, 'count': count} for tag, count in tag_counts.most_common(10)]
    
    # Owner aggregation
    owner_counts = Counter()
    for finding in findings:
        owner = finding.get('triage', {}).get('owner')
        if owner:
            owner_counts[owner] += 1
    
    top_owners = [{'owner': owner, 'count': count} for owner, count in owner_counts.most_common(10)]
    
    # Severity breakdown
    severity_counts = Counter()
    for finding in findings:
        severity = finding.get('severity', 'unknown')
        severity_counts[severity] += 1
    
    severity_breakdown = {
        'critical': severity_counts.get('critical', 0),
        'high': severity_counts.get('high', 0),
        'medium': severity_counts.get('medium', 0),
        'low': severity_counts.get('low', 0),
        'info': severity_counts.get('info', 0)
    }
    
    # Trend data (simplified - just use creation dates)
    trend_30d = _compute_trend_30d(findings)
    
    return {
        'total_findings': total_findings,
        'active': active,
        'resolved': resolved,
        'false_positives': false_positives,
        'risk_accepted': risk_accepted,
        'suppressed': suppressed,
        'avg_fix_time_days': avg_fix_time_days,
        'most_common_tags': most_common_tags,
        'top_owners': top_owners,
        'trend_30d': trend_30d,
        'severity_breakdown': severity_breakdown
    }
