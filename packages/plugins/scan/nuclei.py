"""
Nuclei Vulnerability Scanner Plugin

This plugin provides vulnerability scanning capabilities using Nuclei.
For M1, it uses golden sample data to simulate tool execution.
"""

import json
import logging
from typing import Any, Dict, List
from pathlib import Path
from packages.plugins.loader import PluginInterface

logger = logging.getLogger(__name__)


class NucleiPlugin(PluginInterface):
    """Nuclei vulnerability scanner plugin."""
    
    def __init__(self):
        self.name = "nuclei"
        self.version = "3.2.1"
        self.capabilities = ["scan"]
    
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
            "type": "scan",
            "capabilities": self.capabilities,
            "description": "Nuclei vulnerability scanner plugin",
            "config_schema": {
                "type": "object",
                "properties": {
                    "targets": {"type": "array", "description": "List of target URLs"},
                    "templates": {"type": "string", "description": "Template path or tags"},
                    "threads": {"type": "integer", "description": "Number of threads"},
                    "rate_limit": {"type": "integer", "description": "Rate limit per second"},
                    "severity": {"type": "array", "description": "Severity levels to scan"}
                },
                "required": ["targets"]
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        required_fields = ["targets"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        # Validate targets format
        targets = config["targets"]
        if not isinstance(targets, list) or not targets:
            logger.error("Targets must be a non-empty list")
            return False
        
        for target in targets:
            if not isinstance(target, str) or not target.strip():
                logger.error("Each target must be a non-empty string")
                return False
        
        return True
    
    def _load_golden_sample(self, version: str = "v3.0.x") -> List[Dict[str, Any]]:
        """Load golden sample data for simulation."""
        sample_path = Path(f"tests/golden_samples/nuclei/{version}/output.json")
        
        if not sample_path.exists():
            logger.warning(f"Golden sample not found: {sample_path}")
            return []
        
        try:
            with open(sample_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load golden sample: {e}")
            return []
    
    def _normalize_finding(self, raw_finding: Dict[str, Any], target_url: str) -> Dict[str, Any]:
        """Normalize Nuclei finding to standard format."""
        info = raw_finding.get("info", {})
        
        return {
            "id": f"nuclei_{raw_finding.get('template-id', 'unknown')}_{hash(target_url)}",
            "title": info.get("name", "Unknown Vulnerability"),
            "severity": info.get("severity", "info").lower(),
            "path": raw_finding.get("matched-at", target_url),
            "detector_id": "nuclei",
            "evidence": raw_finding,
            "confidence": 90,
            "status": "open",
            "created_at": raw_finding.get("timestamp", ""),
            "provenance": {
                "tool": "nuclei",
                "version": self.version,
                "template_id": raw_finding.get("template-id"),
                "template_name": info.get("name"),
                "simulation": True
            }
        }
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Nuclei vulnerability scan.
        For M1, this simulates execution using golden sample data.
        """
        targets = config["targets"]
        logger.info(f"Running Nuclei scan on {len(targets)} targets")
        
        # Load golden sample data
        sample_data = self._load_golden_sample()
        
        # Simulate scan results
        findings = []
        for target in targets:
            logger.info(f"Scanning target: {target}")
            
            # Generate findings based on golden sample
            for raw_finding in sample_data:
                finding = self._normalize_finding(raw_finding, target)
                findings.append(finding)
            
            # Add some target-specific findings
            if "example.com" in target:
                # Add realistic findings for example.com
                additional_findings = [
                    {
                        "id": f"nuclei_ssl_cert_{hash(target)}",
                        "title": "SSL Certificate Information Disclosure",
                        "severity": "low",
                        "path": target,
                        "detector_id": "nuclei",
                        "evidence": {"template-id": "ssl-cert", "matched-at": target},
                        "confidence": 85,
                        "status": "open",
                        "created_at": "",
                        "provenance": {"tool": "nuclei", "version": self.version, "simulation": True}
                    },
                    {
                        "id": f"nuclei_cors_{hash(target)}",
                        "title": "CORS Misconfiguration",
                        "severity": "medium",
                        "path": f"{target}/api/users",
                        "detector_id": "nuclei",
                        "evidence": {"template-id": "cors-misconfig", "matched-at": f"{target}/api/users"},
                        "confidence": 80,
                        "status": "open",
                        "created_at": "",
                        "provenance": {"tool": "nuclei", "version": self.version, "simulation": True}
                    }
                ]
                findings.extend(additional_findings)
        
        logger.info(f"Found {len(findings)} vulnerabilities")
        
        return {
            "plugin": "nuclei",
            "type": "scan",
            "targets": targets,
            "results": {
                "findings": findings,
                "total_findings": len(findings),
                "execution_time_ms": 3000,
                "status": "completed"
            },
            "metadata": {
                "version": self.version,
                "simulation": True,
                "golden_sample_used": True,
                "templates_scanned": len(sample_data)
            }
        }
