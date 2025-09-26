from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cr_identification_type = fields.Selection(
        selection=[
            ("01", "Cédula Física"),
            ("02", "Cédula Jurídica"),
            ("03", "DIMEX"),
            ("04", "NITE"),
        ],
        string="Tipo identificación Hacienda",
    )
    cr_identification_number = fields.Char(string="Número identificación Hacienda")
    cr_commercial_name = fields.Char(string="Nombre comercial Hacienda")
    cr_activity_code = fields.Char(string="Actividad económica Hacienda")
    cr_phone_country_code = fields.Char(string="Código país teléfono", default="506")
    cr_phone_number = fields.Char(string="Teléfono Hacienda")
    cr_email = fields.Char(string="Correo electrónico Hacienda")
    cr_province = fields.Char(string="Provincia")
    cr_canton = fields.Char(string="Cantón")
    cr_district = fields.Char(string="Distrito")
    cr_neighborhood = fields.Char(string="Barrio")
    cr_address = fields.Char(string="Otras señas")
    cr_environment = fields.Selection(
        selection=[("sandbox", "Pruebas"), ("production", "Producción")],
        string="Ambiente Hacienda",
        default="sandbox",
    )
