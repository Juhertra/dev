"""
Feroxbuster Discovery Plugin

This plugin provides directory discovery capabilities using Feroxbuster.
For M1, it uses golden sample data to simulate tool execution.
"""

import json
import logging
from typing import Any, Dict, List
from pathlib import Path
from packages.plugins.loader import PluginInterface

logger = logging.getLogger(__name__)


class FeroxPlugin(PluginInterface):
    """Feroxbuster directory discovery plugin."""
    
    def __init__(self):
        self.name = "ferox"
        self.version = "2.10.1"
        self.capabilities = ["discovery"]
    
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
            "type": "discovery",
            "capabilities": self.capabilities,
            "description": "Feroxbuster directory discovery plugin",
            "author": "SecFlow Team",
            "license": "MIT",
            "signature": {
                "algorithm": "sha256",
                "signature": "",  # Will be calculated at runtime
                "timestamp": "2025-10-14T00:00:00Z",
                "issuer": "SecFlow"
            },
            "config_schema": {
                "type": "object",
                "properties": {
                    "target": {"type": "string", "description": "Target URL or domain"},
                    "wordlist": {"type": "string", "description": "Wordlist file path"},
                    "threads": {"type": "integer", "description": "Number of threads"},
                    "timeout": {"type": "integer", "description": "Request timeout in seconds"}
                },
                "required": ["target"]
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration."""
        required_fields = ["target"]
        for field in required_fields:
            if field not in config:
                logger.error(f"Missing required config field: {field}")
                return False
        
        # Validate target format
        target = config["target"]
        if not isinstance(target, str) or not target.strip():
            logger.error("Target must be a non-empty string")
            return False
        
        return True
    
    def _load_golden_sample(self, version: str = "v2.10.x") -> List[Dict[str, Any]]:
        """Load golden sample data for simulation."""
        sample_path = Path(f"tests/golden_samples/feroxbuster/{version}/output.json")
        
        if not sample_path.exists():
            logger.warning(f"Golden sample not found: {sample_path}")
            return []
        
        try:
            with open(sample_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load golden sample: {e}")
            return []
    
    def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Feroxbuster discovery.
        For M1, this simulates execution using golden sample data.
        """
        logger.info(f"Running Feroxbuster discovery on {config['target']}")
        
        # Load golden sample data
        sample_data = self._load_golden_sample()
        
        # Simulate discovery results
        discovered_urls = []
        for item in sample_data:
            # Extract URL from sample data
            if "url" in item:
                # Use the URL from sample data directly, or construct from target
                if item['url'].startswith('http'):
                    discovered_url = item['url']
                else:
                    base_url = config["target"].rstrip('/')
                    discovered_url = f"{base_url}{item['url']}"
                
                discovered_urls.append({
                    "url": discovered_url,
                    "status_code": item.get("status", 200),
                    "content_length": item.get("size", 0),
                    "method": item.get("method", "GET"),
                    "timestamp": item.get("timestamp", ""),
                    "source": "feroxbuster",
                    "confidence": 85
                })
        
        # Simulate some additional discovery based on target
        target = config["target"]
        if "example.com" in target:
            # Add some realistic additional paths
            additional_paths = ["/robots.txt", "/sitemap.xml", "/favicon.ico"]
            for path in additional_paths:
                discovered_urls.append({
                    "url": f"{target.rstrip('/')}{path}",
                    "status_code": 200,
                    "content_length": 1024,
                    "method": "GET",
                    "timestamp": "",
                    "source": "feroxbuster",
                    "confidence": 90
                })
        
        logger.info(f"Discovered {len(discovered_urls)} URLs")
        
        return {
            "plugin": "feroxbuster",
            "type": "discovery",
            "target": config["target"],
            "results": {
                "urls": discovered_urls,
                "total_discovered": len(discovered_urls),
                "execution_time_ms": 1500,
                "status": "completed"
            },
            "metadata": {
                "version": self.version,
                "simulation": True,
                "golden_sample_used": True
            }
        }
