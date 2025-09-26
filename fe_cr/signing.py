"""Herramientas para firmar XML con certificados de Hacienda."""

from __future__ import annotations

import base64
from typing import Iterable, Optional

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from signxml import XMLSigner, methods


class CertificateError(Exception):
    """Errores relacionados con la carga del certificado P12."""


def _load_pkcs12(p12_data: bytes, password: str | bytes | None):
    password_bytes: Optional[bytes]
    if password is None:
        password_bytes = None
    elif isinstance(password, str):
        password_bytes = password.encode("utf-8")
    else:
        password_bytes = password

    private_key, cert, additional_certs = pkcs12.load_key_and_certificates(p12_data, password_bytes)
    if private_key is None or cert is None:
        raise CertificateError("El certificado P12 no contiene llave privada o certificado")
    return private_key, cert, additional_certs or []


def _pem_bytes(cert: x509.Certificate) -> bytes:
    return cert.public_bytes(serialization.Encoding.PEM)


def _serialize_private_key(private_key) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def sign_xml_with_p12(xml_content: bytes | str, p12_data: bytes | str, password: str | bytes | None) -> bytes:
    """Firma un XML utilizando un certificado en formato P12.

    Parameters
    ----------
    xml_content:
        Contenido XML a firmar. Puede ser ``bytes`` o ``str``.
    p12_data:
        Contenido del archivo ``.p12`` en bytes o base64.
    password:
        Contraseña del certificado. Puede ser ``str`` o ``bytes``.

    Returns
    -------
    bytes
        XML firmado siguiendo el estándar XMLDSig requerido por Hacienda.
    """

    if isinstance(xml_content, str):
        xml_bytes = xml_content.encode("utf-8")
    else:
        xml_bytes = xml_content

    if isinstance(p12_data, str):
        try:
            p12_bytes = base64.b64decode(p12_data, validate=True)
        except (base64.binascii.Error, ValueError) as exc:  # type: ignore[attr-defined]
            raise CertificateError("El certificado P12 debe estar en formato binario o base64") from exc
    else:
        p12_bytes = p12_data

    private_key, certificate, extra_certs = _load_pkcs12(p12_bytes, password)

    try:
        xml_tree = etree.fromstring(xml_bytes)
    except etree.XMLSyntaxError as exc:  # pragma: no cover - lxml mensaje explicativo
        raise ValueError("El XML proporcionado no es válido") from exc

    signer = XMLSigner(
        method=methods.enveloped,
        signature_algorithm="rsa-sha256",
        digest_algorithm="sha256",
    )

    key_pem = _serialize_private_key(private_key)
    cert_pem = _pem_bytes(certificate)
    ca_pems: Iterable[bytes] = (_pem_bytes(cert) for cert in extra_certs)

    signed_root = signer.sign(
        xml_tree,
        key=key_pem,
        cert=cert_pem,
        key_name=certificate.subject.rfc4514_string(),
        ca_pem_list=list(ca_pems) or None,
    )

    return etree.tostring(signed_root, xml_declaration=True, encoding="utf-8")


__all__ = ["sign_xml_with_p12", "CertificateError"]
