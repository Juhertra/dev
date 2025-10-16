"""
Plugin Signature Verification Framework

This module implements plugin signature verification to ensure plugin integrity 
and authenticity. For M1, we implement a simple hash-based verification system 
with plans to extend to full digital signatures in M2+.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class PluginSignature:
    """Plugin signature information."""
    plugin_name: str
    version: str
    file_hash: str
    signature_type: str = "sha256"
    verified: bool = False

class PluginSignatureVerifier:
    """Plugin signature verification for M1."""
    
    def __init__(self, whitelist_path: Optional[str] = None):
        self.whitelist_path = whitelist_path or "plugins/whitelist.json"
        self.whitelist = self._load_whitelist()
    
    def _load_whitelist(self) -> Dict[str, Dict]:
        """Load the plugin whitelist."""
        try:
            if os.path.exists(self.whitelist_path):
                with open(self.whitelist_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Whitelist file not found: {self.whitelist_path}")
                return {}
        except Exception as e:
            logger.error(f"Failed to load whitelist: {e}")
            return {}
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def verify_plugin(self, plugin_path: str, plugin_name: str, version: str) -> PluginSignature:
        """Verify a plugin against the whitelist."""
        file_hash = self.calculate_file_hash(plugin_path)
        
        if not file_hash:
            return PluginSignature(
                plugin_name=plugin_name,
                version=version,
                file_hash="",
                verified=False
            )
        
        # Check against whitelist
        whitelist_key = f"{plugin_name}:{version}"
        if whitelist_key in self.whitelist:
            expected_hash = self.whitelist[whitelist_key].get("hash", "")
            verified = file_hash == expected_hash
        else:
            logger.warning(f"Plugin {whitelist_key} not found in whitelist")
            verified = False
        
        return PluginSignature(
            plugin_name=plugin_name,
            version=version,
            file_hash=file_hash,
            verified=verified
        )
    
    def add_to_whitelist(self, plugin_name: str, version: str, file_path: str) -> bool:
        """Add a plugin to the whitelist."""
        try:
            file_hash = self.calculate_file_hash(file_path)
            if not file_hash:
                return False
            
            whitelist_key = f"{plugin_name}:{version}"
            self.whitelist[whitelist_key] = {
                "hash": file_hash,
                "file_path": file_path,
                "added_at": str(Path(file_path).stat().st_mtime)
            }
            
            # Save whitelist
            os.makedirs(os.path.dirname(self.whitelist_path), exist_ok=True)
            with open(self.whitelist_path, 'w') as f:
                json.dump(self.whitelist, f, indent=2)
            
            logger.info(f"Added {whitelist_key} to whitelist")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add plugin to whitelist: {e}")
            return False
    
    def remove_from_whitelist(self, plugin_name: str, version: str) -> bool:
        """Remove a plugin from the whitelist."""
        try:
            whitelist_key = f"{plugin_name}:{version}"
            if whitelist_key in self.whitelist:
                del self.whitelist[whitelist_key]
                
                # Save whitelist
                with open(self.whitelist_path, 'w') as f:
                    json.dump(self.whitelist, f, indent=2)
                
                logger.info(f"Removed {whitelist_key} from whitelist")
                return True
            else:
                logger.warning(f"Plugin {whitelist_key} not found in whitelist")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove plugin from whitelist: {e}")
            return False
    
    def list_whitelisted_plugins(self) -> List[Tuple[str, str]]:
        """List all whitelisted plugins."""
        plugins = []
        for key in self.whitelist.keys():
            if ":" in key:
                name, version = key.split(":", 1)
                plugins.append((name, version))
        return plugins

# Example usage and testing
if __name__ == "__main__":
    # Test the signature verifier
    verifier = PluginSignatureVerifier()
    
    # Test with a sample file
    test_file = "test_plugin.py"
    if os.path.exists(test_file):
        signature = verifier.verify_plugin(test_file, "test-plugin", "1.0.0")
        print(f"Plugin: {signature.plugin_name}")
        print(f"Version: {signature.version}")
        print(f"Hash: {signature.file_hash}")
        print(f"Verified: {signature.verified}")
    else:
        print("Test file not found")