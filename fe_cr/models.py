"""Modelos de datos para la Factura Electrónica de Costa Rica (versión 4.4)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Iterable, List, Optional, Sequence


class SaleCondition(str, Enum):
    """Catálogo de condiciones de venta de acuerdo con Anexo 3."""

    CONTADO = "01"
    CREDITO = "02"
    CONSIGNACION = "03"
    APARTADO = "04"
    ARRENDAMIENTO = "05"
    OTRO = "99"


class PaymentMethod(str, Enum):
    """Catálogo de medios de pago de acuerdo con Anexo 3."""

    EFECTIVO = "01"
    TARJETA = "02"
    CHEQUE = "03"
    TRANSFERENCIA_DEPOSITO = "04"
    RECAUDADO_POR_TERCEROS = "05"
    SINPE = "06"
    OTROS = "99"


@dataclass(slots=True)
class Phone:
    codigo_pais: str
    numero: str


@dataclass(slots=True)
class Fax(Phone):
    pass


@dataclass(slots=True)
class Email:
    direccion: str


@dataclass(slots=True)
class Identification:
    tipo: str
    numero: str


@dataclass(slots=True)
class Location:
    provincia: str
    canton: str
    distrito: str
    barrio: Optional[str] = None
    otras_senas: Optional[str] = None


@dataclass(slots=True)
class Emisor:
    nombre: str
    identificacion: Identification
    nombre_comercial: Optional[str] = None
    ubicacion: Optional[Location] = None
    telefono: Optional[Phone] = None
    fax: Optional[Fax] = None
    correo_electronico: Optional[str] = None


@dataclass(slots=True)
class Receptor:
    nombre: str
    identificacion: Optional[Identification] = None
    identificacion_extranjero: Optional[str] = None
    nombre_comercial: Optional[str] = None
    ubicacion: Optional[Location] = None
    telefono: Optional[Phone] = None
    fax: Optional[Fax] = None
    correo_electronico: Optional[str] = None


@dataclass(slots=True)
class TaxExoneration:
    tipo_documento: str
    numero_documento: str
    nombre_institucion: str
    fecha_emision: datetime
    porcentaje_exoneracion: Decimal
    monto_exoneracion: Decimal


@dataclass(slots=True)
class Tax:
    codigo: str
    tarifa: Decimal
    monto: Decimal
    codigo_tarifa: Optional[str] = None
    factor_iva: Optional[Decimal] = None
    exoneracion: Optional[TaxExoneration] = None


@dataclass(slots=True)
class OtherCharge:
    tipo_documento: str
    numero_documento: str
    nombre_institucion: str
    fecha_emision: datetime
    monto_cargo: Decimal


@dataclass(slots=True)
class Discount:
    monto: Decimal
    naturaleza: str


@dataclass(slots=True)
class InvoiceLine:
    numero_linea: int
    codigo: Optional[str]
    cantidad: Decimal
    unidad_medida: str
    detalle: str
    precio_unitario: Decimal
    monto_total: Decimal
    sub_total: Decimal
    base_imponible: Optional[Decimal] = None
    impuesto: Optional[Tax] = None
    impuesto_neto: Optional[Decimal] = None
    descuento: Optional[Discount] = None
    otros_cargos: Sequence[OtherCharge] = field(default_factory=tuple)


@dataclass(slots=True)
class InvoiceSummary:
    """Totales del comprobante según el esquema ``v4.4``."""

    moneda: str
    tipo_cambio: Optional[Decimal]
    total_serv_gravados: Decimal = Decimal("0")
    total_serv_exentos: Decimal = Decimal("0")
    total_serv_exonerado: Decimal = Decimal("0")
    total_serv_no_sujeto: Decimal = Decimal("0")
    total_serv_otros: Decimal = Decimal("0")
    total_mercancias_gravadas: Decimal = Decimal("0")
    total_mercancias_exentas: Decimal = Decimal("0")
    total_mercancias_exoneradas: Decimal = Decimal("0")
    total_mercancias_no_sujeto: Decimal = Decimal("0")
    total_mercancias_otros: Decimal = Decimal("0")
    total_gravado: Decimal = Decimal("0")
    total_exento: Decimal = Decimal("0")
    total_exonerado: Decimal = Decimal("0")
    total_no_sujeto: Decimal = Decimal("0")
    total_otros: Decimal = Decimal("0")
    total_venta: Decimal = Decimal("0")
    total_descuentos: Decimal = Decimal("0")
    total_venta_neta: Decimal = Decimal("0")
    total_impuestos: Decimal = Decimal("0")
    total_iva_devuelto: Decimal = Decimal("0")
    total_otros_cargos: Decimal = Decimal("0")
    total_comprobante: Decimal = Decimal("0")


@dataclass(slots=True)
class ReferenceInformation:
    tipo_documento: str
    numero_documento: str
    fecha_emision: datetime
    codigo: str
    razon: str


@dataclass(slots=True)
class ElectronicInvoice:
    clave: str
    codigo_actividad: str
    numero_consecutivo: str
    fecha_emision: datetime
    emisor: Emisor
    receptor: Optional[Receptor]
    condicion_venta: SaleCondition
    plazo_credito: Optional[str]
    medios_pago: Sequence[PaymentMethod]
    detalle_servicio: Sequence[InvoiceLine]
    resumen: InvoiceSummary
    informacion_referencia: Sequence[ReferenceInformation] = field(default_factory=tuple)
    otros_cargos: Sequence[OtherCharge] = field(default_factory=tuple)

    def sorted_medios_pago(self) -> List[PaymentMethod]:
        return sorted(set(self.medios_pago), key=lambda m: m.value)

    def iter_detalle(self) -> Iterable[InvoiceLine]:
        yield from self.detalle_servicio
