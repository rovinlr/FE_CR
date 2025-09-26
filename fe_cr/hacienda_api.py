"""Cliente ligero para la API de recepción de Hacienda (Costa Rica)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from urllib import error, request

from .exceptions import ValidationError
from .models import ElectronicInvoice, Identification
from .xml_builder import render_invoice

_ENVIRONMENT_URLS = {
    "production": "https://api.comprobanteselectronicos.go.cr/recepcion/v1",
    "prod": "https://api.comprobanteselectronicos.go.cr/recepcion/v1",
    "testing": "https://api-sandbox.comprobanteselectronicos.go.cr/recepcion/v1",
    "test": "https://api-sandbox.comprobanteselectronicos.go.cr/recepcion/v1",
    "sandbox": "https://api-sandbox.comprobanteselectronicos.go.cr/recepcion/v1",
}


class HaciendaAPIError(Exception):
    """Errores devueltos por la API del Ministerio de Hacienda."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, payload: Any | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class _HTTPResponse:
    def __init__(self, status_code: int, body: bytes, headers: Dict[str, str]):
        self.status_code = status_code
        self._body = body
        self.text = body.decode("utf-8", errors="replace")
        self.headers = headers

    def json(self) -> Dict[str, Any]:
        return json.loads(self.text or "{}")


class _UrllibSession:
    def post(self, url: str, *, json_body: Dict[str, Any], headers: Optional[Dict[str, str]], timeout: float | None) -> _HTTPResponse:
        data = json.dumps(json_body).encode("utf-8")
        headers = {"Content-Type": "application/json", **(headers or {})}
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return _HTTPResponse(resp.getcode(), body, dict(resp.headers))
        except error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return _HTTPResponse(exc.code, body, dict(exc.headers or {}))

    def get(self, url: str, *, headers: Optional[Dict[str, str]], timeout: float | None) -> _HTTPResponse:
        req = request.Request(url, headers=headers or {}, method="GET")
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                return _HTTPResponse(resp.getcode(), body, dict(resp.headers))
        except error.HTTPError as exc:
            body = exc.read() if hasattr(exc, "read") else b""
            return _HTTPResponse(exc.code, body, dict(exc.headers or {}))


@dataclass
class HaciendaAPI:
    """Cliente HTTP sencillo para la API de recepción v1."""

    environment: str = "production"
    timeout: float = 30.0
    session: Any | None = None

    def __post_init__(self) -> None:
        env_key = self.environment.lower()
        if env_key not in _ENVIRONMENT_URLS:
            raise ValueError(f"Ambiente de Hacienda desconocido: {self.environment}")
        self._base_url = _ENVIRONMENT_URLS[env_key]
        self._session = self.session or _UrllibSession()
        self._token: Optional[str] = None

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------
    def authenticate(self, username: str, password: str) -> str:
        """Solicita un token a la API de Hacienda."""

        response = self._session.post(
            f"{self._base_url}/auth",
            json_body={"username": username, "password": password},
            headers=None,
            timeout=self.timeout,
        )
        data = self._process_response(response)
        token = data.get("token")
        if not token:
            raise HaciendaAPIError("La respuesta de Hacienda no contiene token", status_code=response.status_code, payload=data)
        self._token = token
        return token

    def set_token(self, token: str) -> None:
        """Permite establecer manualmente un token ya obtenido."""

        self._token = token

    # ------------------------------------------------------------------
    # Envío y consulta de comprobantes
    # ------------------------------------------------------------------
    def submit_invoice(
        self,
        invoice: ElectronicInvoice,
        *,
        xml: str | bytes | None = None,
        receptor_consecutivo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Envía un comprobante en formato XML base64 a la API."""

        if not self._token:
            raise HaciendaAPIError("No se ha autenticado con Hacienda")

        xml_content = xml or render_invoice(invoice)
        xml_bytes = xml_content.encode("utf-8") if isinstance(xml_content, str) else xml_content

        payload: Dict[str, Any] = {
            "clave": invoice.clave,
            "fecha": _format_datetime(invoice.fecha_emision),
            "emisor": _identification_payload(invoice.emisor.identificacion),
            "comprobanteXml": base64.b64encode(xml_bytes).decode("ascii"),
        }

        if invoice.receptor and invoice.receptor.identificacion:
            payload["receptor"] = _identification_payload(invoice.receptor.identificacion)
        if receptor_consecutivo:
            payload["consecutivoReceptor"] = receptor_consecutivo

        response = self._session.post(
            f"{self._base_url}/recepcion",
            json_body=payload,
            headers=self._auth_headers(),
            timeout=self.timeout,
        )
        return self._process_response(response)

    def fetch_status(self, clave: str) -> Dict[str, Any]:
        """Consulta el estado de un comprobante por medio de su clave."""

        if not self._token:
            raise HaciendaAPIError("No se ha autenticado con Hacienda")

        response = self._session.get(
            f"{self._base_url}/recepcion/{clave}",
            headers=self._auth_headers(),
            timeout=self.timeout,
        )
        return self._process_response(response)

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    def _auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    @staticmethod
    def _process_response(response: _HTTPResponse) -> Dict[str, Any]:
        try:
            data = response.json()
        except ValueError:
            data = {"raw": response.text}

        if response.status_code >= 400:
            raise HaciendaAPIError(
                "Error en la respuesta de Hacienda",
                status_code=response.status_code,
                payload=data,
            )
        return data


def _identification_payload(identificacion: Identification) -> Dict[str, str]:
    return {
        "tipoIdentificacion": identificacion.tipo,
        "numeroIdentificacion": identificacion.numero,
    }


def _format_datetime(value: datetime) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.isoformat(timespec="seconds")
        return value.isoformat(timespec="seconds")
    raise ValidationError("Fecha de emisión inválida", field="FechaEmision")
