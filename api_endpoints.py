#!/usr/bin/env python3
"""
API Endpoints - REST API for external integrations.
"""
import os
import time
from functools import wraps

from flask import Blueprint, Response, current_app, jsonify, request

from detectors.enhanced_pattern_engine import EnhancedPatternEngine
from findings import (
    analyze_and_record,
    count_findings,
    get_findings,
    group_findings_for_ui,
)
from reporting import SecurityReporter

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# Simple rate limiting storage
_rate_limit_storage = {}

def require_api_key(f):
    """Decorator to require API key authentication with rate limiting."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key required"}), 401
        
        # Simple API key validation (in production, use proper authentication)
        valid_keys = current_app.config.get('API_KEYS', [])
        if api_key not in valid_keys:
            return jsonify({"error": "Invalid API key"}), 401
        
        # Simple rate limiting (100 requests per minute per API key)
        current_time = time.time()
        minute_window = int(current_time // 60)
        rate_key = f"{api_key}:{minute_window}"
        
        if rate_key not in _rate_limit_storage:
            _rate_limit_storage[rate_key] = 0
        
        _rate_limit_storage[rate_key] += 1
        
        # Clean up old entries
        for key in list(_rate_limit_storage.keys()):
            if not key.endswith(f":{minute_window}"):
                del _rate_limit_storage[key]
        
        if _rate_limit_storage[rate_key] > 100:
            return jsonify({"error": "Rate limit exceeded"}), 429
        
        return f(*args, **kwargs)
    return decorated_function

def validate_project_id(project_id: str) -> bool:
    """Validate that project ID exists."""
    from store import list_projects
    if not project_id or not project_id.strip():
        return False
    
    # Check if project actually exists
    projects = list_projects()
    return any(p["id"] == project_id for p in projects)

# ===========================
# Project Management API
# ===========================

@api_bp.route("/projects", methods=["GET"])
@require_api_key
def list_projects():
    """List all available projects."""
    try:
        # This would integrate with actual project storage
        projects = [
            {"id": "test-project", "name": "Test Project", "created": "2024-01-01"},
            {"id": "demo-project", "name": "Demo Project", "created": "2024-01-02"}
        ]
        return jsonify({"projects": projects})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>", methods=["GET"])
@require_api_key
def get_project(project_id: str):
    """Get project details."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        # This would get actual project data
        project = {
            "id": project_id,
            "name": f"Project {project_id}",
            "created": "2024-01-01",
            "findings_count": count_findings(project_id)
        }
        return jsonify(project)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Findings API
# ===========================

@api_bp.route("/projects/<project_id>/findings", methods=["GET"])
@require_api_key
def get_project_findings(project_id: str):
    """Get all findings for a project."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        findings = get_findings(project_id)
        
        # Apply filters
        severity = request.args.get('severity')
        confidence_min = request.args.get('confidence_min', type=int)
        confidence_max = request.args.get('confidence_max', type=int)
        cwe = request.args.get('cwe')
        owasp = request.args.get('owasp')
        
        filtered_findings = findings
        
        if severity:
            filtered_findings = [f for f in filtered_findings if f.get('severity') == severity]
        
        if confidence_min is not None:
            filtered_findings = [f for f in filtered_findings if f.get('confidence', 50) >= confidence_min]
        
        if confidence_max is not None:
            filtered_findings = [f for f in filtered_findings if f.get('confidence', 50) <= confidence_max]
        
        if cwe:
            filtered_findings = [f for f in filtered_findings if f.get('cwe') == cwe]
        
        if owasp:
            filtered_findings = [f for f in filtered_findings if f.get('owasp') == owasp or f.get('owasp_api') == owasp]
        
        return jsonify({
            "project_id": project_id,
            "total_findings": len(filtered_findings),
            "findings": filtered_findings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/findings/<finding_id>", methods=["GET"])
@require_api_key
def get_finding(project_id: str, finding_id: str):
    """Get a specific finding by ID."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        findings = get_findings(project_id)
        finding = next((f for f in findings if f.get('id') == finding_id), None)
        
        if not finding:
            return jsonify({"error": "Finding not found"}), 404
        
        return jsonify(finding)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/findings", methods=["POST"])
