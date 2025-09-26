from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fe_cr import (
    ElectronicInvoice,
    Emisor,
    HaciendaAPI,
    HaciendaAPIError,
    Identification,
    InvoiceLine,
    InvoiceSummary,
    PaymentMethod,
    Receptor,
    SaleCondition,
    Tax,
)


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("No JSON")
        return self._json


class DummySession:
    def __init__(self):
        self.requests = []
        self.next_response = DummyResponse()

    def post(self, url, json_body=None, headers=None, timeout=None):
        self.requests.append(("POST", url, json_body, headers))
        return self.next_response

    def get(self, url, headers=None, timeout=None):
        self.requests.append(("GET", url, None, headers))
        return self.next_response


@pytest.fixture()
def invoice():
    emisor = Emisor(
        nombre="Mi Empresa",
        identificacion=Identification(tipo="02", numero="3101123456"),
    )
    receptor = Receptor(
        nombre="Cliente",
        identificacion=Identification(tipo="01", numero="101230123"),
    )
    line = InvoiceLine(
        numero_linea=1,
        codigo="ABC",
        cantidad=Decimal("1"),
        unidad_medida="Unid",
        detalle="Servicio",
        precio_unitario=Decimal("100"),
        monto_total=Decimal("100"),
        sub_total=Decimal("100"),
        impuesto=Tax(codigo="01", tarifa=Decimal("13"), monto=Decimal("13")),
    )
    summary = InvoiceSummary(
        moneda="CRC",
        tipo_cambio=None,
        total_serv_gravados=Decimal("100"),
        total_gravado=Decimal("100"),
        total_venta=Decimal("100"),
        total_venta_neta=Decimal("100"),
        total_impuestos=Decimal("13"),
        total_comprobante=Decimal("113"),
    )
    return ElectronicInvoice(
        clave="50612122300310112345600100001010000000001111111111",
        codigo_actividad="62010",
        numero_consecutivo="00100001010000000001",
        fecha_emision=datetime(2023, 8, 1, 12, 0, 0),
        emisor=emisor,
        receptor=receptor,
        condicion_venta=SaleCondition.CONTADO,
        plazo_credito=None,
        medios_pago=[PaymentMethod.EFECTIVO],
        detalle_servicio=[line],
        resumen=summary,
    )


def test_authenticate_stores_token():
    session = DummySession()
    session.next_response = DummyResponse(json_data={"token": "abc123"})
    api = HaciendaAPI(environment="testing", session=session)

    token = api.authenticate("user", "pass")

    assert token == "abc123"
    method, url, payload, _ = session.requests[0]
    assert method == "POST"
    assert url.endswith("/auth")
    assert payload == {"username": "user", "password": "pass"}


def test_authenticate_error():
    session = DummySession()
    session.next_response = DummyResponse(status_code=400, json_data={"error": "invalid"})
    api = HaciendaAPI(environment="testing", session=session)

    with pytest.raises(HaciendaAPIError):
        api.authenticate("user", "pass")


def test_submit_invoice_uses_base64(invoice):
    session = DummySession()
    session.next_response = DummyResponse(json_data={"estado": "aceptado"})
    api = HaciendaAPI(environment="testing", session=session)
    api.set_token("abc")

    api.submit_invoice(invoice)

    method, url, payload, headers = session.requests[0]
    assert method == "POST"
    assert url.endswith("/recepcion")
    assert payload["clave"] == invoice.clave
    assert payload["emisor"]["numeroIdentificacion"] == invoice.emisor.identificacion.numero
    assert "comprobanteXml" in payload
    assert payload["comprobanteXml"].startswith("PD94")  # Base64 del encabezado XML
    assert headers["Authorization"] == "Bearer abc"


def test_fetch_status(invoice):
    session = DummySession()
    session.next_response = DummyResponse(json_data={"estado": "procesando"})
    api = HaciendaAPI(environment="testing", session=session)
    api.set_token("abc")

    response = api.fetch_status(invoice.clave)

    assert response["estado"] == "procesando"
    method, url, _, headers = session.requests[0]
    assert method == "GET"
    assert invoice.clave in url
    assert headers["Authorization"] == "Bearer abc"
