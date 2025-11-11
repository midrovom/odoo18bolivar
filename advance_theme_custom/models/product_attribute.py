from odoo import models, fields

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    attribute = fields.Boolean(string="Atributos para productos")
