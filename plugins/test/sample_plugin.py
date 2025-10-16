"""
Sample plugin for security testing.

This plugin demonstrates basic functionality and security compliance.
"""

import json
import time
from datetime import datetime
from typing import Dict, Any

class Plugin:
    """Sample plugin for security testing."""
    
    def __init__(self):
        self.name = "sample_plugin"
        self.version = "1.0.0"
        self.description = "Sample plugin for security testing"
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute plugin with input data.
        
        Args:
            data: Input data dictionary
            
        Returns:
            Result dictionary with processing results
        """
        try:
            # Simulate some processing
            time.sleep(0.1)
            
            # Process input data
            result = {
                "status": "success",
                "plugin_name": self.name,
                "plugin_version": self.version,
                "input_data": data,
                "processed_at": datetime.utcnow().isoformat(),
                "message": "Plugin executed successfully"
            }
            
            # Add some computed values
            if isinstance(data, dict):
                result["input_keys"] = list(data.keys())
                result["input_count"] = len(data)
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "plugin_name": self.name,
                "plugin_version": self.version,
                "error": str(e),
                "processed_at": datetime.utcnow().isoformat()
            }

# Plugin metadata
PLUGIN_METADATA = {
    "name": "sample_plugin",
    "version": "1.0.0",
    "description": "Sample plugin for security testing",
    "author": "Security Team",
    "entrypoint": "Plugin",
    "created_at": datetime.utcnow().isoformat()
}
