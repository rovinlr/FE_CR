# FE_CR

Módulo en Python para generar comprobantes electrónicos costarricenses (versión 4.4) a partir de estructuras de datos tipadas.

## Características

- Modelos de datos que siguen los encabezados, cuerpo y anexos de la **Factura Electrónica** establecidos por Tributación.
- Validaciones básicas para los campos más relevantes (clave de 50 dígitos, consecutivo de 20 dígitos, identificación, totales).
- Generación de XML listo para firmar y enviar a la ATV utilizando el esquema oficial `v4.4`.
- Cliente ligero para autenticarse y comunicarse con la API de recepción (`/recepcion/v1`).

- Módulo complementario para Odoo 19 (`l10n_cr_edi`) con vistas, campos adicionales y permisos para gestionar comprobantes electrónicos.


## Instalación

El proyecto está organizado como un paquete estándar de Python. Para usarlo de forma local ejecute:

```bash
pip install -e .
```

## Uso

```python
from datetime import datetime
from decimal import Decimal

from fe_cr import (
    Discount,
    ElectronicInvoice,
    Emisor,
    Identification,
    InvoiceLine,
    InvoiceSummary,
    Location,
    PaymentMethod,
    Phone,
    Receptor,
    SaleCondition,
    Tax,
)
from fe_cr.xml_builder import render_invoice

emisor = Emisor(
    nombre="Mi Empresa S.A.",
    identificacion=Identification(tipo="02", numero="3101123456"),
    nombre_comercial="Mi Empresa",
)

receptor = Receptor(
    nombre="Cliente de Ejemplo",
    identificacion=Identification(tipo="01", numero="101230123"),
    correo_electronico="cliente@correo.com",
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

invoice = ElectronicInvoice(
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

xml = render_invoice(invoice)
print(xml)
```


### Uso desde Odoo 19

1. Instale el paquete Python ejecutando `pip install -e .` (o añada el directorio `fe_cr` al `PYTHONPATH` del entorno de Odoo).
2. Añada la carpeta `l10n_cr_edi` a alguna de las rutas definidas en el `addons_path` de su instancia (puede copiarla o declarar la ruta del repositorio completo `FE_CR`).
3. Active el modo desarrollador, actualice la lista de aplicaciones y quite el filtro "Aplicaciones" para que se muestren los módulos técnicos.
4. Instale **Costa Rica Electronic Invoicing** y configure los datos de Hacienda en *Ajustes → Facturación → Costa Rica*.
5. Abra una factura de cliente para acceder a la pestaña **Factura electrónica CR**, completar los campos requeridos y generar el XML mediante el botón **Generar XML Hacienda**.

### Envío a la API de Hacienda

```python
from fe_cr import HaciendaAPI

api = HaciendaAPI(environment="testing")
token = api.authenticate("cpf-username", "cpf-password")
response = api.submit_invoice(invoice)
status = api.fetch_status(invoice.clave)
```

> **Nota:** La API espera el comprobante en formato Base64 y devuelve un `token` JWT. El `HaciendaAPI` incluido maneja ambos requisitos y expone las respuestas JSON devueltas por Hacienda para facilitar la integración con sistemas externos.


## Pruebas

Las pruebas unitarias se ejecutan con `pytest`:

```bash
pytest
```

## Limitaciones

- El módulo no firma digitalmente el XML.
- No calcula automáticamente los totales; estos deben proporcionarse ya calculados conforme a la normativa.
- El catálogo de códigos (impuestos, actividades, unidades de medida, etc.) debe mantenerse actualizado manualmente según la resolución vigente.
