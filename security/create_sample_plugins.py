#!/usr/bin/env python3
"""
Create and sign sample plugin for testing.

This script creates a sample plugin and signs it with the test keys
for demonstrating the plugin signature verification system.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add security module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from security.signing import PluginSigner, PluginManifest

def create_sample_plugin():
    """Create sample plugin file."""
    plugin_code = '''"""
Sample plugin for security testing.

This plugin demonstrates basic functionality and security compliance.
"""

import json
import time
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
'''
    
    plugin_path = Path("plugins/test/sample_plugin.py")
    plugin_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(plugin_path, 'w') as f:
        f.write(plugin_code)
    
    print(f"Sample plugin created: {plugin_path}")
    return plugin_path

def create_plugin_manifest(plugin_path: Path):
    """Create plugin manifest."""
    manifest_data = {
        "name": "sample_plugin",
        "version": "1.0.0",
        "description": "Sample plugin for security testing",
        "author": "Security Team",
        "entrypoint": "Plugin",
        "created_at": datetime.utcnow().isoformat(),
        "security_profile": {
            "resource_limits": {
                "cpu_seconds": 30,
                "memory_mb": 256
            },
            "permissions": {
                "network_access": False,
                "filesystem_access": {
                    "read_only": True,
                    "read_allowlist": ["/tmp"],
                    "write_allowlist": []
                }
            },
            "signature_required": True
        }
    }
    
    manifest_path = plugin_path.with_suffix('.json')
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    print(f"Plugin manifest created: {manifest_path}")
    return manifest_path

def sign_plugin(plugin_path: Path, manifest_path: Path):
    """Sign the plugin."""
    # Load manifest
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Create PluginManifest object
    manifest = PluginManifest(
        name=manifest_data["name"],
        version=manifest_data["version"],
        description=manifest_data["description"],
        author=manifest_data["author"],
        entrypoint=manifest_data["entrypoint"],
        code_hash="",  # Will be calculated during signing
        signature_type="rsa"
    )
    
    # Sign plugin
    signer = PluginSigner("security/keys/private.pem")
    signature = signer.sign_plugin(manifest, str(plugin_path))
    
    # Update manifest with signature
    manifest_data["signature"] = signature
    manifest_data["signature_type"] = "rsa"
    manifest_data["code_hash"] = signer.calculate_plugin_hash(str(plugin_path))
    
    # Save updated manifest
    with open(manifest_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    print(f"Plugin signed successfully")
    print(f"Signature: {signature[:50]}...")
    print(f"Code hash: {manifest_data['code_hash']}")

def create_malicious_plugin():
    """Create malicious plugin for testing."""
    malicious_code = '''"""
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
'''
    
    plugin_path = Path("plugins/test/malicious_plugin.py")
    
    with open(plugin_path, 'w') as f:
        f.write(malicious_code)
    
    print(f"Malicious plugin created: {plugin_path}")
    return plugin_path

def main():
    """Main function."""
    print("Creating sample plugins for security testing...")
    
    # Create sample plugin
    plugin_path = create_sample_plugin()
    manifest_path = create_plugin_manifest(plugin_path)
    sign_plugin(plugin_path, manifest_path)
    
    print("\n" + "="*50)
    
    # Create malicious plugin
    malicious_path = create_malicious_plugin()
    
    print("\n✅ Sample plugins created successfully!")
    print("\nFiles created:")
    print(f"  Sample plugin: {plugin_path}")
    print(f"  Sample manifest: {manifest_path}")
    print(f"  Malicious plugin: {malicious_path}")
    
    print("\nTo test the plugins:")
    print(f"  python security/plugin_loader.py {plugin_path} {manifest_path}")
    print(f"  python security/plugin_loader.py {malicious_path} {manifest_path}")

if __name__ == "__main__":
    main()
