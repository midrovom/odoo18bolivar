
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    code_supervisor = fields.Char('Código de supervisor')