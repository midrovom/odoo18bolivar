from odoo.http import route
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteProductControllerExtended(WebsiteSale):

    @route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        # Llamar al controlador original
        result = super().get_products_by_category(domain, fields, options, **kwargs)

        # Tu lógica personalizada: agregar valores de atributos con imagen
        if options.get('get_attribute_values'):
            product_ids = result.get('products', [])
            attribute_values = request.env['product.attribute.value'].sudo().search([
                ('product_template_value_ids.product_tmpl_id', 'in', [p['id'] for p in product_ids])
            ])
            result['attribute_values'] = attribute_values.read(['name', 'dr_image', 'attribute_id'])

        return result
