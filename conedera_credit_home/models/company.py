from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    conedera_home_apply_url = fields.Char(string='URL de solicitud de crédito')
    conedera_home_history_url = fields.Char(string='URL del historial de solicitudes')
    conedera_home_documents_url = fields.Char(string='URL de entrega de documentos')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    conedera_home_apply_url = fields.Char(
        related='company_id.conedera_home_apply_url', readonly=False,
    )
    conedera_home_history_url = fields.Char(
        related='company_id.conedera_home_history_url', readonly=False,
    )
    conedera_home_documents_url = fields.Char(
        related='company_id.conedera_home_documents_url', readonly=False,
    )
