"""
Dashboard routes for project overview and key metrics.
"""

import glob
import json
import logging
import os
from collections import defaultdict
from datetime import datetime

from flask import Blueprint, render_template, request

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard_bp', __name__)


@dashboard_bp.route('/p/<pid>/dashboard')
def dashboard_page(pid):
    """Render the project dashboard with actionable metrics and KPIs."""
    try:
        # Get project data
        project_dir = f"ui_projects/{pid}"
        
        # Check for fresh parameter
        fresh = request.args.get('fresh') == '1'
        
        # Compute high-value KPIs
        metrics = _compute_dashboard_metrics(pid, project_dir, fresh=fresh)
        
        logger.info(f"DASHBOARD_VIEW pid={pid} coverage={metrics['coverage']['tested_pct']:.1f}% findings={metrics['findings']['total']}")
        
        return render_template('dashboard.html',
                             pid=pid,
                             active_nav='dashboard',
                             metrics=metrics)
    
    except Exception as e:
        logger.error(f"DASHBOARD_ERROR pid={pid} error={str(e)}")
        return render_template('dashboard.html',
                             pid=pid,
                             active_nav='dashboard',
                             metrics=_get_empty_metrics(),
                             error=str(e))


def _compute_dashboard_metrics(pid, project_dir, fresh=False):
    """Compute high-value KPIs for actionable dashboard metrics."""
    metrics = {
        'coverage': {'tested_pct': 0.0, 'tested': 0, 'total': 0},
        'findings': {'total': 0, 'new_24h': 0, 'new_7d': 0},
        'vulns': {'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}, 'total': 0},
        'detectors': {'top': []},
        'endpoints': {'top': []},
        'runs': {'last_run_at': None, 'runs_last_7d': 0, 'avg_findings_per_run': 0.0, 'worst_severity_last_run': 'info'},
        'mttr': {'days': 0}  # TODO: implement when status tracking is added
    }
    
    try:
        # 1. Coverage: tested endpoints / total endpoints
        endpoints_dir = f"{project_dir}/endpoints"
        if os.path.exists(endpoints_dir):
            endpoint_files = glob.glob(f"{endpoints_dir}/*.json")
            metrics['coverage']['total'] = len(endpoint_files)
            
            # Count tested endpoints (have ≥1 run in their dossier)
            tested_count = 0
            for endpoint_file in endpoint_files:
                try:
                    with open(endpoint_file, 'r') as f:
                        dossier = json.load(f)
                        if dossier.get('runs') and len(dossier['runs']) > 0:
                            tested_count += 1
                except:
                    continue
            
            metrics['coverage']['tested'] = tested_count
            if metrics['coverage']['total'] > 0:
                metrics['coverage']['tested_pct'] = (tested_count / metrics['coverage']['total']) * 100
        
        # 2. Findings: total, new_24h, new_7d
        findings_file = f"{project_dir}.findings.json"
        if os.path.exists(findings_file):
            with open(findings_file, 'r') as f:
                findings = json.load(f)
                metrics['findings']['total'] = len(findings)
                
                # Count by severity
                for finding in findings:
                    sev = finding.get('severity', 'info')
                    if sev in metrics['vulns']['by_severity']:
                        metrics['vulns']['by_severity'][sev] += 1
                
                metrics['vulns']['total'] = len(findings)
                
                # Count new findings by time window
                now = datetime.now()
                for finding in findings:
                    created_at = finding.get('created_at', '')
                    if created_at:
                        try:
                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            days_ago = (now - created_dt).days
                            if days_ago <= 1:
                                metrics['findings']['new_24h'] += 1
                            if days_ago <= 7:
                                metrics['findings']['new_7d'] += 1
                        except:
                            continue
        
        # 3. Top detectors and endpoints (use vulns summary for efficiency)
        if fresh:
            try:
                from routes.vulns import _compute_vulns_summary
                vulns = _compute_vulns_summary(pid)
            except:
                vulns = []
        else:
            vulns_file = f"{project_dir}/indexes/vulns_summary.json"
            if os.path.exists(vulns_file):
                try:
                    with open(vulns_file, 'r') as f:
                        vulns = json.load(f)
                except:
                    vulns = []
            else:
                vulns = []
        
        # Top detectors by distinct endpoints impacted
        detector_stats = defaultdict(lambda: {'endpoints': set(), 'occurrences': 0, 'worst_severity': 'info'})
        endpoint_stats = defaultdict(lambda: {'vulns': set(), 'last_seen_at': None, 'worst_severity': 'info'})
        
        for vuln in vulns:
            detector_id = vuln.get('detector_id', 'unknown')
            endpoint_key = vuln.get('endpoint_key', '')
            severity = vuln.get('worst_severity', 'info')
            occurrences = vuln.get('occurrences', 0)
            latest_at = vuln.get('latest_at', '')
            
            detector_stats[detector_id]['endpoints'].add(endpoint_key)
            detector_stats[detector_id]['occurrences'] += occurrences
            if _severity_rank(severity) < _severity_rank(detector_stats[detector_id]['worst_severity']):
                detector_stats[detector_id]['worst_severity'] = severity
            
            endpoint_stats[endpoint_key]['vulns'].add(detector_id)
            if _severity_rank(severity) < _severity_rank(endpoint_stats[endpoint_key]['worst_severity']):
                endpoint_stats[endpoint_key]['worst_severity'] = severity
            if latest_at and (not endpoint_stats[endpoint_key]['last_seen_at'] or latest_at > endpoint_stats[endpoint_key]['last_seen_at']):
                endpoint_stats[endpoint_key]['last_seen_at'] = latest_at
        
        # Sort and limit top detectors
        top_detectors = sorted(detector_stats.items(), 
                              key=lambda x: len(x[1]['endpoints']), 
                              reverse=True)[:5]
        metrics['detectors']['top'] = [
            {
                'id': detector_id,
                'endpoints': len(stats['endpoints']),
                'occurrences': stats['occurrences'],
                'worst_severity': stats['worst_severity']
            }
            for detector_id, stats in top_detectors
        ]
        
        # Sort and limit top endpoints
        top_endpoints = sorted(endpoint_stats.items(),
                              key=lambda x: len(x[1]['vulns']),
                              reverse=True)[:5]
        metrics['endpoints']['top'] = []
        for endpoint_key, stats in top_endpoints:
            # Parse endpoint key
            parts = endpoint_key.split(' ', 1)
            method = parts[0] if len(parts) > 0 else 'GET'
            url = parts[1] if len(parts) > 1 else ''
            
            # Extract path from URL
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                path = parsed.path or '/'
            except:
                path = '/'
            
            metrics['endpoints']['top'].append({
                'method': method,
                'path': path,
                'endpoint_key': endpoint_key,
                'vulns': len(stats['vulns']),
                'last_seen_at': stats['last_seen_at'],
                'worst_severity': stats['worst_severity']
            })
        
        # 4. Run health metrics
        runs_dir = f"{project_dir}/runs"
        if os.path.exists(runs_dir):
            run_files = glob.glob(f"{runs_dir}/*.json")
            
            if run_files:
                # Sort by modification time (newest first)
                run_files.sort(key=os.path.getmtime, reverse=True)
                
                # Last run
                latest_run_file = run_files[0]
                with open(latest_run_file, 'r') as f:
                    latest_run = json.load(f)
                    metrics['runs']['last_run_at'] = latest_run.get('started_at')
                    
                    # Worst severity from last run
                    worst_sev = 'info'
                    for result in latest_run.get('results', []):
                        severity_counts = result.get('severity_counts', {})
                        severities = ['critical', 'high', 'medium', 'low', 'info']
                        for sev in severities:
                            if severity_counts.get(sev, 0) > 0:
                                if _severity_rank(sev) < _severity_rank(worst_sev):
                                    worst_sev = sev
                                break
                    metrics['runs']['worst_severity_last_run'] = worst_sev
                
                # Runs last 7 days and avg findings per run
                now = datetime.now()
                runs_last_7d = 0
                total_findings_last_10 = 0
                runs_processed = 0
                
                for run_file in run_files[:10]:  # Last 10 runs for avg
                    try:
                        with open(run_file, 'r') as f:
                            run_data = json.load(f)
                            
                        # Check if run is within last 7 days
                        started_at = run_data.get('started_at', '')
                        if started_at:
                            try:
                                run_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                                if (now - run_dt).days <= 7:
                                    runs_last_7d += 1
                            except:
                                pass
                        
                        # Count findings in this run
                        run_findings = 0
                        for result in run_data.get('results', []):
                            severity_counts = result.get('severity_counts', {})
                            run_findings += sum(severity_counts.values())
                        
                        total_findings_last_10 += run_findings
                        runs_processed += 1
                        
                    except:
                        continue
                
                metrics['runs']['runs_last_7d'] = runs_last_7d
                if runs_processed > 0:
                    metrics['runs']['avg_findings_per_run'] = total_findings_last_10 / runs_processed
        
    except Exception as e:
        logger.error(f"DASHBOARD_METRICS_ERROR pid={pid} error={str(e)}")
    
    return metrics


def _severity_rank(severity):
    """Get numeric rank for severity comparison (lower = worse)."""
    ranks = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    return ranks.get(severity.lower(), 4)


def _get_empty_metrics():
    """Return empty metrics structure for error cases."""
    return {
        'coverage': {'tested_pct': 0.0, 'tested': 0, 'total': 0},
        'findings': {'total': 0, 'new_24h': 0, 'new_7d': 0},
        'vulns': {'by_severity': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0, 'info': 0}, 'total': 0},
        'detectors': {'top': []},
        'endpoints': {'top': []},
        'runs': {'last_run_at': None, 'runs_last_7d': 0, 'avg_findings_per_run': 0.0, 'worst_severity_last_run': 'info'},
        'mttr': {'days': 0}
    }


