"""Validaciones basadas en los anexos de la versión 4.4."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from .exceptions import ValidationError
from .models import ElectronicInvoice, Identification, InvoiceLine, PaymentMethod, SaleCondition

_CLAVE_RE = re.compile(r"^[0-9]{50}$")
_CONSECUTIVO_RE = re.compile(r"^[0-9]{20}$")
_IDENTIFICACION_RE = re.compile(r"^[0-9A-Za-z]{9,20}$")


def _ensure(predicate: bool, message: str, *, field: str | None = None) -> None:
    if not predicate:
        raise ValidationError(message, field=field)


def validate_identification(identificacion: Identification, *, field: str) -> None:
    _ensure(identificacion.tipo in {"01", "02", "03", "04"}, "Tipo de identificación inválido", field=field)
    _ensure(
        bool(_IDENTIFICACION_RE.fullmatch(identificacion.numero)),
        "Número de identificación inválido",
        field=field,
    )


def validate_medios_pago(medios_pago: Sequence[PaymentMethod]) -> None:
    _ensure(len(medios_pago) > 0, "Debe indicar al menos un medio de pago", field="MedioPago")


def validate_invoice_line(linea: InvoiceLine) -> None:
    _ensure(linea.numero_linea > 0, "El número de línea debe ser positivo", field="NumeroLinea")
    _ensure(linea.cantidad >= 0, "La cantidad debe ser mayor o igual a cero", field="Cantidad")
    _ensure(linea.precio_unitario >= 0, "El precio unitario debe ser mayor o igual a cero", field="PrecioUnitario")
    _ensure(linea.monto_total >= 0, "El monto total debe ser mayor o igual a cero", field="MontoTotal")
    _ensure(linea.sub_total >= 0, "El subtotal debe ser mayor o igual a cero", field="SubTotal")
    if linea.base_imponible is not None:
        _ensure(linea.base_imponible >= 0, "La base imponible debe ser mayor o igual a cero", field="BaseImponible")
    if linea.impuesto is not None:
        _ensure(linea.impuesto.monto >= 0, "Monto de impuesto inválido", field="Impuesto/Monto")
        _ensure(Decimal("0") <= linea.impuesto.tarifa <= Decimal("100"), "Tarifa de impuesto inválida", field="Impuesto/Tarifa")


def validate_invoice(invoice: ElectronicInvoice) -> None:
    _ensure(bool(_CLAVE_RE.fullmatch(invoice.clave)), "La clave debe tener 50 dígitos", field="Clave")
    _ensure(bool(_CONSECUTIVO_RE.fullmatch(invoice.numero_consecutivo)), "El consecutivo debe tener 20 dígitos", field="NumeroConsecutivo")
    _ensure(isinstance(invoice.fecha_emision, datetime), "Fecha de emisión inválida", field="FechaEmision")
    validate_identification(invoice.emisor.identificacion, field="Emisor/Identificacion")

    if invoice.receptor and invoice.receptor.identificacion:
        validate_identification(invoice.receptor.identificacion, field="Receptor/Identificacion")

    _ensure(isinstance(invoice.condicion_venta, SaleCondition), "Condición de venta inválida", field="CondicionVenta")
    medios_pago_tuple = tuple(invoice.medios_pago)
    validate_medios_pago(medios_pago_tuple)

    numeros_linea: set[int] = set()
    for linea in invoice.iter_detalle():
        validate_invoice_line(linea)
        _ensure(linea.numero_linea not in numeros_linea, "Numero de línea duplicado", field="NumeroLinea")
        numeros_linea.add(linea.numero_linea)

    resumen = invoice.resumen
    _ensure(resumen.total_comprobante >= 0, "Total del comprobante inválido", field="ResumenFactura/TotalComprobante")
    if resumen.tipo_cambio is not None:
        _ensure(resumen.tipo_cambio > 0, "Tipo de cambio debe ser mayor a cero", field="ResumenFactura/TipoCambio")
