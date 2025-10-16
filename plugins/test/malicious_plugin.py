"""
Malicious plugin for security testing.

This plugin attempts various security violations for testing purposes.
"""

import os
import subprocess
import socket
import json
from typing import Dict, Any

class Plugin:
    """Malicious plugin for security testing."""
    
    def __init__(self):
        self.name = "malicious_plugin"
        self.version = "1.0.0"
        self.description = "Malicious plugin for security testing"
    
    def run(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt various security violations."""
        violations = []
        
        try:
            # Attempt to read sensitive files
            try:
                with open("/etc/passwd", "r") as f:
                    content = f.read()
                violations.append("read_sensitive_file")
            except:
                pass
            
            # Attempt to execute system commands
            try:
                result = subprocess.run(["ls", "/"], capture_output=True, timeout=1)
                violations.append("execute_system_command")
            except:
                pass
            
            # Attempt to access network
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(("example.com", 80))
                s.close()
                violations.append("network_access")
            except:
                pass
            
            # Attempt to write to filesystem
            try:
                with open("/tmp/malicious_test.txt", "w") as f:
                    f.write("malicious content")
                violations.append("filesystem_write")
            except:
                pass
            
            return {
                "status": "malicious_attempt",
                "plugin_name": self.name,
                "violations_attempted": violations,
                "message": "Malicious plugin executed"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "plugin_name": self.name,
                "error": str(e)
            }
