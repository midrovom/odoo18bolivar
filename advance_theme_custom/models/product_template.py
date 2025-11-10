from odoo import models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_related_category_filter(self):
        return self.env.ref('advance_theme_custom.dynamic_filter_related_categories').id
