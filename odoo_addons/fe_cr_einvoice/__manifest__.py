# -*- coding: utf-8 -*-
{
    "name": "Costa Rica Electronic Invoicing",
    "summary": "Extiende la facturación de Odoo 19 para cumplir con Hacienda Costa Rica",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "author": "OpenAI Assistant",
    "website": "https://github.com/example/fe_cr",
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "views/electronic_document_views.xml",
        "views/menu_views.xml",
        "views/account_move_views.xml",
        "views/res_company_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": False,
}
