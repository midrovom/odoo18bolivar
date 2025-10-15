from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.addons.theme_prime.controllers.main import ThemePrimeController

class ThemePrimeImageController(ThemePrimeController):

    @http.route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        final_domain = expression.AND([[('website_published', '=', True)], domain])
        products = self._get_products(domain=final_domain, fields=fields, order=options.get('order', False), limit=options.get('limit', False), options=options)

        for product in products:
            attribute_data = []
            for line in product.attribute_line_ids:
                if line.attribute_id.name != 'Marca':
                    values = []
                    for val in line.value_ids:
                        values.append({
                            'id': val.id,
                            'name': val.name,
                            'dr_image': bool(val.dr_image),
                        })
                    attribute_data.append({
                        'attribute_id': {'name': line.attribute_id.name},
                        'value_ids': values,
                    })
            product.attribute_line_ids_data = attribute_data  # campo virtual para JS

        result = {
            'products': [{
                'id': p.id,
                'name': p.name,
                'list_price': p.list_price,
                'attribute_line_ids': getattr(p, 'attribute_line_ids_data', []),
            } for p in products],
        }

        result.update(self._get_shop_related_data(options))

        if options.get('get_categories'):
            domain = [('id', 'in', options.get('categoryIDs'))]
            result['categories'] = self._get_categories(domain)

        if options.get('get_brands'):
            domain = [('id', 'in', options.get('categoryIDs'))]
            result['categories'] = request.website._get_brands(domain).read(['name', 'id'])

        return result
