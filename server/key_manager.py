#!/usr/bin/env python3

import os
import json
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature
from base64 import b64encode, b64decode

class KeyManager:
    def __init__(self, keys_dir=None, public_keys_dir=None):
        """Initialize KeyManager with directories for key storage.
        
        Args:
            keys_dir: Directory for private keys (installation-specific)
            public_keys_dir: Directory for public keys (shared in repo)
        """
        self.keys_dir = Path(keys_dir) if keys_dir else Path('keys')
        self.public_keys_dir = Path(public_keys_dir) if public_keys_dir else Path('identity/public_keys')
        
        # Ensure directories exist
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.public_keys_dir.mkdir(parents=True, exist_ok=True)

    def has_key_pair(self, username):
        """Check if a user has a key pair."""
        key_file = self.public_keys_dir / f"{username}.pub"
        return key_file.exists()

    def get_public_key(self, username):
        """Get a user's public key."""
        key_file = self.public_keys_dir / f"{username}.pub"
        if key_file.exists():
            return key_file.read_text().strip()
        return None

    def sign_message(self, message_content, username):
        """Sign a message for a user."""
        key_file = self.keys_dir / f"{username}.pem"
        if not key_file.exists():
            return None
            
        try:
            # Sign message using private key
            with open(key_file, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None
                )
            
            # Create signature
            signature = private_key.sign(
                message_content.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return signature.hex()
        except Exception as e:
            print(f"Error signing message: {e}")
            return None

    def verify_signature(self, message_content, signature_hex, public_key_pem):
        """Verify a message signature."""
        try:
            # Convert hex signature back to bytes
            signature = bytes.fromhex(signature_hex)
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode()
            )
            
            # Verify signature
            try:
                public_key.verify(
                    signature,
                    message_content.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            except Exception:
                return False
        except Exception as e:
            print(f"Error verifying signature: {e}")
            return False
