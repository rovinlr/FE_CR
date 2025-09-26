from odoo import fields, models


class UomUom(models.Model):
    _inherit = "uom.uom"

    l10n_cr_code = fields.Char(
        string="Código unidad CR",
        help="Código de unidad de medida según el catálogo oficial de Hacienda.",
    )