@require_api_key
def create_finding(project_id: str):
    """Create a new finding."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        # Validate required fields
        required_fields = ['title', 'severity', 'url', 'method']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create finding (this would integrate with actual storage)
        finding = {
            "id": f"api_{len(get_findings(project_id)) + 1}",
            "title": data['title'],
            "severity": data['severity'],
            "confidence": data.get('confidence', 50),
            "cwe": data.get('cwe'),
            "cvss": data.get('cvss'),
            "owasp": data.get('owasp'),
            "owasp_api": data.get('owasp_api'),
            "subcategory": data.get('subcategory'),
            "url": data['url'],
            "method": data['method'],
            "evidence": data.get('evidence', ''),
            "detector_id": data.get('detector_id', 'api'),
            "timestamp": data.get('timestamp', ''),
            "status": data.get('status', 'new')
        }
        
        # This would save to actual storage
        # For now, just return the finding
        return jsonify(finding), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/findings/<finding_id>", methods=["PUT"])
@require_api_key
def update_finding(project_id: str, finding_id: str):
    """Update a finding."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        findings = get_findings(project_id)
        finding = next((f for f in findings if f.get('id') == finding_id), None)
        
        if not finding:
            return jsonify({"error": "Finding not found"}), 404
        
        # Update finding fields
        for key, value in data.items():
            if key in finding:
                finding[key] = value
        
        # This would save to actual storage
        return jsonify(finding)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/findings/<finding_id>", methods=["DELETE"])
@require_api_key
def delete_finding(project_id: str, finding_id: str):
    """Delete a finding."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        findings = get_findings(project_id)
        finding = next((f for f in findings if f.get('id') == finding_id), None)
        
        if not finding:
            return jsonify({"error": "Finding not found"}), 404
        
        # This would delete from actual storage
        return jsonify({"message": "Finding deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Analysis API
# ===========================

@api_bp.route("/projects/<project_id>/analyze", methods=["POST"])
@require_api_key
def analyze_request(project_id: str):
    """Analyze a request/response pair for security issues."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON data required"}), 400
        
        # Validate required fields
        if 'request' not in data or 'response' not in data:
            return jsonify({"error": "Request and response data required"}), 400
        
        # Analyze the request/response
        findings = analyze_and_record(
            project_id,
            data['request'],
            data['response']
        )
        
        return jsonify({
            "project_id": project_id,
            "findings_count": len(findings),
            "findings": findings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Patterns API
# ===========================

@api_bp.route("/projects/<project_id>/patterns", methods=["GET"])
@require_api_key
def get_project_patterns(project_id: str):
    """Get all patterns for a project."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        engine = EnhancedPatternEngine(base_dir, project_id)
        
        patterns = engine.list_patterns()
        
        # Apply filters
        severity = request.args.get('severity')
        enabled = request.args.get('enabled', type=bool)
        pack_type = request.args.get('pack_type')
        
        filtered_patterns = patterns
        
        if severity:
            filtered_patterns = [p for p in filtered_patterns if p.get('severity') == severity]
        
        if enabled is not None:
            filtered_patterns = [p for p in filtered_patterns if p.get('enabled') == enabled]
        
        if pack_type:
            filtered_patterns = [p for p in filtered_patterns if p.get('pack_type') == pack_type]
        
        return jsonify({
            "project_id": project_id,
            "total_patterns": len(filtered_patterns),
            "patterns": filtered_patterns
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/patterns/<pattern_id>/test", methods=["POST"])
@require_api_key
def test_pattern(project_id: str, pattern_id: str):
    """Test a pattern against text."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Text data required"}), 400
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        engine = EnhancedPatternEngine(base_dir, project_id)
        
        result = engine.test_pattern_against_text(pattern_id, data['text'])
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/patterns/<pattern_id>/toggle", methods=["PUT"])
@require_api_key
def toggle_pattern(project_id: str, pattern_id: str):
    """Enable/disable a pattern."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        data = request.get_json()
        if not data or 'enabled' not in data:
            return jsonify({"error": "Enabled status required"}), 400
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        engine = EnhancedPatternEngine(base_dir, project_id)
        
        success = engine.toggle_pattern(pattern_id, data['enabled'])
        
        if success:
            return jsonify({"success": True, "enabled": data['enabled']})
        else:
            return jsonify({"error": "Pattern not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Reports API
# ===========================

@api_bp.route("/projects/<project_id>/reports/summary", methods=["GET"])
@require_api_key
def get_report_summary(project_id: str):
    """Get executive summary report."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        reporter = SecurityReporter(project_id)
        summary = reporter.generate_executive_summary()
        
        return jsonify(summary)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/reports/technical", methods=["GET"])
