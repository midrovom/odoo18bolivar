from odoo import models, fields

class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    atributo = fields.Boolean(string="marcar atributo")
