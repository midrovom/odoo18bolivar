from odoo import http
from odoo.http import request
from odoo.addons.theme_prime.controllers.main import ThemePrimeController

class ThemePrimeImageController(ThemePrimeController):

    @http.route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        # Ejecuta el controlador original
        result = super().get_products_by_category(domain, fields, options, **kwargs)

        # Añade atributos personalizados a cada producto
        for product in result.get('products', []):
            product_record = request.env['product.template'].sudo().browse(product['id'])
            attribute_data = []
            for line in product_record.attribute_line_ids:
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
            product['attribute_line_ids'] = attribute_data

        return result
