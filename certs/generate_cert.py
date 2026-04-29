from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
import datetime
import socket
import ipaddress

def generate_self_signed_cert():
    print("Generating self-signed SSL certificate...")
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Get local IP address to set as Common Name
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    # Generate public certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"California"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Local Web Gyro"),
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
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
        datetime.datetime.utcnow()
    ).not_valid_after(
        # Our certificate will be valid for 10 years
        datetime.datetime.utcnow() + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([x509.DNSName(u"localhost"), x509.IPAddress(ipaddress.IPv4Address(local_ip))]),
        critical=False,
    ).sign(private_key, hashes.SHA256())

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    key_path = os.path.join(BASE_DIR, "key.pem")
    cert_path = os.path.join(BASE_DIR, "cert.pem")

    # Write the private key
    with open(key_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write the certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print(f"Successfully generated cert.pem and key.pem for {local_ip} at {BASE_DIR}")

if __name__ == "__main__":
    generate_self_signed_cert()
