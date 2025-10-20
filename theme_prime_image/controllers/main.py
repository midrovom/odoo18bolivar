from odoo import http
from odoo.http import request

class BannerDynamic(http.Controller):

    @http.route('/banner/products', type='json', auth='public', website=True)
    def banner_products(self, limit=3):
        products = request.env['product.template'].search([('website_published', '=', True)], limit=limit)
        return [
            {
                'id': p.id,
                'name': p.name,
                'list_price': p.list_price,
                'website_url': p.website_url,
            }
            for p in products
        ]