from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cr_identification_type = fields.Selection(
        related="company_id.cr_identification_type",
        readonly=False,
    )
    cr_identification_number = fields.Char(
        related="company_id.cr_identification_number",
        readonly=False,
    )
    cr_commercial_name = fields.Char(
        related="company_id.cr_commercial_name",
        readonly=False,
    )
    cr_activity_code = fields.Char(
        related="company_id.cr_activity_code",
        readonly=False,
    )
    cr_phone_country_code = fields.Char(
        related="company_id.cr_phone_country_code",
        readonly=False,
    )
    cr_phone_number = fields.Char(
        related="company_id.cr_phone_number",
        readonly=False,
    )
    cr_email = fields.Char(
        related="company_id.cr_email",
        readonly=False,
    )
    cr_province = fields.Char(
        related="company_id.cr_province",
        readonly=False,
    )
    cr_canton = fields.Char(
        related="company_id.cr_canton",
        readonly=False,
    )
    cr_district = fields.Char(
        related="company_id.cr_district",
        readonly=False,
    )
    cr_neighborhood = fields.Char(
        related="company_id.cr_neighborhood",
        readonly=False,
    )
    cr_address = fields.Char(
        related="company_id.cr_address",
        readonly=False,
    )
    cr_environment = fields.Selection(
        related="company_id.cr_environment",
        readonly=False,
    )
