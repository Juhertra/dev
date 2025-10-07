#!/usr/bin/env python3
"""
P6 - Metrics Routes

REST endpoints for findings metrics and analytics dashboard.
"""

import json
from typing import Dict, Any
from flask import Blueprint, request, jsonify, render_template, current_app

from analytics_core.analytics import get_metrics, get_filtered_metrics


def register_metrics_routes(web_bp: Blueprint):
    """Register metrics API routes."""
    
    @web_bp.route('/p/<pid>/metrics')
    def project_metrics(pid: str):
        """Get project metrics in HTML or JSON format."""
        try:
            # Get filters from query parameters
            filters = {}
            if request.args.get('status'):
                filters['status'] = request.args.get('status')
            if request.args.get('owner'):
                filters['owner'] = request.args.get('owner')
            if request.args.get('since'):
                filters['since'] = request.args.get('since')
            if request.args.get('tag'):
                filters['tag'] = request.args.get('tag')
            
            # Get metrics (filtered if filters provided)
            if filters:
                metrics = get_filtered_metrics(pid, filters)
            else:
                metrics = get_metrics(pid)
            
            # Return JSON if requested
            if request.args.get('format') == 'json':
                return jsonify(metrics)
            
            # Return HTML template
            return render_template('metrics.html', pid=pid, metrics=metrics, filters=filters)
            
        except Exception as e:
            current_app.logger.error(f"METRICS_ROUTE_ERROR pid={pid} error={str(e)}")
            if request.args.get('format') == 'json':
                return jsonify({'error': str(e)}), 500
            return f"Error loading metrics: {str(e)}", 500
    
    @web_bp.route('/p/<pid>/metrics/export')
    def export_metrics(pid: str):
        """Export metrics in various formats."""
        try:
            export_format = request.args.get('format', 'json')
            
            if export_format not in ['json', 'csv', 'pdf']:
                return jsonify({'error': 'Invalid format. Use json, csv, or pdf'}), 400
            
            # Get metrics
            metrics = get_metrics(pid)
            
            if export_format == 'json':
                return jsonify(metrics)
            elif export_format == 'csv':
                # Generate CSV
                csv_content = _generate_csv_export(metrics)
                from flask import Response
                return Response(
                    csv_content,
                    mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=metrics_{pid}.csv'}
                )
            elif export_format == 'pdf':
                # Generate PDF
                pdf_content = _generate_pdf_export(metrics, pid)
                from flask import Response
                return Response(
                    pdf_content,
                    mimetype='application/pdf',
                    headers={'Content-Disposition': f'attachment; filename=metrics_{pid}.pdf'}
                )
                
        except Exception as e:
            current_app.logger.error(f"EXPORT_ERROR pid={pid} error={str(e)}")
            return jsonify({'error': str(e)}), 500


def _generate_csv_export(metrics: Dict[str, Any]) -> str:
    """Generate CSV export of metrics."""
    import csv
    import io
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['Metric', 'Value'])
    
    # Write metrics
    writer.writerow(['Total Findings', metrics.get('total_findings', 0)])
    writer.writerow(['Active', metrics.get('active', 0)])
    writer.writerow(['Resolved', metrics.get('resolved', 0)])
    writer.writerow(['False Positives', metrics.get('false_positives', 0)])
    writer.writerow(['Risk Accepted', metrics.get('risk_accepted', 0)])
    writer.writerow(['Suppressed', metrics.get('suppressed', 0)])
    writer.writerow(['Avg Fix Time (days)', metrics.get('avg_fix_time_days', 0)])
    
    # Severity breakdown
    severity = metrics.get('severity_breakdown', {})
    writer.writerow(['Critical', severity.get('critical', 0)])
    writer.writerow(['High', severity.get('high', 0)])
    writer.writerow(['Medium', severity.get('medium', 0)])
    writer.writerow(['Low', severity.get('low', 0)])
    writer.writerow(['Info', severity.get('info', 0)])
    
    # Top tags
    writer.writerow([])
    writer.writerow(['Top Tags'])
    for tag_data in metrics.get('most_common_tags', []):
        writer.writerow([tag_data['tag'], tag_data['count']])
    
    # Top owners
    writer.writerow([])
    writer.writerow(['Top Owners'])
    for owner_data in metrics.get('top_owners', []):
        writer.writerow([owner_data['owner'], owner_data['active'], owner_data['total']])
    
    return output.getvalue()


def _generate_pdf_export(metrics: Dict[str, Any], pid: str) -> bytes:
    """Generate PDF export of metrics."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph(f"Security Findings Metrics - Project {pid}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Summary table
        summary_data = [
            ['Metric', 'Value'],
            ['Total Findings', str(metrics.get('total_findings', 0))],
            ['Active', str(metrics.get('active', 0))],
            ['Resolved', str(metrics.get('resolved', 0))],
            ['False Positives', str(metrics.get('false_positives', 0))],
            ['Risk Accepted', str(metrics.get('risk_accepted', 0))],
            ['Suppressed', str(metrics.get('suppressed', 0))],
            ['Avg Fix Time (days)', str(metrics.get('avg_fix_time_days', 0))]
        ]
        
        summary_table = Table(summary_data)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 12))
        
        # Severity breakdown
        severity_title = Paragraph("Severity Breakdown", styles['Heading2'])
        story.append(severity_title)
        
        severity_data = [
            ['Severity', 'Count'],
            ['Critical', str(metrics.get('severity_breakdown', {}).get('critical', 0))],
            ['High', str(metrics.get('severity_breakdown', {}).get('high', 0))],
            ['Medium', str(metrics.get('severity_breakdown', {}).get('medium', 0))],
            ['Low', str(metrics.get('severity_breakdown', {}).get('low', 0))],
            ['Info', str(metrics.get('severity_breakdown', {}).get('info', 0))]
        ]
        
        severity_table = Table(severity_data)
        severity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(severity_table)
        story.append(Spacer(1, 12))
        
        # Top tags
        tags_title = Paragraph("Top Tags", styles['Heading2'])
        story.append(tags_title)
        
        tags_data = [['Tag', 'Count']]
        for tag_data in metrics.get('most_common_tags', []):
            tags_data.append([tag_data['tag'], str(tag_data['count'])])
        
        if len(tags_data) > 1:
            tags_table = Table(tags_data)
            tags_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(tags_table)
        else:
            story.append(Paragraph("No tags found", styles['Normal']))
        
        story.append(Spacer(1, 12))
        
        # Footer
        footer = Paragraph(f"Generated on {metrics.get('last_updated', 'Unknown')}", styles['Normal'])
        story.append(footer)
        
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
        
    except ImportError:
        # Fallback if reportlab is not available
        return b"PDF export requires reportlab package. Please install it with: pip install reportlab"
