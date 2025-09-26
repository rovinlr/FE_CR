from __future__ import annotations

from datetime import datetime, timedelta

import base64

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12

from lxml import etree

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

    _assert_signature_valid(signed)


def _assert_signature_valid(signed_xml: bytes) -> None:
    root = etree.fromstring(signed_xml)
    ds_ns = "http://www.w3.org/2000/09/xmldsig#"
    signature_el = root.find(f".//{{{ds_ns}}}Signature")
    assert signature_el is not None

    signed_info = signature_el.find(f"{{{ds_ns}}}SignedInfo")
    assert signed_info is not None

    signed_info_c14n = etree.tostring(
        signed_info,
        method="c14n",
        exclusive=True,
        with_comments=False,
    )

    signature_value_el = signature_el.find(f"{{{ds_ns}}}SignatureValue")
    assert signature_value_el is not None and signature_value_el.text
    signature_value = base64.b64decode(signature_value_el.text)

    cert_text = signature_el.findtext(f"{{{ds_ns}}}KeyInfo/{{{ds_ns}}}X509Data/{{{ds_ns}}}X509Certificate")
    assert cert_text
    cert = x509.load_der_x509_certificate(base64.b64decode(cert_text))

    cert.public_key().verify(
        signature_value,
        signed_info_c14n,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    digest_value_text = signature_el.findtext(
        f"{{{ds_ns}}}SignedInfo/{{{ds_ns}}}Reference/{{{ds_ns}}}DigestValue"
    )
    assert digest_value_text
    expected_digest = base64.b64decode(digest_value_text)

    root_without_signature = etree.fromstring(signed_xml)
    signature_to_remove = root_without_signature.find(f".//{{{ds_ns}}}Signature")
    assert signature_to_remove is not None
    signature_to_remove.getparent().remove(signature_to_remove)

    canonical = etree.tostring(
        root_without_signature,
        method="c14n",
        exclusive=True,
        with_comments=False,
    )

    digest = hashes.Hash(hashes.SHA256())
    digest.update(canonical)
    assert digest.finalize() == expected_digest
