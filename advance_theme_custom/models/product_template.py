from odoo import api, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_related_category_filter(self):
        # Devuelve el ID del filtro dinámico de categorías relacionadas
        return self.env.ref('advance_theme_custom.dynamic_filter_related_categories').id
