# from odoo import http
# from odoo.http import request
# from odoo.addons.theme_prime.controllers.main import ThemePrimeMainClass


# class ThemePrimeMainClassExtended(ThemePrimeMainClass):

#     def _prepare_product_data(self, products, fields, pricelist, options=None):
#         # Asegurar que los campos necesarios para atributos estén incluidos
#         fields = list(set(fields or []))
#         fields += [
#             'attribute_line_ids',
#             'attribute_line_ids.attribute_id',
#             'attribute_line_ids.value_ids',
#             'attribute_line_ids.value_ids.name',
#             'attribute_line_ids.value_ids.dr_image',
#         ]

#         # Llamar al método original para conservar toda la lógica base
#         result = super()._prepare_product_data(products, fields, pricelist, options)

#         # Agregar atributos personalizados a cada producto
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
