from odoo import http
from odoo.http import request
from odoo.addons.theme_prime.controllers.main import ThemePrimeMainClass

class ThemePrimeMainClassExtended(ThemePrimeMainClass):

    @http.route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        # 1. Llamamos al método original de Theme Prime
        result = super().get_products_by_category(domain, fields=fields, options=options, **kwargs)

        # 2. Añadimos atributos de producto al resultado
        for product in result.get('products', []):
            pt = request.env['product.template'].sudo().browse(product['id'])
            attributes = []
            for line in pt.attribute_line_ids:
                attributes.append({
                    'attribute': line.attribute_id.name,
                    'values': [val.name for val in line.value_ids],
                })
            product['attributes'] = attributes

        return result
