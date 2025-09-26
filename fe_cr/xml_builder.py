"""Generación de XML para comprobantes electrónicos versión 4.4."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
from xml.etree.ElementTree import Element, SubElement, tostring

from .models import (
    ElectronicInvoice,
    InvoiceLine,
    OtherCharge,
    PaymentMethod,
    Tax,
)
from .validation import validate_invoice

_NAMESPACE = "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica"
_SCHEMA_LOCATION = (
    "https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica.xsd"
)


def _decimal_to_text(value: Decimal | float | int, *, places: int = 5) -> str:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    quantized = value.quantize(Decimal((0, (1,), -places)), rounding=ROUND_HALF_UP)
    # El formato "f" evita la notación científica
    return format(quantized.normalize(), "f")


def _text(element: Element, tag: str, value: str) -> Element:
    child = SubElement(element, tag)
    child.text = value
    return child


def _datetime_to_text(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _append_phone(parent: Element, tag: str, phone) -> None:
    node = SubElement(parent, tag)
    _text(node, "CodigoPais", phone.codigo_pais)
    _text(node, "NumTelefono", phone.numero)


def _append_location(parent: Element, location) -> None:
    node = SubElement(parent, "Ubicacion")
    _text(node, "Provincia", location.provincia)
    _text(node, "Canton", location.canton)
    _text(node, "Distrito", location.distrito)
    if location.barrio:
        _text(node, "Barrio", location.barrio)
    if location.otras_senas:
        _text(node, "OtrasSenas", location.otras_senas)


def _append_other_charge(parent: Element, tag: str, cargo: OtherCharge) -> None:
    node = SubElement(parent, tag)
    _text(node, "TipoDocumento", cargo.tipo_documento)
    _text(node, "NumeroDocumento", cargo.numero_documento)
    _text(node, "NombreInstitucion", cargo.nombre_institucion)
    _text(node, "FechaEmision", _datetime_to_text(cargo.fecha_emision))
    _text(node, "MontoCargo", _decimal_to_text(cargo.monto_cargo, places=5))


def _append_tax(parent: Element, tax: Tax) -> None:
    node = SubElement(parent, "Impuesto")
    _text(node, "Codigo", tax.codigo)
    if tax.codigo_tarifa:
        _text(node, "CodigoTarifa", tax.codigo_tarifa)
    _text(node, "Tarifa", _decimal_to_text(tax.tarifa))
    _text(node, "Monto", _decimal_to_text(tax.monto))
    if tax.factor_iva is not None:
        _text(node, "FactorIVA", _decimal_to_text(tax.factor_iva))
    if tax.exoneracion is not None:
        exo = SubElement(node, "Exoneracion")
        _text(exo, "TipoDocumento", tax.exoneracion.tipo_documento)
        _text(exo, "NumeroDocumento", tax.exoneracion.numero_documento)
        _text(exo, "NombreInstitucion", tax.exoneracion.nombre_institucion)
        _text(exo, "FechaEmision", _datetime_to_text(tax.exoneracion.fecha_emision))
        _text(exo, "PorcentajeExoneracion", _decimal_to_text(tax.exoneracion.porcentaje_exoneracion))
        _text(exo, "MontoExoneracion", _decimal_to_text(tax.exoneracion.monto_exoneracion))


def _append_line(parent: Element, line: InvoiceLine) -> None:
    node = SubElement(parent, "LineaDetalle")
    _text(node, "NumeroLinea", str(line.numero_linea))
    if line.codigo:
        codigo = SubElement(node, "Codigo")
        _text(codigo, "Tipo", "01")
        _text(codigo, "Codigo", line.codigo)
    _text(node, "Cantidad", _decimal_to_text(line.cantidad))
    _text(node, "UnidadMedida", line.unidad_medida)
    _text(node, "Detalle", line.detalle)
    _text(node, "PrecioUnitario", _decimal_to_text(line.precio_unitario))
    _text(node, "MontoTotal", _decimal_to_text(line.monto_total))
    if line.descuento is not None:
        descuento = SubElement(node, "Descuento")
        _text(descuento, "MontoDescuento", _decimal_to_text(line.descuento.monto))
        _text(descuento, "NaturalezaDescuento", line.descuento.naturaleza)
    _text(node, "SubTotal", _decimal_to_text(line.sub_total))
    if line.base_imponible is not None:
        _text(node, "BaseImponible", _decimal_to_text(line.base_imponible))
    if line.impuesto is not None:
        _append_tax(node, line.impuesto)
    if line.impuesto_neto is not None:
        _text(node, "ImpuestoNeto", _decimal_to_text(line.impuesto_neto))
    for cargo in line.otros_cargos:
        _append_other_charge(node, "OtroCargo", cargo)

    monto_total_linea = line.sub_total
    if line.impuesto_neto is not None:
        monto_total_linea += line.impuesto_neto
    elif line.impuesto is not None:
        monto_total_linea += line.impuesto.monto
    if line.descuento is not None:
        monto_total_linea -= line.descuento.monto
    for cargo in line.otros_cargos:
        monto_total_linea += cargo.monto_cargo
    _text(node, "MontoTotalLinea", _decimal_to_text(monto_total_linea))


def _append_payment(parent: Element, medios: Iterable[PaymentMethod]) -> None:
    for medio in medios:
        _text(parent, "MedioPago", medio.value)


def invoice_to_xml(invoice: ElectronicInvoice, *, validate: bool = True) -> Element:
    if validate:
        validate_invoice(invoice)

    root = Element(
        "FacturaElectronica",
        attrib={
            "xmlns": _NAMESPACE,
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": f"{_NAMESPACE} {_SCHEMA_LOCATION}",
        },
    )
    _text(root, "Clave", invoice.clave)
    _text(root, "CodigoActividad", invoice.codigo_actividad)
    _text(root, "NumeroConsecutivo", invoice.numero_consecutivo)
    _text(root, "FechaEmision", _datetime_to_text(invoice.fecha_emision))

    emisor = SubElement(root, "Emisor")
    _text(emisor, "Nombre", invoice.emisor.nombre)
    identificacion = SubElement(emisor, "Identificacion")
    _text(identificacion, "Tipo", invoice.emisor.identificacion.tipo)
    _text(identificacion, "Numero", invoice.emisor.identificacion.numero)
    if invoice.emisor.nombre_comercial:
        _text(emisor, "NombreComercial", invoice.emisor.nombre_comercial)
    if invoice.emisor.ubicacion:
        _append_location(emisor, invoice.emisor.ubicacion)
    if invoice.emisor.telefono:
        _append_phone(emisor, "Telefono", invoice.emisor.telefono)
    if invoice.emisor.fax:
        _append_phone(emisor, "Fax", invoice.emisor.fax)
    if invoice.emisor.correo_electronico:
        _text(emisor, "CorreoElectronico", invoice.emisor.correo_electronico)

    if invoice.receptor is not None:
        receptor = SubElement(root, "Receptor")
        _text(receptor, "Nombre", invoice.receptor.nombre)
        if invoice.receptor.identificacion:
            identificacion = SubElement(receptor, "Identificacion")
            _text(identificacion, "Tipo", invoice.receptor.identificacion.tipo)
            _text(identificacion, "Numero", invoice.receptor.identificacion.numero)
        if invoice.receptor.identificacion_extranjero:
            _text(receptor, "IdentificacionExtranjero", invoice.receptor.identificacion_extranjero)
        if invoice.receptor.nombre_comercial:
            _text(receptor, "NombreComercial", invoice.receptor.nombre_comercial)
        if invoice.receptor.ubicacion:
            _append_location(receptor, invoice.receptor.ubicacion)
        if invoice.receptor.telefono:
            _append_phone(receptor, "Telefono", invoice.receptor.telefono)
        if invoice.receptor.fax:
            _append_phone(receptor, "Fax", invoice.receptor.fax)
        if invoice.receptor.correo_electronico:
            _text(receptor, "CorreoElectronico", invoice.receptor.correo_electronico)

    _text(root, "CondicionVenta", invoice.condicion_venta.value)
    if invoice.plazo_credito:
        _text(root, "PlazoCredito", invoice.plazo_credito)

    _append_payment(root, invoice.sorted_medios_pago())

    detalle = SubElement(root, "DetalleServicio")
    for linea in invoice.iter_detalle():
        _append_line(detalle, linea)

    resumen = SubElement(root, "ResumenFactura")
    _text(resumen, "CodigoMoneda", invoice.resumen.moneda)
    if invoice.resumen.tipo_cambio is not None:
        _text(resumen, "TipoCambio", _decimal_to_text(invoice.resumen.tipo_cambio, places=5))
    _text(resumen, "TotalServGravados", _decimal_to_text(invoice.resumen.total_serv_gravados))
    _text(resumen, "TotalServExentos", _decimal_to_text(invoice.resumen.total_serv_exentos))
    _text(resumen, "TotalMercanciasGravadas", _decimal_to_text(invoice.resumen.total_mercancias_gravadas))
    _text(resumen, "TotalMercanciasExentas", _decimal_to_text(invoice.resumen.total_mercancias_exentas))
    _text(resumen, "TotalGravado", _decimal_to_text(invoice.resumen.total_gravado))
    _text(resumen, "TotalExento", _decimal_to_text(invoice.resumen.total_exento))
    _text(resumen, "TotalExonerado", _decimal_to_text(invoice.resumen.total_exonerado))
    _text(resumen, "TotalVenta", _decimal_to_text(invoice.resumen.total_venta))
    _text(resumen, "TotalDescuentos", _decimal_to_text(invoice.resumen.total_descuentos))
    _text(resumen, "TotalVentaNeta", _decimal_to_text(invoice.resumen.total_venta_neta))
    _text(resumen, "TotalImpuesto", _decimal_to_text(invoice.resumen.total_impuestos))
    _text(resumen, "TotalOtrosCargos", _decimal_to_text(invoice.resumen.total_otros_cargos))
    _text(resumen, "TotalComprobante", _decimal_to_text(invoice.resumen.total_comprobante))

    if invoice.otros_cargos:
        otros_cargos = SubElement(root, "OtrosCargos")
        for cargo in invoice.otros_cargos:
            _append_other_charge(otros_cargos, "OtroCargo", cargo)

    if invoice.informacion_referencia:
        info = SubElement(root, "InformacionReferencia")
        for ref in invoice.informacion_referencia:
            ref_node = SubElement(info, "Referencia")
            _text(ref_node, "TipoDocumento", ref.tipo_documento)
            _text(ref_node, "Numero", ref.numero_documento)
            _text(ref_node, "FechaEmision", _datetime_to_text(ref.fecha_emision))
            _text(ref_node, "Codigo", ref.codigo)
            _text(ref_node, "Razon", ref.razon)

    return root


def render_invoice(invoice: ElectronicInvoice, *, validate: bool = True, encoding: str = "utf-8", xml_declaration: bool = True) -> str:
    element = invoice_to_xml(invoice, validate=validate)
    xml_bytes = tostring(element, encoding=encoding, xml_declaration=xml_declaration)
    return xml_bytes.decode(encoding)
