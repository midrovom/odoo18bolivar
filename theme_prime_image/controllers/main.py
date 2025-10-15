from odoo import http
from odoo.http import request

class ThemePrimeExtensionController(http.Controller):

    @http.route('/get_products_by_category', type='json', auth='public')
    def get_products_by_category(self, category_id):
        products = request.env['product.template'].sudo().search([
            ('public_categ_ids', 'in', [category_id])
        ], limit=10)

        return [{
            'id': p.id,
            'name': p.name,
        } for p in products]
