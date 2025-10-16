"""
CVE Mapper Enricher Plugin

This plugin provides CVE mapping and enrichment capabilities.
For M1, it simulates CVE enrichment using static data.
"""

import json
import logging
from typing import Any, Dict, List
from packages.plugins.loader import PluginInterface

logger = logging.getLogger(__name__)


class CVEMapperPlugin(PluginInterface):
    """CVE mapping and enrichment plugin."""
    
    def __init__(self):
        self.name = "cve_mapper"
        self.version = "1.0.0"
        self.capabilities = ["enrich"]
        
        # Static CVE database for M1 simulation
        self.cve_database = {
            "ssl-cert": {
                "cve_id": "CVE-2021-3450",
                "severity": "medium",
                "description": "SSL certificate information disclosure vulnerability",
                "cvss_score": 5.3,
                "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-3450"]
            },
            "cors-misconfig": {
                "cve_id": "CVE-2020-25638",
                "severity": "medium", 
                "description": "CORS misconfiguration leading to information disclosure",
                "cvss_score": 6.1,
                "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2020-25638"]
            },
            "http-methods": {
                "cve_id": "CVE-2021-44228",
                "severity": "critical",
                "description": "HTTP methods enumeration vulnerability",
                "cvss_score": 10.0,
                "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-44228"]
            },
            "tech-detect": {
                "cve_id": "CVE-2021-44228",
                "severity": "critical",
                "description": "Technology detection leading to exploitation",
                "cvss_score": 10.0,
                "references": ["https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2021-44228"]
            }
        }
    
    def get_name(self) -> str:
        return self.name
    
    def get_version(self) -> str:
        return self.version
    
    def get_capabilities(self) -> List[str]:
        return self.capabilities
    
    def get_manifest(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "type": "enricher",
            "capabilities": self.capabilities,
            "description": "CVE mapping and enrichment plugin",
            "config_schema": {
                "type": "object",
                "properties": {
                    "findings": {"type": "array", "description": "List of findings to enrich"},
                    "cve_database": {"type": "string", "description": "CVE database source"},
                    "severity_threshold": {"type": "string", "description": "Minimum severity to enrich"}
                },
                "required": ["findings"]
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        required_fields = ["findings"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        # Validate findings format
        findings = config["findings"]
        if not isinstance(findings, list):
            logger.error("Findings must be a list")
            return False
        
        return True
    
    def _map_template_to_cve(self, template_id: str) -> Dict[str, Any]:
        """Map Nuclei template ID to CVE information."""
        return self.cve_database.get(template_id, {
            "cve_id": "CVE-UNKNOWN",
            "severity": "unknown",
            "description": "Unknown vulnerability",
            "cvss_score": 0.0,
            "references": []
        })
    
    def _enrich_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a single finding with CVE information."""
        enriched_finding = finding.copy()
        
        # Extract template ID from evidence
        evidence = finding.get("evidence", {})
        template_id = evidence.get("template-id", "")
        
        if template_id:
            cve_info = self._map_template_to_cve(template_id)
            
            # Add CVE enrichment
            enriched_finding["cve_details"] = {
                "cve_id": cve_info["cve_id"],
                "severity": cve_info["severity"],
                "description": cve_info["description"],
                "cvss_score": cve_info["cvss_score"],
                "references": cve_info["references"],
                "enriched_by": "cve_mapper",
                "enrichment_timestamp": "",
                "confidence": 85
            }
            
            # Update finding severity if CVE severity is higher
            finding_severity = finding.get("severity", "info").lower()
            cve_severity = cve_info["severity"].lower()
            
            severity_order = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
            if severity_order.get(cve_severity, 0) > severity_order.get(finding_severity, 0):
                enriched_finding["severity"] = cve_severity
                enriched_finding["severity_source"] = "cve_enrichment"
            
            # Add CWE mapping if available
            if template_id in ["ssl-cert", "cors-misconfig"]:
                enriched_finding["cwe_id"] = "CWE-200"  # Information Exposure
            elif template_id in ["http-methods", "tech-detect"]:
                enriched_finding["cwe_id"] = "CWE-200"  # Information Exposure
        
        return enriched_finding
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute CVE enrichment on findings.
        For M1, this simulates enrichment using static CVE data.
        """
        findings = config["findings"]
        logger.info(f"Running CVE enrichment on {len(findings)} findings")
        
        # Enrich each finding
        enriched_findings = []
        enrichment_stats = {
            "total_findings": len(findings),
            "enriched_findings": 0,
            "cve_mapped": 0,
            "severity_upgraded": 0
        }
        
        for finding in findings:
            enriched_finding = self._enrich_finding(finding)
            enriched_findings.append(enriched_finding)
            
            # Update statistics
            enrichment_stats["enriched_findings"] += 1
            if enriched_finding.get("cve_details", {}).get("cve_id") != "CVE-UNKNOWN":
                enrichment_stats["cve_mapped"] += 1
            if enriched_finding.get("severity_source") == "cve_enrichment":
                enrichment_stats["severity_upgraded"] += 1
        
        logger.info(f"Enriched {enrichment_stats['enriched_findings']} findings")
        
        return {
            "plugin": "cve_mapper",
            "type": "enrichment",
            "results": {
                "enriched_findings": enriched_findings,
                "statistics": enrichment_stats,
                "execution_time_ms": 500,
                "status": "completed"
            },
            "metadata": {
                "version": self.version,
                "simulation": True,
                "cve_database_size": len(self.cve_database),
                "enrichment_method": "static_mapping"
            }
        }