@require_api_key
def get_technical_report(project_id: str):
    """Get detailed technical report."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        reporter = SecurityReporter(project_id)
        report = reporter.generate_technical_report()
        
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route("/projects/<project_id>/reports/export", methods=["GET"])
@require_api_key
def export_report(project_id: str):
    """Export report in various formats."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        format_type = request.args.get('format', 'json')
        if format_type not in ['json', 'csv', 'sarif', 'html']:
            return jsonify({"error": "Invalid format"}), 400
        
        reporter = SecurityReporter(project_id)
        
        # Create temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format_type}', delete=False) as f:
            temp_file = f.name
        
        success = False
        if format_type == 'json':
            success = reporter.export_findings_json(temp_file)
        elif format_type == 'csv':
            success = reporter.export_findings_csv(temp_file)
        elif format_type == 'sarif':
            success = reporter.export_sarif(temp_file)
        elif format_type == 'html':
            success = reporter.generate_html_report(temp_file)
        
        if not success:
            return jsonify({"error": "Export failed"}), 500
        
        # Read the file and return as response
        with open(temp_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Clean up
        os.unlink(temp_file)
        
        from flask import Response
        return Response(
            content,
            mimetype={
                'json': 'application/json',
                'csv': 'text/csv',
                'sarif': 'application/json',
                'html': 'text/html'
            }[format_type],
            headers={
                'Content-Disposition': f'attachment; filename=security_report_{project_id}.{format_type}'
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Statistics API
# ===========================

@api_bp.route("/projects/<project_id>/statistics", methods=["GET"])
@require_api_key
def get_project_statistics(project_id: str):
    """Get project statistics."""
    try:
        if not validate_project_id(project_id):
            return jsonify({"error": "Invalid project ID"}), 400
        
        findings = get_findings(project_id)
        grouped = group_findings_for_ui(findings, project_id)
        
        # Calculate statistics
        total_findings = len(findings)
        severity_counts = {}
        for finding in findings:
            sev = finding.get('severity', 'info')
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        cwe_counts = {}
        for finding in findings:
            cwe = finding.get('cwe')
            if cwe:
                cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1
        
        owasp_counts = {}
        for finding in findings:
            owasp = finding.get('owasp') or finding.get('owasp_api')
            if owasp:
                owasp_counts[owasp] = owasp_counts.get(owasp, 0) + 1
        
        statistics = {
            "project_id": project_id,
            "total_findings": total_findings,
            "severity_breakdown": severity_counts,
            "cwe_breakdown": cwe_counts,
            "owasp_breakdown": owasp_counts,
            "owasp_counts": grouped.get("counts", {}),
            "unique_endpoints": len(set(f.get('url', '') for f in findings)),
            "unique_vulnerabilities": len(set(f.get('title', '') for f in findings))
        }
        
        return jsonify(statistics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================
# Health Check
# ===========================

@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    })

# ===========================
# Error Handlers
# ===========================

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@api_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"error": "Method not allowed"}), 405

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Phase 3: Metrics endpoint
@api_bp.route("/metrics")
def prometheus_metrics():
    """
    Prometheus metrics endpoint. 
    Returns metrics in Prometheus text format when ENABLE_METRICS=1.
    Returns 404 when metrics are disabled.
    """
    from metrics import export_prometheus_metrics, should_collect_metrics
    
    if not should_collect_metrics():
        return jsonify({"error": "Metrics disabled"}), 404
    
    try:
        metrics_text = export_prometheus_metrics()
        return Response(
            metrics_text,
            mimetype='text/plain; version=0.0.4; charset=utf-8',
            headers={
                'X-Server': 'Security Toolkit Phase 3',
                'Cache-Control': 'no-cache'
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error generating metrics: {e}")
        return jsonify({"error": "Failed to generate metrics"}), 500
