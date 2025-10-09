#!/usr/bin/env python3
"""
P6 - Export Findings Report Script

CLI tool for exporting findings reports in various formats.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics_core.analytics import get_filtered_metrics, get_metrics
from findings import get_findings


def export_csv(pid: str, filters: Dict[str, Any], output_file: str) -> None:
    """Export findings to CSV format."""
    try:
        findings = get_findings(pid)
        
        # Apply filters
        filtered_findings = _apply_filters(findings, filters)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            if not filtered_findings:
                # Empty CSV with headers
                writer = csv.writer(csvfile)
                writer.writerow(['No findings found'])
                return
            
            # Get all possible field names
            fieldnames = set()
            for finding in filtered_findings:
                fieldnames.update(finding.keys())
                # Add triage fields
                triage = finding.get('triage', {})
                for key in triage.keys():
                    fieldnames.add(f'triage_{key}')
            
            # Sort fieldnames for consistent output
            fieldnames = sorted(fieldnames)
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for finding in filtered_findings:
                # Flatten triage fields
                row = finding.copy()
                triage = row.pop('triage', {})
                for key, value in triage.items():
                    if isinstance(value, (list, dict)):
                        row[f'triage_{key}'] = json.dumps(value)
                    else:
                        row[f'triage_{key}'] = value
                
                writer.writerow(row)
        
        print(f"✅ CSV export completed: {output_file}")
        
    except Exception as e:
        print(f"❌ CSV export failed: {e}")
        sys.exit(1)


def export_json(pid: str, filters: Dict[str, Any], output_file: str) -> None:
    """Export findings to JSON format."""
    try:
        findings = get_findings(pid)
        
        # Apply filters
        filtered_findings = _apply_filters(findings, filters)
        
        # Get metrics for context
        metrics = get_filtered_metrics(pid, filters) if filters else get_metrics(pid)
        
        export_data = {
            'export_info': {
                'project_id': pid,
                'exported_at': datetime.now(timezone.utc).isoformat(),
                'total_findings': len(filtered_findings),
                'filters_applied': filters
            },
            'metrics': metrics,
            'findings': filtered_findings
        }
        
        with open(output_file, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON export completed: {output_file}")
        
    except Exception as e:
        print(f"❌ JSON export failed: {e}")
        sys.exit(1)


def export_pdf(pid: str, filters: Dict[str, Any], output_file: str) -> None:
    """Export findings to PDF format."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
        
        # Get metrics and findings
        metrics = get_filtered_metrics(pid, filters) if filters else get_metrics(pid)
        findings = get_findings(pid)
        filtered_findings = _apply_filters(findings, filters)
        
        doc = SimpleDocTemplate(output_file, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        title = Paragraph(f"Security Findings Report - Project {pid}", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Export info
        export_info = Paragraph(f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC", styles['Normal'])
        story.append(export_info)
        if filters:
            filters_text = ", ".join([f"{k}: {v}" for k, v in filters.items()])
            filters_info = Paragraph(f"Filters: {filters_text}", styles['Normal'])
            story.append(filters_info)
        story.append(Spacer(1, 12))
        
        # Summary metrics
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
        
        # Findings table (first 50 findings)
        if filtered_findings:
            findings_title = Paragraph("Findings Details (First 50)", styles['Heading2'])
            story.append(findings_title)
            
            # Prepare findings data
            findings_data = [['Title', 'Severity', 'Status', 'Detector', 'Created']]
            for finding in filtered_findings[:50]:  # Limit to first 50
                triage = finding.get('triage', {})
                findings_data.append([
                    finding.get('title', '')[:50],  # Truncate title
                    finding.get('severity', ''),
                    triage.get('status', 'open'),
                    finding.get('detector_id', '')[:30],  # Truncate detector_id
                    finding.get('created_at', '')[:10]  # Date only
                ])
            
            findings_table = Table(findings_data)
            findings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            
            story.append(findings_table)
        
        doc.build(story)
        print(f"✅ PDF export completed: {output_file}")
        
    except ImportError:
        print("❌ PDF export requires reportlab package. Install with: pip install reportlab")
        sys.exit(1)
    except Exception as e:
        print(f"❌ PDF export failed: {e}")
        sys.exit(1)


def _apply_filters(findings: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Apply filters to findings list."""
    filtered = []
    
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
        
        filtered.append(finding)
    
    return filtered


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Export findings reports")
    parser.add_argument("--pid", required=True, help="Project ID")
    parser.add_argument("--format", choices=['csv', 'json', 'pdf'], required=True, help="Export format")
    parser.add_argument("--output", help="Output file path (default: auto-generated)")
    
    # Filter options
    parser.add_argument("--status", help="Filter by triage status")
    parser.add_argument("--owner", help="Filter by owner")
    parser.add_argument("--since", help="Filter by creation date (YYYY-MM-DD)")
    parser.add_argument("--tag", help="Filter by tag")
    
    args = parser.parse_args()
    
    # Build filters
    filters = {}
    if args.status:
        filters['status'] = args.status
    if args.owner:
        filters['owner'] = args.owner
    if args.since:
        filters['since'] = args.since
    if args.tag:
        filters['tag'] = args.tag
    
    # Generate output filename if not provided
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"exports/findings_report_{args.pid}_{timestamp}.{args.format}"
    
    # Ensure exports directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    print(f"🚀 Exporting findings for project {args.pid}")
    print(f"📊 Format: {args.format}")
    if filters:
        print(f"🔍 Filters: {filters}")
    print(f"📁 Output: {args.output}")
    print()
    
    # Export based on format
    if args.format == 'csv':
        export_csv(args.pid, filters, args.output)
    elif args.format == 'json':
        export_json(args.pid, filters, args.output)
    elif args.format == 'pdf':
        export_pdf(args.pid, filters, args.output)
    
    print("\n✅ Export completed successfully!")


if __name__ == "__main__":
    main()
