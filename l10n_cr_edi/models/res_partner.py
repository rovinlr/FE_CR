from odoo import fields, models


class ResPartner(models.Model):
    """Campos adicionales requeridos por Hacienda para los receptores."""

    _inherit = "res.partner"

    l10n_cr_identification_type = fields.Selection(
        selection=[
            ("01", "Cédula Física"),
            ("02", "Cédula Jurídica"),
            ("03", "DIMEX"),
            ("04", "NITE"),
            ("05", "Documento Extranjero"),
        ],
        string="Tipo identificación CR",
        help="Tipo de identificación del receptor según el catálogo 4.4 de Hacienda.",
        default="01",
    )
    l10n_cr_identification_number = fields.Char(
        string="Número identificación CR",
        help="Número de identificación del receptor utilizado en los comprobantes electrónicos.",
    )
    l10n_cr_phone_country_code = fields.Char(
        string="Código país teléfono CR",
        default="506",
    )
    l10n_cr_phone_number = fields.Char(string="Teléfono CR")
    l10n_cr_province = fields.Char(string="Provincia CR")
    l10n_cr_canton = fields.Char(string="Cantón CR")
    l10n_cr_district = fields.Char(string="Distrito CR")
    l10n_cr_neighborhood = fields.Char(string="Barrio CR")
    l10n_cr_address = fields.Char(string="Otras señas CR")
