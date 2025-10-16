# Plugin Signature Verification Module

"""
Plugin signature verification using RSA/ECDSA cryptography.

This module provides cryptographic signature verification for plugins,
ensuring authenticity and preventing tampering.
"""

import hashlib
import json
import logging
import pathlib
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

@dataclass
class PluginManifest:
    """Plugin manifest with signature information."""
    name: str
    version: str
    description: str
    author: str
    entrypoint: str
    code_hash: str
    signature: Optional[str] = None
    signature_type: str = "rsa"
    created_at: str = None
    expires_at: Optional[str] = None

@dataclass
class SignatureVerificationResult:
    """Result of signature verification."""
    valid: bool
    plugin_name: str
    signature_type: str
    verification_time: float
    error: Optional[str] = None
    audit_record: Optional[Dict[str, Any]] = None

class PluginSigner:
    """Plugin signing functionality."""
    
    def __init__(self, private_key_path: Optional[str] = None):
        self.private_key_path = private_key_path
        self.private_key = None
        self.public_key = None
        
        if private_key_path and pathlib.Path(private_key_path).exists():
            self._load_keys()
    
    def _load_keys(self):
        """Load private and public keys from file."""
        try:
            with open(self.private_key_path, 'rb') as f:
                self.private_key = load_pem_private_key(f.read(), password=None)
            
            # Extract public key
            self.public_key = self.private_key.public_key()
            logger.info(f"Loaded keys from {self.private_key_path}")
            
        except Exception as e:
            logger.error(f"Failed to load keys from {self.private_key_path}: {e}")
            raise
    
    def generate_key_pair(self, key_size: int = 2048, algorithm: str = "rsa") -> Tuple[bytes, bytes]:
        """Generate a new key pair for testing."""
        if algorithm == "rsa":
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size
            )
        elif algorithm == "ecdsa":
            private_key = ec.generate_private_key(ec.SECP256R1())
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
    
    def calculate_plugin_hash(self, plugin_path: str) -> str:
        """Calculate SHA256 hash of plugin file."""
        plugin_file = pathlib.Path(plugin_path)
        if not plugin_file.exists():
            raise FileNotFoundError(f"Plugin file not found: {plugin_path}")
        
        sha256_hash = hashlib.sha256()
        with open(plugin_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def sign_plugin(self, manifest: PluginManifest, plugin_path: str) -> str:
        """Sign a plugin manifest."""
        if not self.private_key:
            raise ValueError("Private key not loaded")
        
        # Calculate plugin hash
        manifest.code_hash = self.calculate_plugin_hash(plugin_path)
        manifest.created_at = datetime.utcnow().isoformat()
        
        # Create manifest bytes for signing
        manifest_data = {
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "author": manifest.author,
            "entrypoint": manifest.entrypoint,
            "code_hash": manifest.code_hash,
            "created_at": manifest.created_at,
            "expires_at": manifest.expires_at
        }
        
        manifest_bytes = json.dumps(manifest_data, sort_keys=True).encode('utf-8')
        
        # Sign the manifest
        if manifest.signature_type == "rsa":
            signature = self.private_key.sign(
                manifest_bytes,
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        elif manifest.signature_type == "ecdsa":
            signature = self.private_key.sign(
                manifest_bytes,
                ec.ECDSA(hashes.SHA256())
            )
        else:
            raise ValueError(f"Unsupported signature type: {manifest.signature_type}")
        
        # Encode signature as base64
        import base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        logger.info(f"Signed plugin manifest for {manifest.name}")
        return signature_b64

class PluginSignatureVerifier:
    """Plugin signature verification functionality."""
    
    def __init__(self, public_key_path: Optional[str] = None):
        self.public_key_path = public_key_path
        self.public_key = None
        
        if public_key_path and pathlib.Path(public_key_path).exists():
            self._load_public_key()
    
    def _load_public_key(self):
        """Load public key from file."""
        try:
            with open(self.public_key_path, 'rb') as f:
                self.public_key = load_pem_public_key(f.read())
            
            logger.info(f"Loaded public key from {self.public_key_path}")
            
        except Exception as e:
            logger.error(f"Failed to load public key from {self.public_key_path}: {e}")
            raise
    
    def verify_plugin_signature(self, manifest: PluginManifest, plugin_path: str) -> SignatureVerificationResult:
        """Verify plugin signature."""
        start_time = time.time()
        
        try:
            # Validate manifest
            if not manifest.signature:
                raise ValueError("No signature provided in manifest")
            
            if not manifest.code_hash:
                raise ValueError("No code hash provided in manifest")
            
            # Verify plugin hash matches manifest
            calculated_hash = self._calculate_plugin_hash(plugin_path)
            if calculated_hash != manifest.code_hash:
                raise ValueError(f"Plugin hash mismatch. Expected: {manifest.code_hash}, Got: {calculated_hash}")
            
            # Create manifest data for verification
            manifest_data = {
                "name": manifest.name,
                "version": manifest.version,
                "description": manifest.description,
                "author": manifest.author,
                "entrypoint": manifest.entrypoint,
                "code_hash": manifest.code_hash,
                "created_at": manifest.created_at,
                "expires_at": manifest.expires_at
            }
            
            manifest_bytes = json.dumps(manifest_data, sort_keys=True).encode('utf-8')
            
            # Decode signature
            import base64
            signature_bytes = base64.b64decode(manifest.signature)
            
            # Verify signature
            if manifest.signature_type == "rsa":
                if not self.public_key:
                    raise ValueError("RSA public key not loaded")
                
                self.public_key.verify(
                    signature_bytes,
                    manifest_bytes,
                    padding.PKCS1v15(),
                    hashes.SHA256()
                )
            elif manifest.signature_type == "ecdsa":
                if not self.public_key:
                    raise ValueError("ECDSA public key not loaded")
                
                self.public_key.verify(
                    signature_bytes,
                    manifest_bytes,
                    ec.ECDSA(hashes.SHA256())
                )
            else:
                raise ValueError(f"Unsupported signature type: {manifest.signature_type}")
            
            verification_time = time.time() - start_time
            
            # Create audit record
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_signature_verification",
                "plugin_name": manifest.name,
                "plugin_version": manifest.version,
                "signature_type": manifest.signature_type,
                "verification_result": "valid",
                "verification_time": verification_time,
                "plugin_path": plugin_path
            }
            
            logger.info(f"Plugin {manifest.name} signature verification successful")
            
            return SignatureVerificationResult(
                valid=True,
                plugin_name=manifest.name,
                signature_type=manifest.signature_type,
                verification_time=verification_time,
                audit_record=audit_record
            )
            
        except InvalidSignature:
            verification_time = time.time() - start_time
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_signature_verification",
                "plugin_name": manifest.name,
                "plugin_version": manifest.version,
                "signature_type": manifest.signature_type,
                "verification_result": "invalid_signature",
                "verification_time": verification_time,
                "plugin_path": plugin_path
            }
            
            logger.warning(f"Plugin {manifest.name} signature verification failed: invalid signature")
            
            return SignatureVerificationResult(
                valid=False,
                plugin_name=manifest.name,
                signature_type=manifest.signature_type,
                verification_time=verification_time,
                error="Invalid signature",
                audit_record=audit_record
            )
            
        except Exception as e:
            verification_time = time.time() - start_time
            
            audit_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": "plugin_signature_verification",
                "plugin_name": manifest.name,
                "plugin_version": manifest.version,
                "signature_type": manifest.signature_type,
                "verification_result": "error",
                "verification_time": verification_time,
                "plugin_path": plugin_path,
                "error": str(e)
            }
            
            logger.error(f"Plugin {manifest.name} signature verification failed: {e}")
            
            return SignatureVerificationResult(
                valid=False,
                plugin_name=manifest.name,
                signature_type=manifest.signature_type,
                verification_time=verification_time,
                error=str(e),
                audit_record=audit_record
            )
    
    def _calculate_plugin_hash(self, plugin_path: str) -> str:
        """Calculate SHA256 hash of plugin file."""
        plugin_file = pathlib.Path(plugin_path)
        if not plugin_file.exists():
            raise FileNotFoundError(f"Plugin file not found: {plugin_path}")
        
        sha256_hash = hashlib.sha256()
        with open(plugin_file, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()

# Convenience functions for integration
def sign_plugin(manifest: PluginManifest, plugin_path: str, private_key_path: str) -> str:
    """Sign a plugin manifest using private key."""
    signer = PluginSigner(private_key_path)
    return signer.sign_plugin(manifest, plugin_path)

def verify_plugin_signature(manifest: PluginManifest, plugin_path: str, public_key_path: str) -> SignatureVerificationResult:
    """Verify plugin signature using public key."""
    verifier = PluginSignatureVerifier(public_key_path)
    return verifier.verify_plugin_signature(manifest, plugin_path)

# CLI interface
def main():
    """CLI interface for plugin signing and verification."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Plugin signature verification")
    parser.add_argument("action", choices=["sign", "verify"], help="Action to perform")
    parser.add_argument("manifest", help="Plugin manifest file")
    parser.add_argument("plugin", help="Plugin file path")
    parser.add_argument("--key", required=True, help="Private key file (for signing) or public key file (for verification)")
    parser.add_argument("--signature-type", default="rsa", choices=["rsa", "ecdsa"], help="Signature type")
    
    args = parser.parse_args()
    
    if args.action == "sign":
        # Load manifest
        with open(args.manifest, 'r') as f:
            manifest_data = json.load(f)
        
        manifest = PluginManifest(
            name=manifest_data["name"],
            version=manifest_data["version"],
            description=manifest_data["description"],
            author=manifest_data["author"],
            entrypoint=manifest_data["entrypoint"],
            signature_type=args.signature_type
        )
        
        # Sign plugin
        signature = sign_plugin(manifest, args.plugin, args.key)
        
        # Update manifest with signature
        manifest_data["signature"] = signature
        manifest_data["signature_type"] = args.signature_type
        
        # Save updated manifest
        with open(args.manifest, 'w') as f:
            json.dump(manifest_data, f, indent=2)
        
        print(f"Plugin {manifest.name} signed successfully")
        
    elif args.action == "verify":
        # Load manifest
        with open(args.manifest, 'r') as f:
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
        
        # Verify plugin
        result = verify_plugin_signature(manifest, args.plugin, args.key)
        
        if result.valid:
            print(f"✅ Plugin {manifest.name} signature verification successful")
        else:
            print(f"❌ Plugin {manifest.name} signature verification failed: {result.error}")
            exit(1)

if __name__ == "__main__":
    main()
