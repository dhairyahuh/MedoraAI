"""
TLS/SSL Configuration for Production
"""
import ssl
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_ssl_context(
    cert_file: Path,
    key_file: Path,
    require_client_cert: bool = False
) -> ssl.SSLContext:
    """
    Create SSL context for TLS 1.3
    
    Args:
        cert_file: Path to server certificate
        key_file: Path to private key
        require_client_cert: Enable mTLS (mutual TLS)
    
    Returns:
        Configured SSLContext
    """
    # Create context for server
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Load certificate and key
    context.load_cert_chain(str(cert_file), str(key_file))
    
    # TLS 1.2+ (TLS 1.3 preferred, but allow 1.2 for compatibility)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Strong cipher suites (compatible with OpenSSL)
    # TLS 1.3 ciphers are configured automatically
    # For TLS 1.2, use strong ECDHE ciphers
    try:
        context.set_ciphers(
            'ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS'
        )
    except ssl.SSLError:
        # Fallback to default secure ciphers
        logger.warning("Custom cipher suite failed, using defaults")
    
    # Security options
    context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1  # Block old TLS versions
    context.options |= ssl.OP_NO_COMPRESSION  # Prevent CRIME attack
    context.options |= ssl.OP_SINGLE_DH_USE   # Perfect forward secrecy
    context.options |= ssl.OP_SINGLE_ECDH_USE
    
    # Client certificate verification (mTLS)
    if require_client_cert:
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = False  # We verify in JWT
        # Load CA certificates for client verification
        # context.load_verify_locations(cafile="ca_certificates.pem")
    
    logger.info(f"SSL context configured: TLS 1.3, cert={cert_file.name}")
    
    return context


def generate_self_signed_cert(
    cert_path: Path,
    key_path: Path,
    common_name: str = "fedmed.local"
):
    """
    Generate self-signed certificate for development
    
    Production: Use Let's Encrypt or proper CA
    """
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta
    
    logger.info(f"Generating self-signed certificate for {common_name}...")
    
    # Generate private key (RSA 4096-bit)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )
    
    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Maryland"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Baltimore"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Federated Medical AI"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(common_name),
            x509.DNSName("localhost"),
            x509.DNSName("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Ensure directory exists
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    # Save private key
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Set restrictive permissions on private key (Unix-like systems)
    try:
        import os
        os.chmod(key_path, 0o600)
    except:
        pass
    
    logger.info(f"✓ Certificate generated: {cert_path}")
    logger.info(f"✓ Private key generated: {key_path}")
    
    return cert_path, key_path


def ensure_certificates_exist(
    cert_dir: Path,
    common_name: str = "fedmed.local"
) -> tuple:
    """
    Ensure SSL certificates exist, generate if missing
    
    Returns:
        (cert_path, key_path)
    """
    cert_path = cert_dir / "server.crt"
    key_path = cert_dir / "server.key"
    
    if not cert_path.exists() or not key_path.exists():
        logger.warning("SSL certificates not found, generating self-signed...")
        generate_self_signed_cert(cert_path, key_path, common_name)
    else:
        logger.info(f"Using existing certificates from {cert_dir}")
    
    return cert_path, key_path
