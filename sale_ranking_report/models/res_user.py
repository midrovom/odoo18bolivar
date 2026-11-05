from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ResUsers(models.Model):
    _inherit = 'res.users'

    _sql_constraints = [
        ('balance_code_uniq', 'UNIQUE(balance_code)', 'El código de vendedor debe ser único!'),
    ]
    