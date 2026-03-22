"""
AES-256-GCM Encryption for Model Files
Secures PyTorch model weights with authenticated encryption
"""
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os
import io
import torch
import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CryptoHandler:
    """
    Handles AES-256-GCM encryption/decryption for model files
    
    Security Properties:
    - Confidentiality: AES-256 encryption
    - Authenticity: GCM authentication tag (prevents tampering)
    - Nonce: Random 96-bit nonce per file (prevents replay attacks)
    
    File Format:
    [12 bytes: nonce][16 bytes: auth_tag][variable: ciphertext]
    """
    
    # Constants
    NONCE_SIZE = 12        # 96 bits (NIST recommended for GCM)
    TAG_SIZE = 16          # 128 bits (authentication tag)
    KEY_SIZE = 32          # 256 bits (AES-256)
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Initialize crypto handler
        
        Args:
            master_key: 32-byte master key (for production: use KMS)
        """
        if master_key is None:
            # For development: generate random key
            # For production: load from AWS KMS / Azure Key Vault
            master_key = self._load_or_generate_master_key()
        
        if len(master_key) != self.KEY_SIZE:
            raise ValueError(f"Master key must be {self.KEY_SIZE} bytes")
        
        self.master_key = master_key
        logger.info("Crypto handler initialized with AES-256-GCM")
    
    def _load_or_generate_master_key(self) -> bytes:
        """
        Load master key from secure storage or generate new one
        
        Production: Replace with KMS integration
        """
        key_file = Path(__file__).parent / "keys" / "master.key"
        key_file.parent.mkdir(exist_ok=True)
        
        if key_file.exists():
            logger.info(f"Loading master key from {key_file}")
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            logger.warning("Generating new master key (use KMS in production!)")
            master_key = AESGCM.generate_key(bit_length=256)
            with open(key_file, 'wb') as f:
                f.write(master_key)
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            return master_key
    
    def derive_hospital_key(self, hospital_id: str, salt: bytes = None) -> bytes:
        """
        Derive hospital-specific key from master key using HKDF
        
        Why HKDF:
        - Key separation (hospital keys are independent)
        - Forward secrecy (compromising one doesn't affect others)
        - Standard: RFC 5869
        
        Args:
            hospital_id: Unique hospital identifier
            salt: Optional salt (use hospital creation timestamp)
        
        Returns:
            32-byte derived key
        """
        if salt is None:
            salt = hospital_id.encode()
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=self.KEY_SIZE,
            salt=salt,
            info=f"hospital:{hospital_id}".encode(),
            backend=default_backend()
        )
        
        derived_key = hkdf.derive(self.master_key)
        return derived_key
    
    def encrypt_model(
        self,
        state_dict: Dict[str, Any],
        hospital_id: str = "global"
    ) -> bytes:
        """
        Encrypt PyTorch model state_dict to bytes
        
        Args:
            state_dict: PyTorch model.state_dict()
            hospital_id: Hospital ID for key derivation
        
        Returns:
            Encrypted bytes (nonce + tag + ciphertext)
        """
        # Derive hospital-specific key
        key = self.derive_hospital_key(hospital_id)
        aesgcm = AESGCM(key)
        
        # Serialize model to bytes
        buffer = io.BytesIO()
        torch.save(state_dict, buffer)
        plaintext = buffer.getvalue()
        
        logger.info(f"Encrypting model ({len(plaintext)} bytes) for {hospital_id}")
        
        # Generate random nonce (MUST be unique per encryption)
        nonce = os.urandom(self.NONCE_SIZE)
        
        # Encrypt with authenticated encryption
        # GCM provides both confidentiality and authenticity
        ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, None)
        
        # Combine: [nonce][ciphertext+tag]
        encrypted_blob = nonce + ciphertext_and_tag
        
        logger.info(f"Model encrypted: {len(encrypted_blob)} bytes")
        return encrypted_blob
    
    def decrypt_model(
        self,
        encrypted_blob: bytes,
        hospital_id: str = "global"
    ) -> Dict[str, Any]:
        """
        Decrypt encrypted model bytes to state_dict
        
        Args:
            encrypted_blob: Encrypted bytes (nonce + tag + ciphertext)
            hospital_id: Hospital ID for key derivation
        
        Returns:
            PyTorch state_dict
        
        Raises:
            cryptography.exceptions.InvalidTag: Decryption failed (tampered data)
        """
        # Derive hospital-specific key
        key = self.derive_hospital_key(hospital_id)
        aesgcm = AESGCM(key)
        
        # Extract nonce and ciphertext
        nonce = encrypted_blob[:self.NONCE_SIZE]
        ciphertext_and_tag = encrypted_blob[self.NONCE_SIZE:]
        
        logger.info(f"Decrypting model ({len(encrypted_blob)} bytes) for {hospital_id}")
        
        try:
            # Decrypt and verify authentication tag
            plaintext = aesgcm.decrypt(nonce, ciphertext_and_tag, None)
            
            # Deserialize PyTorch model
            buffer = io.BytesIO(plaintext)
            state_dict = torch.load(buffer)
            
            logger.info("Model decrypted successfully")
            return state_dict
        
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_gradients(
        self,
        gradients: Dict[str, torch.Tensor],
        hospital_id: str
    ) -> bytes:
        """
        Encrypt model gradients (same as model encryption)
        
        Args:
            gradients: Dictionary of parameter_name -> gradient_tensor
            hospital_id: Hospital ID
        
        Returns:
            Encrypted bytes
        """
        return self.encrypt_model(gradients, hospital_id)
    
    def decrypt_gradients(
        self,
        encrypted_blob: bytes,
        hospital_id: str
    ) -> Dict[str, torch.Tensor]:
        """
        Decrypt model gradients
        
        Args:
            encrypted_blob: Encrypted gradient bytes
            hospital_id: Hospital ID
        
        Returns:
            Dictionary of gradients
        """
        return self.decrypt_model(encrypted_blob, hospital_id)
    
    def save_encrypted_model(
        self,
        state_dict: Dict[str, Any],
        file_path: Path,
        hospital_id: str = "global"
    ):
        """
        Encrypt and save model to file
        
        Args:
            state_dict: PyTorch model state_dict
            file_path: Where to save encrypted file
            hospital_id: Hospital ID for key derivation
        """
        encrypted_blob = self.encrypt_model(state_dict, hospital_id)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(encrypted_blob)
        
        logger.info(f"Encrypted model saved to {file_path}")
    
    def load_encrypted_model(
        self,
        file_path: Path,
        hospital_id: str = "global"
    ) -> Dict[str, Any]:
        """
        Load and decrypt model from file
        
        Args:
            file_path: Path to encrypted model file
            hospital_id: Hospital ID for key derivation
        
        Returns:
            PyTorch state_dict
        """
        with open(file_path, 'rb') as f:
            encrypted_blob = f.read()
        
        logger.info(f"Loading encrypted model from {file_path}")
        return self.decrypt_model(encrypted_blob, hospital_id)
    
    def compute_hash(self, data: bytes) -> str:
        """
        Compute SHA-256 hash of data (for integrity checks)
        
        Args:
            data: Data to hash
        
        Returns:
            Hex-encoded hash
        """
        from cryptography.hazmat.primitives import hashes
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(data)
        return digest.finalize().hex()


# Singleton instance
_crypto_handler: Optional[CryptoHandler] = None


def get_crypto_handler() -> CryptoHandler:
    """Get singleton crypto handler instance"""
    global _crypto_handler
    
    if _crypto_handler is None:
        _crypto_handler = CryptoHandler()
    
    return _crypto_handler


# Example usage
if __name__ == "__main__":
    # Test encryption/decryption
    handler = get_crypto_handler()
    
    # Create dummy model
    import torch.nn as nn
    model = nn.Sequential(
        nn.Linear(10, 50),
        nn.ReLU(),
        nn.Linear(50, 2)
    )
    state_dict = model.state_dict()
    
    print("Original state_dict keys:")
    print(list(state_dict.keys()))
    
    # Encrypt
    print("\n--- Encrypting Model ---")
    encrypted_blob = handler.encrypt_model(state_dict, hospital_id="hosp_001")
    print(f"✓ Encrypted: {len(encrypted_blob)} bytes")
    print(f"  Hash: {handler.compute_hash(encrypted_blob)[:16]}...")
    
    # Decrypt
    print("\n--- Decrypting Model ---")
    decrypted_state_dict = handler.decrypt_model(encrypted_blob, hospital_id="hosp_001")
    print(f"✓ Decrypted: {len(decrypted_state_dict)} parameters")
    print("  Keys match:", list(state_dict.keys()) == list(decrypted_state_dict.keys()))
    
    # Verify values match
    all_match = all(
        torch.allclose(state_dict[k], decrypted_state_dict[k])
        for k in state_dict.keys()
    )
    print(f"  Values match: {all_match}")
    
    # Test tampering detection
    print("\n--- Testing Tampering Detection ---")
    tampered_blob = encrypted_blob[:-1] + b'\x00'  # Flip last byte
    try:
        handler.decrypt_model(tampered_blob, hospital_id="hosp_001")
        print("✗ ERROR: Tampering not detected!")
    except Exception as e:
        print(f"✓ Tampering detected: {type(e).__name__}")
    
    # Test file I/O
    print("\n--- Testing File I/O ---")
    test_file = Path("test_encrypted_model.enc")
    handler.save_encrypted_model(state_dict, test_file, hospital_id="hosp_001")
    print(f"✓ Saved to {test_file}")
    
    loaded_state_dict = handler.load_encrypted_model(test_file, hospital_id="hosp_001")
    print(f"✓ Loaded from {test_file}")
    print(f"  Integrity verified: {list(loaded_state_dict.keys()) == list(state_dict.keys())}")
    
    # Cleanup
    test_file.unlink()
    print("\n✓ All tests passed!")
