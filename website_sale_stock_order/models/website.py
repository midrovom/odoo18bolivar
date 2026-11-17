"""Expose stock-based choices in the native Odoo 18 shop ordering menu."""

from odoo import _, fields, models


class Website(models.Model):
    _inherit = 'website'

    # Applies automatically to websites created after the module installation.
    shop_default_sort = fields.Selection(default='stock_desc')

    def _get_product_sort_mapping(self):
        return super()._get_product_sort_mapping() + [
            ('stock_desc', _('Stock: mayor a menor')),
            ('stock_asc', _('Stock: menor a mayor')),
        ]
