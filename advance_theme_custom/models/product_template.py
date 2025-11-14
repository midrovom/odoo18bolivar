from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _get_combination_info(self, combination=False, product_id=False, add_qty=1.0,
                            parent_combination=False, only_template=False):
        combination_info = super()._get_combination_info(
            combination=combination,
            product_id=product_id,
            add_qty=add_qty,
            parent_combination=parent_combination,
            only_template=only_template
        )

        if combination_info.get('product_id'):
            product_variant = self.env['product.product'].browse(combination_info['product_id'])
            combination_info['list_price_base'] = product_variant.product_tmpl_id.list_price

        return combination_info
