"""Let administrators choose the default sorting mode per website."""

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    website_stock_sort_default = fields.Selection(
        string='Orden predeterminado de la tienda',
        related='website_id.shop_default_sort',
        readonly=False,
    )
