from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AnalyticsSalesLocal(models.Model):
    _name = 'analytics.sales.local'
    _description = 'Local comercial Analytics Sales (nlocal ERP)'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(string='nlocal (ERP)', required=True, index=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, index=True, ondelete='cascade')
    active = fields.Boolean(default=True)

    _sql_constraints = [('analytics_sales_local_unique', 'unique(company_id, name)', 'El nlocal ya existe para esta compañía.')]

    @api.constrains('company_id')
    def _check_establishment_company(self):
        for local in self:
            memberships = self.env['analytics.sales.establishment'].sudo().search([
                ('local_ids', 'in', local.id),
            ])
            if any(group.company_id != local.company_id for group in memberships):
                raise ValidationError(_('El local pertenece a un establecimiento de otra compañía.'))

    @api.model
    def name_create(self, name):
        # Only admin users with model ACL can create locales using the UI.
        return super().name_create(name)
