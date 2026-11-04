# -*- coding: utf-8 -*-
from odoo import models, fields, api



class ResUsers(models.Model):
    _inherit = 'res.users'

    balance_code = fields.Char('Vendedor')


