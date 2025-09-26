from __future__ import annotations

from datetime import datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from signxml import XMLVerifier

from fe_cr.signing import sign_xml_with_p12


def _build_p12(password: str) -> bytes:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(x509.oid.NameOID.COUNTRY_NAME, "CR"),
            x509.NameAttribute(x509.oid.NameOID.ORGANIZATION_NAME, "Test"),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "Test Cert"),
        ]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow() - timedelta(days=1))
        .not_valid_after(datetime.utcnow() + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"test",
        key=key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode()),
    )


def test_sign_xml_with_p12_creates_valid_signature():
    xml_content = """
        <FacturaElectronica xmlns="https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica">
            <Clave>50602022300310112345600100001010000000012100000001</Clave>
        </FacturaElectronica>
    """.strip()
    p12_bytes = _build_p12("1234")

    signed = sign_xml_with_p12(xml_content, p12_bytes, "1234")

    assert b"Signature" in signed

    XMLVerifier().verify(signed)
