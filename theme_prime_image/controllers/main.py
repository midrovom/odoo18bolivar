from odoo import http
from odoo.http import request

class ThemePrimeExtensionController(http.Controller):

    @http.route('/get_products_by_slug', type='json', auth='public')
    def get_products_by_slug(self, slug):
        category = request.env['product.public.category'].sudo().search([
            ('name', 'ilike', slug)
        ], limit=1)

        if not category:
            return []

        products = request.env['product.template'].sudo().search([
            ('public_categ_ids', 'in', [category.id])
        ], limit=10)

        return [{
            'id': p.id,
            'name': p.name,
        } for p in products]
