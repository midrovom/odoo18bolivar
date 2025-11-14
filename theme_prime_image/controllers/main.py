from odoo.addons.theme_prime.controllers.main import ThemePrimeMainClass
from odoo.http import request

class ThemePrimeMainClassExtended(ThemePrimeMainClass):

    def _prepare_product_data(self, products, fields, pricelist, options=None):
        fields = list(set(fields or []))
        fields += ['attribute_line_ids']
        result = super()._prepare_product_data(products, fields, pricelist, options)

        for res_product, product in zip(result, products):
            res_product['attributes'] = []
            res_product['other_attributes'] = []

            for line in product.attribute_line_ids:
                if line.attribute_id.dr_is_brand:
                    continue

                for val in line.value_ids:
                    attr_data = {
                        'id': val.id,
                        'name': val.name,
                        'image': val.dr_image and f'/web/image/product.attribute.value/{val.id}/dr_image' or False,
                        'attribute_name': line.attribute_id.name,
                    }
                    if line.attribute_id.attribute_custom:
                        res_product['attributes'].append(attr_data)
                    else:
                        res_product['other_attributes'].append(attr_data)

        return result

    #funcion para precio 
    def _get_computed_product_price(self, product, product_data, price_public_visibility, visibility_label, currency_id):
        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {'display_currency': currency_id}
        res = super()._get_computed_product_price(
            product, product_data, price_public_visibility, visibility_label, currency_id
        )

        base_price = product.product_tmpl_id.list_price
        res.update({
            'list_price_base_raw': base_price if price_public_visibility else ' ',
            'list_price_base': FieldMonetary.value_to_html(base_price, monetary_options) if price_public_visibility else ' '
        })

        return res




# class ThemePrimeMainClassExtended(ThemePrimeMainClass):

#     def _prepare_product_data(self, products, fields, pricelist, options=None):
#         fields = list(set(fields or []))
#         fields += ['attribute_line_ids']

#         result = super()._prepare_product_data(products, fields, pricelist, options)

#         for res_product, product in zip(result, products):
#             res_product['attributes'] = []
#             for line in product.attribute_line_ids:
#                 if line.attribute_id.name != 'Marca':
#                     for val in line.value_ids:
#                         res_product['attributes'].append({
#                             'id': val.id,
#                             'name': val.name,
#                             'image': val.dr_image and f'/web/image/product.attribute.value/{val.id}/dr_image' or False,
#                         })

#         return result
