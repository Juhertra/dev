# Security-Integrated Plugin Loader

"""
Plugin loader with integrated security features.

This module demonstrates how to integrate the security components
with the plugin loading system for M1.
"""

import os
import sys
import json
import logging
import pathlib
import time
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

# Import security modules
from security.signing import (
    PluginManifest, PluginSignatureVerifier, verify_plugin_signature
)
from security.sandbox import (
    SandboxConfig, run_plugin_secure
)
from security.policy_enforcement import (
    SecurityPolicyManager, check_plugin_security, enforce_security_policy
)
from security.audit_logging import (
    SecurityAuditLogger, log_plugin_load, log_plugin_execution,
    log_signature_verification, log_policy_check, log_security_violation
)

logger = logging.getLogger(__name__)

@dataclass
class PluginLoadResult:
    """Result of plugin loading operation."""
    success: bool
    plugin_name: str
    plugin_path: str
    error: Optional[str] = None
    load_time: float = 0.0
    security_checks_passed: bool = False

class SecurePluginLoader:
    """Secure plugin loader with integrated security features."""
    
    def __init__(self, 
                 public_key_path: str = "security/keys/public.pem",
                 policy_dir: str = "security/policies",
                 sandbox_config: Optional[SandboxConfig] = None,
                 audit_logger: Optional[SecurityAuditLogger] = None):
        
        self.public_key_path = public_key_path
        self.policy_dir = policy_dir
        
        # Initialize security components
        self.signature_verifier = PluginSignatureVerifier(public_key_path)
        self.policy_manager = SecurityPolicyManager(policy_dir)
        self.sandbox_config = sandbox_config or SandboxConfig()
        self.audit_logger = audit_logger or SecurityAuditLogger()
        
        # Plugin registry
        self.loaded_plugins: Dict[str, Dict[str, Any]] = {}
        
        logger.info("Secure plugin loader initialized")
    
    def load_plugin(self, plugin_path: str, manifest_path: str,
                   user_id: Optional[str] = None,
                   session_id: Optional[str] = None) -> PluginLoadResult:
        """Load plugin with comprehensive security checks."""
        start_time = time.time()
        
        try:
            # 1. Load plugin manifest
            manifest = self._load_plugin_manifest(manifest_path)
            plugin_name = manifest.name
            
            logger.info(f"Loading plugin: {plugin_name}")
            
            # 2. Security checks
            security_passed = self._perform_security_checks(
                manifest, plugin_path, user_id, session_id
            )
            
            if not security_passed:
                error_msg = "Plugin failed security checks"
                logger.error(f"Plugin {plugin_name} failed security checks")
                
                # Log security violation
                log_security_violation(
                    "security_check_failure",
                    f"Plugin {plugin_name} failed security checks",
                    plugin_name, plugin_path, user_id, session_id
                )
                
                return PluginLoadResult(
                    success=False,
                    plugin_name=plugin_name,
                    plugin_path=plugin_path,
                    error=error_msg,
                    load_time=time.time() - start_time,
                    security_checks_passed=False
                )
            
            # 3. Register plugin
            self.loaded_plugins[plugin_name] = {
                "manifest": manifest,
                "plugin_path": plugin_path,
                "loaded_at": time.time(),
                "user_id": user_id,
                "session_id": session_id
            }
            
            load_time = time.time() - start_time
            
            # Log successful load
            log_plugin_load(plugin_name, plugin_path, True, None, user_id, session_id)
            
            logger.info(f"Plugin {plugin_name} loaded successfully in {load_time:.3f}s")
            
            return PluginLoadResult(
                success=True,
                plugin_name=plugin_name,
                plugin_path=plugin_path,
                load_time=load_time,
                security_checks_passed=True
            )
            
        except Exception as e:
            load_time = time.time() - start_time
            error_msg = f"Plugin loading failed: {str(e)}"
            
            logger.error(f"Plugin loading error: {e}")
            
            # Log failed load
            plugin_name = pathlib.Path(plugin_path).stem
            log_plugin_load(plugin_name, plugin_path, False, error_msg, user_id, session_id)
            
            return PluginLoadResult(
                success=False,
                plugin_name=plugin_name,
                plugin_path=plugin_path,
                error=error_msg,
                load_time=load_time,
                security_checks_passed=False
            )
    
    def execute_plugin(self, plugin_name: str, input_data: Any,
                      user_id: Optional[str] = None,
                      session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute plugin in secure sandbox."""
        if plugin_name not in self.loaded_plugins:
            error_msg = f"Plugin {plugin_name} not loaded"
            logger.error(error_msg)
            
            log_security_violation(
                "plugin_not_loaded",
                error_msg,
                plugin_name, None, user_id, session_id
            )
            
            return {
                "success": False,
                "error": error_msg
            }
        
        plugin_info = self.loaded_plugins[plugin_name]
        plugin_path = plugin_info["plugin_path"]
        
        try:
            logger.info(f"Executing plugin: {plugin_name}")
            
            # Execute in sandbox
            result = run_plugin_secure(
                plugin_name, input_data, plugin_path, self.sandbox_config
            )
            
            # Log execution
            log_plugin_execution(
                plugin_name, plugin_path, result["success"],
                result.get("execution_time", 0),
                result.get("memory_used", 0),
                result.get("error"), user_id, session_id
            )
            
            if result["success"]:
                logger.info(f"Plugin {plugin_name} executed successfully")
            else:
                logger.warning(f"Plugin {plugin_name} execution failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            error_msg = f"Plugin execution error: {str(e)}"
            logger.error(f"Plugin {plugin_name} execution error: {e}")
            
            # Log execution failure
            log_plugin_execution(
                plugin_name, plugin_path, False, 0, 0, error_msg, user_id, session_id
            )
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def _load_plugin_manifest(self, manifest_path: str) -> PluginManifest:
        """Load plugin manifest from file."""
        try:
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
            
            manifest = PluginManifest(
                name=manifest_data["name"],
                version=manifest_data["version"],
                description=manifest_data["description"],
                author=manifest_data["author"],
                entrypoint=manifest_data["entrypoint"],
                code_hash=manifest_data.get("code_hash", ""),
                signature=manifest_data.get("signature"),
                signature_type=manifest_data.get("signature_type", "rsa"),
                created_at=manifest_data.get("created_at"),
                expires_at=manifest_data.get("expires_at")
            )
            
            return manifest
            
        except Exception as e:
            raise ValueError(f"Failed to load plugin manifest: {e}")
    
    def _perform_security_checks(self, manifest: PluginManifest, plugin_path: str,
                               user_id: Optional[str] = None,
                               session_id: Optional[str] = None) -> bool:
        """Perform comprehensive security checks."""
        try:
            # 1. Signature verification
            if not self._verify_plugin_signature(manifest, plugin_path):
                return False
            
            # 2. Policy compliance check
            if not self._check_policy_compliance(manifest, plugin_path, user_id, session_id):
                return False
            
            # 3. Additional security validations
            if not self._additional_security_validations(manifest, plugin_path):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Security check error: {e}")
            return False
    
    def _verify_plugin_signature(self, manifest: PluginManifest, plugin_path: str) -> bool:
        """Verify plugin signature."""
        try:
            result = self.signature_verifier.verify_plugin_signature(manifest, plugin_path)
            
            # Log verification result
            log_signature_verification(
                manifest.name, plugin_path, result.valid,
                manifest.signature_type, result.verification_time,
                result.error
            )
            
            if not result.valid:
                logger.error(f"Signature verification failed for {manifest.name}: {result.error}")
                return False
            
            logger.info(f"Signature verification successful for {manifest.name}")
            return True
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            log_signature_verification(
                manifest.name, plugin_path, False,
                manifest.signature_type, 0, str(e)
            )
            return False
    
    def _check_policy_compliance(self, manifest: PluginManifest, plugin_path: str,
                               user_id: Optional[str] = None,
                               session_id: Optional[str] = None) -> bool:
        """Check policy compliance."""
        try:
            # Convert manifest to dict for policy check
            manifest_dict = {
                "name": manifest.name,
                "version": manifest.version,
                "description": manifest.description,
                "author": manifest.author,
                "entrypoint": manifest.entrypoint,
                "signature": manifest.signature,
                "signature_type": manifest.signature_type,
                "security_profile": self._extract_security_profile(manifest)
            }
            
            # Check security compliance
            compliant, violations = check_plugin_security(manifest_dict, plugin_path)
            
            # Log policy check result
            log_policy_check(
                manifest.name, plugin_path, compliant, violations, user_id, session_id
            )
            
            if not compliant:
                logger.error(f"Policy compliance check failed for {manifest.name}: {violations}")
                return False
            
            logger.info(f"Policy compliance check successful for {manifest.name}")
            return True
            
        except Exception as e:
            logger.error(f"Policy compliance check error: {e}")
            log_policy_check(
                manifest.name, plugin_path, False, [str(e)], user_id, session_id
            )
            return False
    
    def _additional_security_validations(self, manifest: PluginManifest, plugin_path: str) -> bool:
        """Perform additional security validations."""
        try:
            # Check plugin file exists and is readable
            if not pathlib.Path(plugin_path).exists():
                logger.error(f"Plugin file does not exist: {plugin_path}")
                return False
            
            # Check plugin file permissions
            plugin_file = pathlib.Path(plugin_path)
            if plugin_file.stat().st_mode & 0o002:  # World writable
                logger.error(f"Plugin file is world writable: {plugin_path}")
                return False
            
            # Check manifest integrity
            if not self._validate_manifest_integrity(manifest):
                logger.error(f"Manifest integrity check failed for {manifest.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Additional security validation error: {e}")
            return False
    
    def _extract_security_profile(self, manifest: PluginManifest) -> Dict[str, Any]:
        """Extract security profile from manifest."""
        # This would typically come from the manifest file
        # For now, return default security profile
        return {
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
            }
        }
    
    def _validate_manifest_integrity(self, manifest: PluginManifest) -> bool:
        """Validate manifest integrity."""
        required_fields = ["name", "version", "description", "author", "entrypoint"]
        
        for field in required_fields:
            if not getattr(manifest, field):
                logger.error(f"Manifest missing required field: {field}")
                return False
        
        return True
    
    def list_loaded_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins."""
        return [
            {
                "name": name,
                "version": info["manifest"].version,
                "description": info["manifest"].description,
                "loaded_at": info["loaded_at"],
                "user_id": info["user_id"],
                "session_id": info["session_id"]
            }
            for name, info in self.loaded_plugins.items()
        ]
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload plugin."""
        if plugin_name in self.loaded_plugins:
            del self.loaded_plugins[plugin_name]
            logger.info(f"Plugin {plugin_name} unloaded")
            return True
        
        logger.warning(f"Plugin {plugin_name} not found")
        return False

# Convenience functions
def create_secure_plugin_loader(public_key_path: str = "security/keys/public.pem",
                               policy_dir: str = "security/policies",
                               sandbox_config: Optional[SandboxConfig] = None) -> SecurePluginLoader:
    """Create secure plugin loader instance."""
    return SecurePluginLoader(public_key_path, policy_dir, sandbox_config)

def load_and_execute_plugin(plugin_path: str, manifest_path: str,
                           input_data: Any, user_id: Optional[str] = None,
                           session_id: Optional[str] = None) -> Dict[str, Any]:
    """Load and execute plugin in one operation."""
    loader = create_secure_plugin_loader()
    
    # Load plugin
    load_result = loader.load_plugin(plugin_path, manifest_path, user_id, session_id)
    
    if not load_result.success:
        return {
            "success": False,
            "error": f"Plugin loading failed: {load_result.error}"
        }
    
    # Execute plugin
    return loader.execute_plugin(load_result.plugin_name, input_data, user_id, session_id)

# CLI interface
def main():
    """CLI interface for secure plugin loader."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Secure Plugin Loader")
    parser.add_argument("plugin", help="Plugin file path")
    parser.add_argument("manifest", help="Plugin manifest file path")
    parser.add_argument("--input", default="{}", help="Input data as JSON")
    parser.add_argument("--user-id", help="User ID for audit logging")
    parser.add_argument("--session-id", help="Session ID for audit logging")
    parser.add_argument("--public-key", default="security/keys/public.pem", help="Public key file")
    parser.add_argument("--policy-dir", default="security/policies", help="Policy directory")
    
    args = parser.parse_args()
    
    # Parse input data
    input_data = json.loads(args.input)
    
    # Create loader
    loader = create_secure_plugin_loader(args.public_key, args.policy_dir)
    
    # Load plugin
    load_result = loader.load_plugin(args.plugin, args.manifest, args.user_id, args.session_id)
    
    if not load_result.success:
        print(f"❌ Plugin loading failed: {load_result.error}")
        sys.exit(1)
    
    print(f"✅ Plugin {load_result.plugin_name} loaded successfully")
    
    # Execute plugin
    execution_result = loader.execute_plugin(
        load_result.plugin_name, input_data, args.user_id, args.session_id
    )
    
    if execution_result["success"]:
        print("✅ Plugin execution successful")
        print(json.dumps(execution_result["data"], indent=2))
    else:
        print(f"❌ Plugin execution failed: {execution_result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
