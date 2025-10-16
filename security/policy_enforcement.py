# Security Policy Enforcement Module

"""
Security policy enforcement for plugin execution.

This module integrates security policies with plugin loading and execution,
ensuring compliance with security requirements.
"""

import os
import yaml
import json
import logging
import pathlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class PolicyViolation(Enum):
    """Policy violation types."""
    SIGNATURE_REQUIRED = "signature_required"
    NETWORK_ACCESS_DENIED = "network_access_denied"
    FILESYSTEM_WRITE_DENIED = "filesystem_write_denied"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"
    UNAUTHORIZED_DIRECTORY = "unauthorized_directory"
    UNSAFE_OPERATION = "unsafe_operation"

@dataclass
class SecurityPolicy:
    """Security policy definition."""
    name: str
    version: str
    description: str
    rules: List[Dict[str, Any]]
    enforcement_level: str = "strict"  # strict, warning, disabled
    created_at: str = None
    updated_at: str = None

@dataclass
class PolicyCheckResult:
    """Result of policy check."""
    compliant: bool
    violations: List[PolicyViolation]
    warnings: List[str]
    audit_record: Optional[Dict[str, Any]] = None

class SecurityPolicyManager:
    """Manages security policies and enforcement."""
    
    def __init__(self, policy_dir: str = "security/policies"):
        self.policy_dir = pathlib.Path(policy_dir)
        self.policies: Dict[str, SecurityPolicy] = {}
        self.audit_logger = logging.getLogger("security.audit")
        
        # Load default policies
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default security policies."""
        default_policies = {
            "plugin_security": SecurityPolicy(
                name="plugin_security",
                version="1.0",
                description="Plugin security policy",
                rules=[
                    {
                        "name": "signature_required",
                        "type": "signature_verification",
                        "enforcement": "strict",
                        "description": "All plugins must be cryptographically signed"
                    },
                    {
                        "name": "network_access_denied",
                        "type": "network_restriction",
                        "enforcement": "strict",
                        "description": "Plugins are denied network access by default"
                    },
                    {
                        "name": "filesystem_write_denied",
                        "type": "filesystem_restriction",
                        "enforcement": "strict",
                        "description": "Plugins are denied filesystem write access by default"
                    },
                    {
                        "name": "resource_limits",
                        "type": "resource_restriction",
                        "enforcement": "strict",
                        "description": "Plugins must respect resource limits"
                    }
                ],
                created_at=datetime.utcnow().isoformat()
            )
        }
        
        for name, policy in default_policies.items():
            self.policies[name] = policy
        
        logger.info(f"Loaded {len(default_policies)} default security policies")
    
    def load_policy_file(self, policy_file: str) -> Optional[SecurityPolicy]:
        """Load security policy from file."""
        try:
            policy_path = self.policy_dir / policy_file
            
            if not policy_path.exists():
                logger.warning(f"Policy file not found: {policy_path}")
                return None
            
            with open(policy_path, 'r') as f:
                policy_data = yaml.safe_load(f)
            
            policy = SecurityPolicy(
                name=policy_data["name"],
                version=policy_data["version"],
                description=policy_data["description"],
                rules=policy_data["rules"],
                enforcement_level=policy_data.get("enforcement_level", "strict"),
                created_at=policy_data.get("created_at"),
                updated_at=policy_data.get("updated_at")
            )
            
            self.policies[policy.name] = policy
            logger.info(f"Loaded policy: {policy.name}")
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to load policy file {policy_file}: {e}")
            return None
    
    def check_plugin_policy(self, plugin_manifest: Dict[str, Any], 
                           plugin_path: str) -> PolicyCheckResult:
        """Check plugin against security policies."""
        violations = []
        warnings = []
        
        try:
            # Get plugin security policy
            policy = self.policies.get("plugin_security")
            if not policy:
                warnings.append("No plugin security policy found")
                return PolicyCheckResult(
                    compliant=True,
                    violations=[],
                    warnings=warnings
                )
            
            # Check signature requirement
            if not self._check_signature_requirement(plugin_manifest, policy):
                violations.append(PolicyViolation.SIGNATURE_REQUIRED)
            
            # Check network access
            if not self._check_network_access(plugin_manifest, policy):
                violations.append(PolicyViolation.NETWORK_ACCESS_DENIED)
            
            # Check filesystem access
            if not self._check_filesystem_access(plugin_manifest, policy):
                violations.append(PolicyViolation.FILESYSTEM_WRITE_DENIED)
            
            # Check resource limits
            if not self._check_resource_limits(plugin_manifest, policy):
                violations.append(PolicyViolation.RESOURCE_LIMIT_EXCEEDED)
            
            # Create audit record
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "policy_check",
                "plugin_name": plugin_manifest.get("name", "unknown"),
                "plugin_path": plugin_path,
                "policy_name": policy.name,
                "policy_version": policy.version,
                "compliant": len(violations) == 0,
                "violations": [v.value for v in violations],
                "warnings": warnings
            }
            
            # Log audit record
            if violations:
                self.audit_logger.warning(f"Policy violations for plugin {plugin_manifest.get('name')}: {[v.value for v in violations]}")
            else:
                self.audit_logger.info(f"Plugin {plugin_manifest.get('name')} compliant with security policies")
            
            return PolicyCheckResult(
                compliant=len(violations) == 0,
                violations=violations,
                warnings=warnings,
                audit_record=audit_record
            )
            
        except Exception as e:
            logger.error(f"Policy check failed: {e}")
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "policy_check",
                "plugin_name": plugin_manifest.get("name", "unknown"),
                "plugin_path": plugin_path,
                "error": str(e)
            }
            
            self.audit_logger.error(f"Policy check error: {e}")
            
            return PolicyCheckResult(
                compliant=False,
                violations=[PolicyViolation.UNSAFE_OPERATION],
                warnings=[f"Policy check error: {e}"],
                audit_record=audit_record
            )
    
    def _check_signature_requirement(self, plugin_manifest: Dict[str, Any], 
                                   policy: SecurityPolicy) -> bool:
        """Check if plugin meets signature requirements."""
        signature_rule = next((r for r in policy.rules if r["name"] == "signature_required"), None)
        if not signature_rule:
            return True
        
        if signature_rule["enforcement"] == "disabled":
            return True
        
        # Check if plugin has signature
        has_signature = bool(plugin_manifest.get("signature"))
        signature_type = plugin_manifest.get("signature_type", "none")
        
        if not has_signature:
            logger.warning(f"Plugin {plugin_manifest.get('name')} missing required signature")
            return False
        
        if signature_type not in ["rsa", "ecdsa"]:
            logger.warning(f"Plugin {plugin_manifest.get('name')} has unsupported signature type: {signature_type}")
            return False
        
        return True
    
    def _check_network_access(self, plugin_manifest: Dict[str, Any], 
                            policy: SecurityPolicy) -> bool:
        """Check if plugin network access is compliant."""
        network_rule = next((r for r in policy.rules if r["name"] == "network_access_denied"), None)
        if not network_rule:
            return True
        
        if network_rule["enforcement"] == "disabled":
            return True
        
        # Check if plugin requests network access
        security_profile = plugin_manifest.get("security_profile", {})
        permissions = security_profile.get("permissions", {})
        network_access = permissions.get("network_access", False)
        
        if network_access:
            logger.warning(f"Plugin {plugin_manifest.get('name')} requests network access (denied by policy)")
            return False
        
        return True
    
    def _check_filesystem_access(self, plugin_manifest: Dict[str, Any], 
                               policy: SecurityPolicy) -> bool:
        """Check if plugin filesystem access is compliant."""
        filesystem_rule = next((r for r in policy.rules if r["name"] == "filesystem_write_denied"), None)
        if not filesystem_rule:
            return True
        
        if filesystem_rule["enforcement"] == "disabled":
            return True
        
        # Check if plugin requests filesystem write access
        security_profile = plugin_manifest.get("security_profile", {})
        permissions = security_profile.get("permissions", {})
        filesystem_access = permissions.get("filesystem_access", {})
        read_only = filesystem_access.get("read_only", True)
        
        if not read_only:
            logger.warning(f"Plugin {plugin_manifest.get('name')} requests filesystem write access (denied by policy)")
            return False
        
        return True
    
    def _check_resource_limits(self, plugin_manifest: Dict[str, Any], 
                            policy: SecurityPolicy) -> bool:
        """Check if plugin resource limits are compliant."""
        resource_rule = next((r for r in policy.rules if r["name"] == "resource_limits"), None)
        if not resource_rule:
            return True
        
        if resource_rule["enforcement"] == "disabled":
            return True
        
        # Check if plugin has reasonable resource limits
        security_profile = plugin_manifest.get("security_profile", {})
        resource_limits = security_profile.get("resource_limits", {})
        
        cpu_seconds = resource_limits.get("cpu_seconds", 0)
        memory_mb = resource_limits.get("memory_mb", 0)
        
        # Check CPU limit (max 60 seconds)
        if cpu_seconds > 60:
            logger.warning(f"Plugin {plugin_manifest.get('name')} requests excessive CPU time: {cpu_seconds}s")
            return False
        
        # Check memory limit (max 512MB)
        if memory_mb > 512:
            logger.warning(f"Plugin {plugin_manifest.get('name')} requests excessive memory: {memory_mb}MB")
            return False
        
        return True
    
    def enforce_policy(self, plugin_manifest: Dict[str, Any], 
                      plugin_path: str) -> bool:
        """Enforce security policy for plugin."""
        result = self.check_plugin_policy(plugin_manifest, plugin_path)
        
        if not result.compliant:
            logger.error(f"Plugin {plugin_manifest.get('name')} violates security policies")
            return False
        
        return True

class PluginSecurityEnforcer:
    """Enforces security policies for plugin execution."""
    
    def __init__(self, policy_manager: SecurityPolicyManager):
        self.policy_manager = policy_manager
        self.audit_logger = logging.getLogger("security.audit")
    
    def validate_plugin(self, plugin_manifest: Dict[str, Any], 
                       plugin_path: str) -> Tuple[bool, List[str]]:
        """Validate plugin against security policies."""
        try:
            # Check policy compliance
            result = self.policy_manager.check_plugin_policy(plugin_manifest, plugin_path)
            
            if not result.compliant:
                error_messages = [f"Policy violation: {v.value}" for v in result.violations]
                return False, error_messages
            
            # Additional security checks
            additional_errors = self._additional_security_checks(plugin_manifest, plugin_path)
            
            if additional_errors:
                return False, additional_errors
            
            return True, []
            
        except Exception as e:
            logger.error(f"Plugin validation failed: {e}")
            return False, [f"Validation error: {str(e)}"]
    
    def _additional_security_checks(self, plugin_manifest: Dict[str, Any], 
                                  plugin_path: str) -> List[str]:
        """Perform additional security checks."""
        errors = []
        
        try:
            # Check plugin file exists and is readable
            if not pathlib.Path(plugin_path).exists():
                errors.append("Plugin file does not exist")
                return errors
            
            # Check plugin file permissions
            plugin_file = pathlib.Path(plugin_path)
            if plugin_file.stat().st_mode & 0o002:  # World writable
                errors.append("Plugin file is world writable (security risk)")
            
            # Check manifest integrity
            if not self._check_manifest_integrity(plugin_manifest):
                errors.append("Plugin manifest integrity check failed")
            
            # Check for suspicious patterns
            if self._check_suspicious_patterns(plugin_manifest):
                errors.append("Plugin manifest contains suspicious patterns")
            
        except Exception as e:
            errors.append(f"Additional security check failed: {str(e)}")
        
        return errors
    
    def _check_manifest_integrity(self, plugin_manifest: Dict[str, Any]) -> bool:
        """Check plugin manifest integrity."""
        required_fields = ["name", "version", "description", "author", "entrypoint"]
        
        for field in required_fields:
            if field not in plugin_manifest:
                logger.warning(f"Plugin manifest missing required field: {field}")
                return False
        
        return True
    
    def _check_suspicious_patterns(self, plugin_manifest: Dict[str, Any]) -> bool:
        """Check for suspicious patterns in plugin manifest."""
        suspicious_patterns = [
            "eval", "exec", "import os", "subprocess", "socket",
            "urllib", "requests", "http", "ftp", "file://"
        ]
        
        manifest_str = json.dumps(plugin_manifest).lower()
        
        for pattern in suspicious_patterns:
            if pattern in manifest_str:
                logger.warning(f"Suspicious pattern found in plugin manifest: {pattern}")
                return True
        
        return False

# Convenience functions
def check_plugin_security(plugin_manifest: Dict[str, Any], 
                         plugin_path: str) -> Tuple[bool, List[str]]:
    """Check plugin security compliance."""
    policy_manager = SecurityPolicyManager()
    enforcer = PluginSecurityEnforcer(policy_manager)
    return enforcer.validate_plugin(plugin_manifest, plugin_path)

def enforce_security_policy(plugin_manifest: Dict[str, Any], 
                          plugin_path: str) -> bool:
    """Enforce security policy for plugin."""
    policy_manager = SecurityPolicyManager()
    return policy_manager.enforce_policy(plugin_manifest, plugin_path)

# CLI interface
def main():
    """CLI interface for policy enforcement."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security policy enforcement")
    parser.add_argument("manifest", help="Plugin manifest file")
    parser.add_argument("plugin", help="Plugin file path")
    parser.add_argument("--policy-dir", default="security/policies", help="Policy directory")
    
    args = parser.parse_args()
    
    # Load manifest
    with open(args.manifest, 'r') as f:
        manifest = json.load(f)
    
    # Check security
    compliant, errors = check_plugin_security(manifest, args.plugin)
    
    if compliant:
        print("✅ Plugin is compliant with security policies")
    else:
        print("❌ Plugin violates security policies:")
        for error in errors:
            print(f"  - {error}")
        exit(1)

if __name__ == "__main__":
    main()
