from odoo import models, fields

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    is_dia = fields.Boolean(string="Día atributo")
