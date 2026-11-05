from odoo import models, fields

class ResUsersEmpresaRel(models.Model):
    _name = 'res.users.empresa.rel'
    _description = 'Empresas por usuario con orden'
    _order = 'sequence, id'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
    empresa_id = fields.Many2one('sales.report.empresa', required=True)
    sequence = fields.Integer(default=10)

class ResUsers(models.Model):
    _inherit = 'res.users'

    empresa_ids = fields.Many2many(
        'sales.report.empresa',
        'res_users_sales_report_empresa_rel',
        'user_id',
        'empresa_id',
        string="Empresas permitidas"
    )

    empresa_rel_ids = fields.One2many(
        'res.users.empresa.rel',
        'user_id',
        string="Empresas (ordenadas)"
    )

