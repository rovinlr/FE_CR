"""Herramientas para firmar XML con certificados de Hacienda."""

from __future__ import annotations

import base64
from typing import Iterable, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree


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

    cert_pem = _pem_bytes(certificate)
    ca_pems: Iterable[bytes] = (_pem_bytes(cert) for cert in extra_certs)

    signed_root = _sign_enveloped(
        xml_tree,
        private_key=private_key,
        certificate_pem=cert_pem,
        ca_pems=list(ca_pems),
        key_name=certificate.subject.rfc4514_string(),
    )

    return etree.tostring(signed_root, xml_declaration=True, encoding="utf-8")


def _sign_enveloped(
    xml_root: etree._Element,
    *,
    private_key,
    certificate_pem: bytes,
    ca_pems: list[bytes],
    key_name: str,
) -> etree._Element:
    """Firmar ``xml_root`` usando un ``Signature`` enveloped RSA-SHA256.

    Esta implementación reproduce el comportamiento requerido por el módulo
    sin depender de :mod:`signxml`, evitando así la necesidad de instalar
    dependencias externas en tiempo de ejecución.
    """

    ds_ns = "http://www.w3.org/2000/09/xmldsig#"
    nsmap = {"ds": ds_ns}

    signature_el = etree.Element(etree.QName(ds_ns, "Signature"), nsmap=nsmap)

    signed_info = etree.SubElement(signature_el, etree.QName(ds_ns, "SignedInfo"))
    etree.SubElement(
        signed_info,
        etree.QName(ds_ns, "CanonicalizationMethod"),
        Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )
    etree.SubElement(
        signed_info,
        etree.QName(ds_ns, "SignatureMethod"),
        Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
    )

    reference = etree.SubElement(signed_info, etree.QName(ds_ns, "Reference"), URI="")
    transforms = etree.SubElement(reference, etree.QName(ds_ns, "Transforms"))
    etree.SubElement(
        transforms,
        etree.QName(ds_ns, "Transform"),
        Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    )
    etree.SubElement(
        transforms,
        etree.QName(ds_ns, "Transform"),
        Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
    )

    etree.SubElement(
        reference,
        etree.QName(ds_ns, "DigestMethod"),
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )

    digest_value = etree.SubElement(reference, etree.QName(ds_ns, "DigestValue"))
    digest_value.text = _digest_base64(xml_root)

    signed_info_c14n = etree.tostring(
        signed_info,
        method="c14n",
        exclusive=True,
        with_comments=False,
    )

    signature_value = etree.SubElement(signature_el, etree.QName(ds_ns, "SignatureValue"))
    signature_value.text = _signature_base64(signed_info_c14n, private_key)

    key_info = etree.SubElement(signature_el, etree.QName(ds_ns, "KeyInfo"))
    key_name_el = etree.SubElement(key_info, etree.QName(ds_ns, "KeyName"))
    key_name_el.text = key_name

    x509_data = etree.SubElement(key_info, etree.QName(ds_ns, "X509Data"))
    etree.SubElement(x509_data, etree.QName(ds_ns, "X509Certificate")).text = _pem_body_b64(
        certificate_pem
    )
    for ca_pem in ca_pems:
        etree.SubElement(x509_data, etree.QName(ds_ns, "X509Certificate")).text = _pem_body_b64(
            ca_pem
        )

    xml_root.append(signature_el)
    return xml_root


def _digest_base64(xml_root: etree._Element) -> str:
    canonical = etree.tostring(xml_root, method="c14n", exclusive=True, with_comments=False)
    digest = hashes.Hash(hashes.SHA256())
    digest.update(canonical)
    return base64.b64encode(digest.finalize()).decode("ascii")


def _signature_base64(signed_info: bytes, private_key) -> str:
    signature = private_key.sign(signed_info, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("ascii")


def _pem_body_b64(pem_bytes: bytes) -> str:
    lines = pem_bytes.decode("ascii").splitlines()
    body = [line for line in lines if not line.startswith("---") and line.strip()]
    return "".join(body)


__all__ = ["sign_xml_with_p12", "CertificateError"]
