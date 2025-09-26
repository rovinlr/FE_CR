from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_cr_tax_code = fields.Char(
        string="Código impuesto CR",
        help="Código del impuesto según el catálogo de Hacienda (Anexo 4.4).",
    )
    l10n_cr_summary_group = fields.Selection(
        selection=[
            ("gravado", "Gravado"),
            ("exento", "Exento"),
            ("exonerado", "Exonerado"),
            ("no_sujeto", "No sujeto"),
            ("otros", "Otros"),
        ],
        string="Resumen Hacienda",
        help=(
            "Clasificación del impuesto utilizada para agrupar los totales del "
            "resumen de factura electrónica (Anexo 4.4)."
        ),
    )
