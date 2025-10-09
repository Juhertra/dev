#!/usr/bin/env python3
"""
Reporting Module - Generate comprehensive security reports.
"""
import csv
import json
from datetime import datetime
from typing import Any, Dict, List

from findings import get_findings, group_findings_for_ui


class SecurityReporter:
    """
    Generate comprehensive security reports in various formats.
    """
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.timestamp = datetime.now()
    
    def generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary of security findings."""
        findings = get_findings(self.project_id)
        grouped = group_findings_for_ui(self.project_id)
        
        # Calculate risk metrics
        total_findings = len(findings)
        critical_count = len([f for f in findings if f.get("severity") == "critical"])
        high_count = len([f for f in findings if f.get("severity") == "high"])
        medium_count = len([f for f in findings if f.get("severity") == "medium"])
        low_count = len([f for f in findings if f.get("severity") == "low"])
        
        # Calculate risk score (weighted)
        risk_score = (critical_count * 10 + high_count * 7 + medium_count * 4 + low_count * 1)
        max_possible = total_findings * 10
        risk_percentage = (risk_score / max_possible * 100) if max_possible > 0 else 0
        
        # OWASP breakdown
        owasp_web = grouped.get("counts", {}).get("web", 0)
        owasp_api = grouped.get("counts", {}).get("api", 0)
        
        return {
            "project_id": self.project_id,
            "report_date": self.timestamp.isoformat(),
            "total_findings": total_findings,
            "severity_breakdown": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "low": low_count
            },
            "risk_score": {
                "raw_score": risk_score,
                "percentage": round(risk_percentage, 1),
                "level": self._get_risk_level(risk_percentage)
            },
            "owasp_breakdown": {
                "web": owasp_web,
                "api": owasp_api
            },
            "top_vulnerabilities": self._get_top_vulnerabilities(findings),
            "recommendations": self._get_priority_recommendations(findings)
        }
    
    def _get_risk_level(self, risk_percentage: float) -> str:
        """Determine risk level based on percentage."""
        if risk_percentage >= 80:
            return "Critical"
        elif risk_percentage >= 60:
            return "High"
        elif risk_percentage >= 40:
            return "Medium"
        elif risk_percentage >= 20:
            return "Low"
        else:
            return "Very Low"
    
    def _get_top_vulnerabilities(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get top vulnerabilities by frequency and severity."""
        vuln_counts = {}
        
        for finding in findings:
            title = finding.get("title", "Unknown")
            severity = finding.get("severity", "info")
            
            if title not in vuln_counts:
                vuln_counts[title] = {
                    "title": title,
                    "count": 0,
                    "severity": severity,
                    "cwe": finding.get("cwe"),
                    "confidence": finding.get("confidence", 50)
                }
            vuln_counts[title]["count"] += 1
        
        # Sort by severity weight and count
        severity_weights = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        
        sorted_vulns = sorted(
            vuln_counts.values(),
            key=lambda x: (severity_weights.get(x["severity"], 0), x["count"]),
            reverse=True
        )
        
        return sorted_vulns[:10]  # Top 10
    
    def _get_priority_recommendations(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get priority recommendations based on findings."""
        recommendations = []
        
        # Group findings by OWASP category
        owasp_groups = {}
        for finding in findings:
            owasp = finding.get("owasp") or finding.get("owasp_api")
            if owasp:
                if owasp not in owasp_groups:
                    owasp_groups[owasp] = []
                owasp_groups[owasp].append(finding)
        
        # Generate recommendations for each OWASP category
        for owasp, group_findings in owasp_groups.items():
            if not group_findings:
                continue
            
            severity_counts = {}
            for f in group_findings:
                sev = f.get("severity", "info")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            # Determine priority based on severity distribution
            if severity_counts.get("critical", 0) > 0 or severity_counts.get("high", 0) > 2:
                priority = "High"
            elif severity_counts.get("high", 0) > 0 or severity_counts.get("medium", 0) > 3:
                priority = "Medium"
            else:
                priority = "Low"
            
            recommendations.append({
                "owasp_category": owasp,
                "finding_count": len(group_findings),
                "severity_breakdown": severity_counts,
                "priority": priority,
                "recommendation": self._get_owasp_recommendation(owasp),
                "affected_endpoints": len(set(f.get("url", "") for f in group_findings))
            })
        
        # Sort by priority
        priority_order = {"High": 3, "Medium": 2, "Low": 1}
        recommendations.sort(key=lambda x: priority_order.get(x["priority"], 0), reverse=True)
        
        return recommendations
    
    def _get_owasp_recommendation(self, owasp_category: str) -> str:
        """Get recommendation text for OWASP category."""
        recommendations = {
            "A01:2021-Broken Access Control": "Implement proper authorization checks at the resource level. Use deny-by-default approach and verify object ownership.",
            "A02:2021-Cryptographic Failures": "Upgrade to strong cryptographic algorithms, implement proper key management, and ensure data encryption at rest and in transit.",
            "A03:2021-Injection": "Use parameterized queries, input validation, and output encoding. Implement proper sanitization for all user inputs.",
            "A04:2021-Insecure Design": "Conduct threat modeling and security design reviews. Implement defense-in-depth strategies.",
            "A05:2021-Security Misconfiguration": "Follow security hardening guidelines, remove default credentials, and implement proper security headers.",
            "A06:2021-Vulnerable and Outdated Components": "Maintain an inventory of components, regularly update dependencies, and monitor for security advisories.",
            "A07:2021-Identification and Authentication Failures": "Implement multi-factor authentication, strong password policies, and secure session management.",
            "A08:2021-Software and Data Integrity Failures": "Implement code signing, secure CI/CD pipelines, and integrity verification mechanisms.",
            "A09:2021-Security Logging and Monitoring Failures": "Implement comprehensive logging, monitoring, and alerting for security events.",
            "A10:2021-Server-Side Request Forgery": "Implement URL validation, use allowlists for external requests, and block internal network access.",
            "API1:2023-Broken Object Level Authorization": "Implement proper object-level authorization checks and use opaque identifiers.",
            "API2:2023-Broken Authentication": "Implement strong authentication mechanisms, token validation, and secure credential storage.",
            "API3:2023-Broken Object Property Level Authorization": "Implement field-level authorization and input validation for object properties.",
            "API4:2023-Unrestricted Resource Consumption": "Implement rate limiting, resource quotas, and request size limits.",
            "API5:2023-Broken Function Level Authorization": "Implement proper function-level authorization and role-based access control.",
            "API6:2023-Unrestricted Access to Sensitive Business Flows": "Implement additional authentication for sensitive operations and fraud detection.",
            "API7:2023-Server Side Request Forgery": "Implement URL validation and network segmentation for external requests.",
            "API8:2023-Security Misconfiguration": "Follow API security best practices and implement proper configuration management.",
            "API9:2023-Imprecise Rate Limiting": "Implement comprehensive rate limiting with proper error responses and monitoring.",
            "API10:2023-Unsafe Consumption of APIs": "Implement proper validation and sanitization of data from external APIs."
        }
        
        return recommendations.get(owasp_category, "Review and address security issues in this category.")
    
    def generate_technical_report(self) -> Dict[str, Any]:
        """Generate detailed technical report."""
        findings = get_findings(self.project_id)
        grouped = group_findings_for_ui(self.project_id)
        
        # Detailed findings analysis
        detailed_findings = []
        for finding in findings:
            detailed_findings.append({
                "id": finding.get("id"),
                "title": finding.get("title"),
                "severity": finding.get("severity"),
                "confidence": finding.get("confidence", 50),
                "cwe": finding.get("cwe"),
                "cvss": finding.get("cvss"),
                "owasp": finding.get("owasp"),
                "owasp_api": finding.get("owasp_api"),
                "subcategory": finding.get("subcategory"),
                "url": finding.get("url"),
                "method": finding.get("method"),
                "evidence": finding.get("evidence"),
                "detector_id": finding.get("detector_id"),
                "timestamp": finding.get("timestamp")
            })
        
        return {
            "project_id": self.project_id,
            "report_date": self.timestamp.isoformat(),
            "executive_summary": self.generate_executive_summary(),
            "detailed_findings": detailed_findings,
            "owasp_breakdown": grouped.get("owasp", {}),
            "subcategory_breakdown": grouped.get("subcategories", {}),
            "detector_breakdown": grouped.get("detectors", {}),
            "statistics": {
                "total_findings": len(findings),
                "unique_endpoints": len(set(f.get("url", "") for f in findings)),
                "unique_vulnerabilities": len(set(f.get("title", "") for f in findings)),
                "average_confidence": sum(f.get("confidence", 50) for f in findings) / len(findings) if findings else 0
            }
        }
    
    def export_findings_json(self, output_file: str) -> bool:
        """Export findings to JSON format."""
        try:
            report = self.generate_technical_report()
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting JSON: {e}")
            return False
    
    def export_findings_csv(self, output_file: str) -> bool:
        """Export findings to CSV format."""
        try:
            findings = get_findings(self.project_id)
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "ID", "Title", "Severity", "Confidence", "CWE", "CVSS",
                    "OWASP Web", "OWASP API", "Subcategory", "URL", "Method",
                    "Evidence", "Detector ID", "Timestamp"
                ])
                
                for finding in findings:
                    writer.writerow([
                        finding.get("id", ""),
                        finding.get("title", ""),
                        finding.get("severity", ""),
                        finding.get("confidence", 50),
                        finding.get("cwe", ""),
                        finding.get("cvss", ""),
                        finding.get("owasp", ""),
                        finding.get("owasp_api", ""),
                        finding.get("subcategory", ""),
                        finding.get("url", ""),
                        finding.get("method", ""),
                        finding.get("evidence", ""),
                        finding.get("detector_id", ""),
                        finding.get("timestamp", "")
                    ])
            return True
        except Exception as e:
            print(f"Error exporting CSV: {e}")
            return False
    
    def export_sarif(self, output_file: str) -> bool:
        """Export findings to SARIF format."""
        try:
            findings = get_findings(self.project_id)
            
            sarif = {
                "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
                "version": "2.1.0",
                "runs": [{
                    "tool": {
                        "driver": {
                            "name": "Security Testing Tool",
                            "version": "1.0.0",
                            "informationUri": "https://example.com/security-tool"
                        }
                    },
                    "results": []
                }]
            }
            
            for finding in findings:
                # Map severity to SARIF level
                severity_map = {
                    "critical": "error",
                    "high": "error", 
                    "medium": "warning",
                    "low": "note",
                    "info": "note"
                }
                
                level = severity_map.get(finding.get("severity", "info"), "note")
                
                result = {
                    "ruleId": finding.get("detector_id", "unknown"),
                    "level": level,
                    "message": {
                        "text": finding.get("title", "Security Finding")
                    },
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": finding.get("url", "")
                            }
                        }
                    }],
                    "properties": {
                        "confidence": finding.get("confidence", 50),
                        "cwe": finding.get("cwe", ""),
                        "cvss": finding.get("cvss", ""),
                        "owasp": finding.get("owasp", finding.get("owasp_api", "")),
                        "subcategory": finding.get("subcategory", ""),
                        "method": finding.get("method", ""),
                        "evidence": finding.get("evidence", "")
                    }
                }
                
                sarif["runs"][0]["results"].append(result)
            
            with open(output_file, 'w') as f:
                json.dump(sarif, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting SARIF: {e}")
            return False
    
    def generate_html_report(self, output_file: str) -> bool:
        """Generate HTML report."""
        try:
            report = self.generate_technical_report()
            
            html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Report - {{ project_id }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { border-bottom: 2px solid #007bff; padding-bottom: 20px; margin-bottom: 30px; }
        .header h1 { color: #007bff; margin: 0; }
        .header .subtitle { color: #666; margin: 5px 0 0 0; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; border-left: 4px solid #007bff; }
        .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
        .stat-label { color: #666; margin-top: 5px; }
        .section { margin-bottom: 30px; }
        .section h2 { color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
        .finding-item { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #dc3545; }
        .finding-title { font-weight: bold; color: #333; }
        .finding-details { color: #666; font-size: 0.9em; margin-top: 5px; }
        .severity-critical { border-left-color: #dc3545; }
        .severity-high { border-left-color: #fd7e14; }
        .severity-medium { border-left-color: #ffc107; }
        .severity-low { border-left-color: #20c997; }
        .severity-info { border-left-color: #6c757d; }
        .recommendation { background: #e7f3ff; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #007bff; }
        .recommendation h4 { margin: 0 0 10px 0; color: #007bff; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: bold; }
        .risk-level { padding: 5px 10px; border-radius: 15px; font-weight: bold; }
        .risk-critical { background: #dc3545; color: white; }
        .risk-high { background: #fd7e14; color: white; }
        .risk-medium { background: #ffc107; color: black; }
        .risk-low { background: #20c997; color: white; }
        .risk-very-low { background: #6c757d; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Security Assessment Report</h1>
            <p class="subtitle">Project: {{ project_id }} | Generated: {{ report_date }}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ executive_summary.total_findings }}</div>
                <div class="stat-label">Total Findings</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ executive_summary.risk_score.percentage }}%</div>
                <div class="stat-label">Risk Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ executive_summary.severity_breakdown.critical }}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ executive_summary.severity_breakdown.high }}</div>
                <div class="stat-label">High</div>
            </div>
        </div>
        
        <div class="section">
            <h2>Risk Assessment</h2>
            <p><strong>Overall Risk Level:</strong> 
                <span class="risk-level risk-{{ executive_summary.risk_score.level.lower().replace(' ', '-') }}">
                    {{ executive_summary.risk_score.level }}
                </span>
            </p>
            <p><strong>Risk Score:</strong> {{ executive_summary.risk_score.percentage }}% 
               ({{ executive_summary.risk_score.raw_score }} points)</p>
        </div>
        
        <div class="section">
            <h2>Top Vulnerabilities</h2>
            {% for vuln in executive_summary.top_vulnerabilities %}
            <div class="finding-item severity-{{ vuln.severity }}">
                <div class="finding-title">{{ vuln.title }}</div>
                <div class="finding-details">
                    Severity: {{ vuln.severity.title() }} | 
                    Count: {{ vuln.count }} | 
                    CWE: {{ vuln.cwe or 'N/A' }} | 
                    Confidence: {{ vuln.confidence }}%
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="section">
            <h2>Priority Recommendations</h2>
            {% for rec in executive_summary.recommendations %}
            <div class="recommendation">
                <h4>{{ rec.owasp_category }} ({{ rec.priority }} Priority)</h4>
                <p>{{ rec.recommendation }}</p>
                <p><strong>Affected:</strong> {{ rec.finding_count }} findings across {{ rec.affected_endpoints }} endpoints</p>
            </div>
            {% endfor %}
        </div>
        
        <div class="section">
            <h2>Detailed Findings</h2>
            <table>
                <thead>
                    <tr>
                        <th>Title</th>
                        <th>Severity</th>
                        <th>Confidence</th>
                        <th>CWE</th>
                        <th>URL</th>
                        <th>Method</th>
                    </tr>
                </thead>
                <tbody>
                    {% for finding in detailed_findings %}
                    <tr>
                        <td>{{ finding.title }}</td>
                        <td>{{ finding.severity.title() }}</td>
                        <td>{{ finding.confidence }}%</td>
                        <td>{{ finding.cwe or '-' }}</td>
                        <td>{{ finding.url }}</td>
                        <td>{{ finding.method }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
            """
            
            # Render template with report data
            from jinja2 import Template
            template = Template(html_template)
            html_content = template.render(
                project_id=self.project_id,
                report_date=self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                executive_summary=report["executive_summary"],
                detailed_findings=report["detailed_findings"]
            )
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True
        except Exception as e:
            print(f"Error generating HTML report: {e}")
            return False
