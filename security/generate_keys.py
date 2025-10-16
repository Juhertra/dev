#!/usr/bin/env python3
"""
Generate test key pair for plugin signature verification.

This script generates RSA and ECDSA key pairs for testing the plugin
signature verification system.
"""

import os
import sys
from pathlib import Path

# Add security module to path
sys.path.insert(0, str(Path(__file__).parent))

from security.signing import PluginSigner

def generate_test_keys():
    """Generate test key pairs."""
    signer = PluginSigner()
    
    # Generate RSA key pair
    print("Generating RSA key pair...")
    rsa_private, rsa_public = signer.generate_key_pair(key_size=2048, algorithm="rsa")
    
    # Save RSA keys
    rsa_private_path = Path("security/keys/rsa_private.pem")
    rsa_public_path = Path("security/keys/rsa_public.pem")
    
    with open(rsa_private_path, 'wb') as f:
        f.write(rsa_private)
    
    with open(rsa_public_path, 'wb') as f:
        f.write(rsa_public)
    
    print(f"RSA private key saved to: {rsa_private_path}")
    print(f"RSA public key saved to: {rsa_public_path}")
    
    # Generate ECDSA key pair
    print("Generating ECDSA key pair...")
    ecdsa_private, ecdsa_public = signer.generate_key_pair(algorithm="ecdsa")
    
    # Save ECDSA keys
    ecdsa_private_path = Path("security/keys/ecdsa_private.pem")
    ecdsa_public_path = Path("security/keys/ecdsa_public.pem")
    
    with open(ecdsa_private_path, 'wb') as f:
        f.write(ecdsa_private)
    
    with open(ecdsa_public_path, 'wb') as f:
        f.write(ecdsa_public)
    
    print(f"ECDSA private key saved to: {ecdsa_private_path}")
    print(f"ECDSA public key saved to: {ecdsa_public_path}")
    
    # Create symlinks for default keys
    default_private_path = Path("security/keys/private.pem")
    default_public_path = Path("security/keys/public.pem")
    
    if default_private_path.exists():
        default_private_path.unlink()
    if default_public_path.exists():
        default_public_path.unlink()
    
    default_private_path.symlink_to("rsa_private.pem")
    default_public_path.symlink_to("rsa_public.pem")
    
    print(f"Default keys linked to RSA keys:")
    print(f"  Private: {default_private_path} -> rsa_private.pem")
    print(f"  Public: {default_public_path} -> rsa_public.pem")
    
    print("\n✅ Test key pairs generated successfully!")
    print("\nKey files:")
    print(f"  RSA Private: {rsa_private_path}")
    print(f"  RSA Public: {rsa_public_path}")
    print(f"  ECDSA Private: {ecdsa_private_path}")
    print(f"  ECDSA Public: {ecdsa_public_path}")
    print(f"  Default Private: {default_private_path}")
    print(f"  Default Public: {default_public_path}")

if __name__ == "__main__":
    generate_test_keys()
