from odoo import api, fields, models, _


class ElectronicDocument(models.Model):
    """Registra los documentos electrónicos generados para Hacienda."""

    _name = "fe.cr.document"
    _description = "Documento electrónico de Costa Rica"
    _order = "create_date desc"

    name = fields.Char(string="Nombre", required=True, default=lambda self: _("Comprobante"))
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura",
        required=True,
        ondelete="cascade",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("generated", "Generado"),
            ("sent", "Enviado"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
            ("error", "Error"),
        ],
        default="draft",
        string="Estado",
        tracking=True,
    )
    xml_comprobante = fields.Binary(string="XML Comprobante")
    xml_respuesta = fields.Binary(string="XML Respuesta")
    xml_filename = fields.Char(string="Nombre del XML")
    message = fields.Text(string="Mensaje de Hacienda")
    sent_date = fields.Datetime(string="Fecha de envío")
    response_date = fields.Datetime(string="Fecha de respuesta")

    @api.model
    def create_from_invoice(self, move, xml_content, filename):
        document = self.create(
            {
                "name": filename,
                "move_id": move.id,
                "state": "generated",
                "xml_comprobante": xml_content,
                "xml_filename": filename,
            }
        )
        move.cr_document_ids = [(4, document.id)]
        return document
