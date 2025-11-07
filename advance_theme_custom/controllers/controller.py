from odoo import http
from odoo.http import request

class WebsiteCategorySnippet(http.Controller):

    @http.route('/website/snippet/categories', type='json', auth='public')
    def categories_handler(self, domain=None):
        categories = request.env['product.public.category'].sudo().search(domain or [], limit=12)
        return [{
            "name": cat.name,
            "url": f"/shop/category/{cat.id}",
            "image": f"/web/image/product.public.category/{cat.id}/image_1920"
        } for cat in categories]
