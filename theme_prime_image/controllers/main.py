from odoo import http
from odoo.http import request
from odoo.addons.theme_prime.controllers.main import ThemePrimeController

class ThemePrimeControllerExtended(ThemePrimeController):

    @http.route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        # Llamar al controlador original
        result = super().get_products_by_category(domain, fields, options, **kwargs)

        # Agregar atributos personalizados agrupados por producto
        if options.get('get_attribute_values'):
            product_ids = [p['id'] for p in result['products']]
            values = request.env['product.template.attribute.value'].sudo().search([
                ('product_tmpl_id', 'in', product_ids)
            ])
            grouped = {}
            for val in values:
                pid = val.product_tmpl_id.id
                grouped.setdefault(pid, []).append({
                    'id': val.product_attribute_value_id.id,
                    'name': val.product_attribute_value_id.name,
                    'dr_image': val.product_attribute_value_id.dr_image,
                    'attribute_id': val.product_attribute_value_id.attribute_id.id,
                })
            result['attribute_values'] = grouped

        return result
