from __future__ import annotations

import base64
import json
from decimal import Decimal

from odoo import _, fields, models
from odoo.exceptions import UserError

from fe_cr import (
    Discount,
    ElectronicInvoice,
    Emisor,
    HaciendaAPI,
    HaciendaAPIError,
    Identification,
    InvoiceLine,
    InvoiceSummary,
    Location,
    PaymentMethod,
    Phone,
    Receptor,
    SaleCondition,
    Tax,
    ValidationError,
    sign_xml_with_p12,
    validate_invoice,
)
from fe_cr.xml_builder import render_invoice


class AccountMove(models.Model):
    _inherit = "account.move"

    cr_invoice_key = fields.Char(string="Clave Hacienda", size=50)
    cr_consecutive_number = fields.Char(string="Número consecutivo", size=20)
    cr_activity_code = fields.Char(string="Código de actividad", size=6)
    cr_sale_condition = fields.Selection(
        selection=[
            (SaleCondition.CONTADO.value, "Contado"),
            (SaleCondition.CREDITO.value, "Crédito"),
            (SaleCondition.CONSIGNACION.value, "Consignación"),
            (SaleCondition.APARTADO.value, "Apartado"),
            (SaleCondition.ARRENDAMIENTO.value, "Arrendamiento"),
            (SaleCondition.OTRO.value, "Otro"),
        ],
        string="Condición de venta",
        default=SaleCondition.CONTADO.value,
    )
    cr_credit_days = fields.Integer(string="Plazo de crédito (días)")
    cr_payment_methods = fields.Char(
        string="Medios de pago",
        help="Lista de códigos separados por coma según el catálogo de Hacienda",
    )
    cr_electronic_state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("generated", "XML Generado"),
            ("sent", "Enviado"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
            ("error", "Error"),
        ],
        default="draft",
        string="Estado electrónico",
    )
    cr_document_ids = fields.One2many(
        comodel_name="fe.cr.document",
        inverse_name="move_id",
        string="Documentos electrónicos",
        readonly=True,
    )

    def action_generate_cr_xml(self):
        for move in self:
            move._ensure_cr_configuration()
            invoice = move._prepare_cr_invoice_payload()
            try:
                validate_invoice(invoice)
            except ValidationError as exc:
                raise UserError(_("La factura no cumple con los anexos 4.4: %s") % exc) from exc

            xml_bytes = render_invoice(invoice).encode("utf-8")
            filename = f"{move.name or 'factura'}_{move.id}.xml"
            document = move._ensure_cr_document(xml_bytes, filename)
            document.state = "generated"
            document.message = False
            move.cr_electronic_state = "generated"
        return True

    def action_send_cr_xml(self):
        for move in self:
            move._ensure_cr_configuration()
            company = move.company_id
            move._ensure_cr_credentials()

            invoice = move._prepare_cr_invoice_payload()
            try:
                validate_invoice(invoice)
            except ValidationError as exc:
                raise UserError(_("La factura no cumple con los anexos 4.4: %s") % exc) from exc

            unsigned_xml = render_invoice(invoice).encode("utf-8")
            filename = f"{move.name or 'factura'}_{move.id}.xml"
            document = move._ensure_cr_document(unsigned_xml, filename)

            try:
                signed_xml = move._sign_cr_xml(unsigned_xml)
            except Exception as exc:
                document.write(
                    {
                        "state": "error",
                        "message": str(exc),
                    }
                )
                move.cr_electronic_state = "error"
                raise UserError(_("No se pudo firmar el XML: %s") % exc) from exc

            api = HaciendaAPI(environment=company.cr_environment or "sandbox")
            try:
                api.authenticate(company.cr_hacienda_username, company.cr_hacienda_password)
                response = api.submit_invoice(invoice, xml=signed_xml)
            except HaciendaAPIError as exc:
                payload = exc.payload or {}
                message = json.dumps(payload, ensure_ascii=False, indent=2) if isinstance(payload, dict) else str(exc)
                document.write(
                    {
                        "state": "error",
                        "message": message,
                        "xml_comprobante": base64.b64encode(signed_xml),
                    }
                )
                move.cr_electronic_state = "error"
                raise UserError(_("Hacienda rechazó el comprobante: %s") % exc) from exc
            except Exception as exc:
                document.write(
                    {
                        "state": "error",
                        "message": str(exc),
                        "xml_comprobante": base64.b64encode(signed_xml),
                    }
                )
                move.cr_electronic_state = "error"
                raise UserError(_("Ocurrió un error al enviar a Hacienda: %s") % exc) from exc

            document.write(
                {
                    "state": "sent",
                    "xml_comprobante": base64.b64encode(signed_xml),
                    "sent_date": fields.Datetime.now(),
                    "message": json.dumps(response, ensure_ascii=False, indent=2),
                }
            )
            move.cr_electronic_state = "sent"
        return True

    def _ensure_cr_configuration(self):
        for move in self:
            company = move.company_id
            missing = []
            required_fields = {
                "cr_identification_type": _("Tipo de identificación"),
                "cr_identification_number": _("Número de identificación"),
                "cr_province": _("Provincia"),
                "cr_canton": _("Cantón"),
                "cr_district": _("Distrito"),
                "cr_address": _("Dirección"),
            }
            for field_name, label in required_fields.items():
                if not company[field_name]:
                    missing.append(label)
            if missing:
                raise UserError(
                    _(
                        "La compañía %s no tiene configurados los siguientes datos necesarios para Hacienda: %s"
                    )
                    % (company.name, ", ".join(missing))
                )
            if not move.partner_id:
                raise UserError(_("La factura debe tener un cliente asignado."))
        return True

    def _prepare_cr_invoice_payload(self) -> ElectronicInvoice:
        self.ensure_one()
        company = self.company_id
        partner = self.partner_id

        emisor = Emisor(
            nombre=company.name,
            identificacion=Identification(
                tipo=company.cr_identification_type,
                numero=company.cr_identification_number,
            ),
            nombre_comercial=company.cr_commercial_name or company.name,
            ubicacion=Location(
                provincia=company.cr_province,
                canton=company.cr_canton,
                distrito=company.cr_district,
                barrio=company.cr_neighborhood or None,
                otras_senas=company.cr_address,
            ),
            telefono=Phone(
                codigo_pais=company.cr_phone_country_code or "506",
                numero=company.cr_phone_number or "",
            )
            if company.cr_phone_number
            else None,
            correo_electronico=company.email or company.cr_email,
        )

        receptor = Receptor(
            nombre=partner.name,
            identificacion=Identification(
                tipo=(partner.l10n_cr_identification_type or "01"),
                numero=(partner.vat or partner.ref or "000000000"),
            )
            if (partner.vat or partner.ref)
            else None,
            nombre_comercial=partner.commercial_partner_id.name,
            correo_electronico=partner.email,
        )

        detalle = []
        for index, line in enumerate(
            self.invoice_line_ids.filtered(lambda l: l.display_type not in ("line_section", "line_note")),
            start=1,
        ):
            tax = None
            tax_amount = Decimal("0.00")
            if line.tax_ids:
                tax_record = line.tax_ids[0]
                tax_code = getattr(tax_record, "l10n_cr_tax_code", None) or "01"
                tax = Tax(
                    codigo=tax_code,
                    tarifa=Decimal(str(tax_record.amount)),
                    monto=Decimal(str(line.price_total - line.price_subtotal)),
                )
                tax_amount = tax.monto
            discount = None
            if line.discount:
                line_total = Decimal(str(line.price_unit)) * Decimal(str(line.quantity))
                discount_amount = line_total * Decimal(str(line.discount / 100.0))
                discount = Discount(
                    monto=Decimal(str(discount_amount)),
                    naturaleza=_("Descuento de línea"),
                )
            detalle.append(
                InvoiceLine(
                    numero_linea=index,
                    codigo=line.product_id.default_code,
                    cantidad=Decimal(str(line.quantity or 0)),
                    unidad_medida=line.product_uom_id.l10n_cr_code or line.product_uom_id.name or "Unid",
                    detalle=line.name,
                    precio_unitario=Decimal(str(line.price_unit)),
                    monto_total=Decimal(str(line.price_unit)) * Decimal(str(line.quantity)),
                    sub_total=Decimal(str(line.price_subtotal)),
                    impuesto=tax,
                    impuesto_neto=tax_amount,
                    descuento=discount,
                )
            )

        conversion_rate = None
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            rate = self.currency_id._get_conversion_rate(
                self.currency_id,
                self.company_id.currency_id,
                self.company_id,
                self.invoice_date or fields.Date.context_today(self),
            )
            conversion_rate = Decimal(str(rate))

        resumen = InvoiceSummary(
            moneda=self.currency_id.name,
            tipo_cambio=conversion_rate,
            total_serv_gravados=sum(
                Decimal(str(line.price_subtotal))
                for line in self.invoice_line_ids
                if line.tax_ids
            ),
            total_gravado=Decimal(str(self.amount_untaxed)),
            total_venta=Decimal(str(self.amount_untaxed)),
            total_venta_neta=Decimal(str(self.amount_untaxed)),
            total_impuestos=Decimal(str(self.amount_tax)),
            total_comprobante=Decimal(str(self.amount_total)),
        )

        clave = self.cr_invoice_key or self._generate_cr_key()
        consecutivo = self.cr_consecutive_number or self._generate_cr_consecutive()

        try:
            sale_condition = SaleCondition(self.cr_sale_condition or SaleCondition.CONTADO.value)
        except ValueError:
            sale_condition = SaleCondition.CONTADO

        invoice = ElectronicInvoice(
            clave=clave,
            codigo_actividad=self.cr_activity_code or company.cr_activity_code,
            numero_consecutivo=consecutivo,
            fecha_emision=self.invoice_date or fields.Date.context_today(self),
            emisor=emisor,
            receptor=receptor,
            condicion_venta=sale_condition,
            plazo_credito=self.cr_credit_days or None,
            medios_pago=self._parse_payment_methods(),
            detalle_servicio=detalle,
            resumen=resumen,
        )
        self.cr_invoice_key = clave
        self.cr_consecutive_number = consecutivo
        return invoice

    def _ensure_cr_document(self, xml_bytes, filename):
        self.ensure_one()
        documents = self.cr_document_ids.filtered(lambda d: d.state in {"draft", "generated", "error"})
        document = documents.sorted(key=lambda d: d.create_date or fields.Datetime.now(), reverse=True)[:1]
        if document:
            document.write(
                {
                    "xml_comprobante": base64.b64encode(xml_bytes),
                    "xml_filename": filename,
                }
            )
            return document
        return self.env["fe.cr.document"].create_from_invoice(
            self,
            xml_bytes,
            filename,
        )

    def _ensure_cr_credentials(self):
        for move in self:
            company = move.company_id
            missing = []
            if not company.cr_hacienda_username:
                missing.append(_("Usuario Hacienda"))
            if not company.cr_hacienda_password:
                missing.append(_("Contraseña Hacienda"))
            if not company.cr_certificate_p12:
                missing.append(_("Certificado P12 Hacienda"))
            if not company.cr_certificate_password:
                missing.append(_("Contraseña certificado"))
            if missing:
                raise UserError(
                    _(
                        "La compañía %s no tiene configurados los credenciales requeridos: %s"
                    )
                    % (company.name, ", ".join(missing))
                )
        return True

    def _sign_cr_xml(self, xml_bytes: bytes) -> bytes:
        self.ensure_one()
        company = self.company_id
        try:
            certificate_bytes = base64.b64decode(company.cr_certificate_p12)
        except Exception as exc:  # pragma: no cover - casos extremos
            raise UserError(_("El certificado P12 es inválido")) from exc
        password = company.cr_certificate_password or ""
        return sign_xml_with_p12(xml_bytes, certificate_bytes, password)

    def _parse_payment_methods(self):
        codes = (self.cr_payment_methods or "01").split(",")
        methods = []
        for code in codes:
            code = code.strip()
            try:
                methods.append(PaymentMethod(code or "01"))
            except ValueError:
                continue
        return methods or [PaymentMethod.EFECTIVO]

    def _generate_cr_key(self) -> str:
        date = fields.Date.to_date(self.invoice_date or fields.Date.context_today(self))
        date_str = date.strftime("%d%m%y")
        identifier = (self.company_id.cr_identification_number or "000000000").zfill(12)
        consecutive = (self.cr_consecutive_number or str(self.id)).zfill(20)
        security_code = f"{self.id:08d}"[-8:]
        situation = "1"
        return f"506{date_str}{identifier}{consecutive}{security_code}{situation}"

    def _generate_cr_consecutive(self) -> str:
        journal_code = (self.journal_id.code or "001")[:3].rjust(3, "0")
        terminal = "00001"
        sequence = str(self.id or 0).zfill(10)
        return f"{journal_code}{terminal}{sequence}"
