from datetime import datetime
from decimal import Decimal
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fe_cr import (
    ElectronicInvoice,
    Emisor,
    Identification,
    InvoiceLine,
    InvoiceSummary,
    PaymentMethod,
    Receptor,
    SaleCondition,
    Tax,
)
from fe_cr.xml_builder import render_invoice

NS = "{https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica}"


def _sample_invoice() -> ElectronicInvoice:
    emisor = Emisor(
        nombre="Mi Empresa S.A.",
        identificacion=Identification(tipo="02", numero="3101123456"),
    )
    receptor = Receptor(
        nombre="Cliente de Ejemplo",
        identificacion=Identification(tipo="01", numero="101230123"),
    )
    linea = InvoiceLine(
        numero_linea=1,
        codigo="ABC-123",
        cantidad=Decimal("1"),
        unidad_medida="Unid",
        detalle="Servicio profesional",
        precio_unitario=Decimal("100.00"),
        monto_total=Decimal("100.00"),
        sub_total=Decimal("100.00"),
        impuesto=Tax(codigo="01", tarifa=Decimal("13"), monto=Decimal("13")),
    )
    resumen = InvoiceSummary(
        moneda="CRC",
        tipo_cambio=None,
        total_serv_gravados=Decimal("100.00"),
        total_gravado=Decimal("100.00"),
        total_venta=Decimal("100.00"),
        total_venta_neta=Decimal("100.00"),
        total_impuestos=Decimal("13.00"),
        total_comprobante=Decimal("113.00"),
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
        detalle_servicio=[linea],
        resumen=resumen,
    )


def test_render_invoice_generates_valid_xml():
    invoice = _sample_invoice()
    xml = render_invoice(invoice)
    root = ET.fromstring(xml)

    assert root.tag == f"{NS}FacturaElectronica"
    assert root.findtext(f"{NS}Clave") == invoice.clave
    assert root.find(f"{NS}Emisor/{NS}Identificacion/{NS}Numero").text == invoice.emisor.identificacion.numero
    assert root.find(f"{NS}Receptor/{NS}Identificacion/{NS}Numero").text == invoice.receptor.identificacion.numero
    assert root.find(f"{NS}DetalleServicio/{NS}LineaDetalle/{NS}Impuesto/{NS}Monto").text == "13"
    assert root.find(f"{NS}ResumenFactura/{NS}TotalComprobante").text == "113"


def test_render_invoice_without_validation():
    invoice = _sample_invoice()
    xml = render_invoice(invoice, validate=False)
    assert "FacturaElectronica" in xml
