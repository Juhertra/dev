from flask import Response, render_template, request


def register_reports_routes(bp):
    """Register reports-related routes on the given blueprint."""

    @bp.route("/p/<pid>/reports")
    def reports_page(pid: str):
        from reporting import SecurityReporter
        from store import get_project_name
        try:
            reporter = SecurityReporter(pid)
            executive_summary = reporter.generate_executive_summary()
            return render_template("reports.html", pid=pid, project_name=get_project_name(pid), summary=executive_summary)
        except Exception as e:
            return f"Error loading reports: {str(e)}", 500

    @bp.route("/p/<pid>/reports/export")
    def export_report(pid: str):
        from reporting import SecurityReporter
        try:
            format_type = request.args.get('format', 'json')
            if format_type not in ['json', 'csv', 'sarif', 'html']:
                return {"error": "Invalid format"}, 400
            reporter = SecurityReporter(pid)
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format_type}', delete=False, encoding='utf-8') as f:
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
                return {"error": "Export failed"}, 500
            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()
            import os
            os.unlink(temp_file)
            return Response(content, mimetype={
                'json': 'application/json', 'csv': 'text/csv', 'sarif': 'application/json', 'html': 'text/html'
            }[format_type], headers={'Content-Disposition': f'attachment; filename=security_report_{pid}.{format_type}'})
        except Exception as e:
            return {"error": str(e)}, 500

    @bp.route("/p/<pid>/reports/summary")
    def report_summary(pid: str):
        from reporting import SecurityReporter
        try:
            reporter = SecurityReporter(pid)
            summary = reporter.generate_executive_summary()
            return summary
        except Exception as e:
            return {"error": str(e)}, 500


