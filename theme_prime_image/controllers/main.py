from odoo.addons.theme_prime.controllers.main import ThemePrimeMainClass
from odoo.http import request


# class ThemePrimeMainClassExtended(ThemePrimeMainClass):

#     def _prepare_product_data(self, products, fields, pricelist, options=None):
#         fields = list(set(fields or []))
#         fields += ['attribute_line_ids']  # Solo este campo es necesario para acceder desde el objeto

#         result = super()._prepare_product_data(products, fields, pricelist, options)

#         for res_product, product in zip(result, products):
#             res_product['attributes'] = []
#             for line in product.attribute_line_ids:
#                 if line.attribute_id.name != 'Marca':
#                     for val in line.value_ids:
#                         res_product['attributes'].append({
#                             'id': val.id,
#                             'name': val.name,
#                             'image': val.dr_image,
#                         })

#         return result

class ThemePrimeMainClassExtended(ThemePrimeMainClass):

    def _prepare_product_data(self, products, fields, pricelist, options=None):
        fields = list(set(fields or []))
        fields += ['attribute_line_ids']

        result = super()._prepare_product_data(products, fields, pricelist, options)

        for res_product, product in zip(result, products):
            res_product['attributes'] = []
            for line in product.attribute_line_ids:
                if line.attribute_id.name != 'Marca':
                    for val in line.value_ids:
                        res_product['attributes'].append({
                            'id': val.id,
                            'name': val.name,
                            'image': val.dr_image and f'/web/image/product.attribute.value/{val.id}/dr_image' or False,
                        })

        return result
