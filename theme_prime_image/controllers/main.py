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


    from odoo.addons.website_sale.controllers.main import WebsiteSale
    from odoo.http import request
    class ThemePrimeWebsiteSaleExtended(WebsiteSale):

        def _prepare_product_values(self, product, category, search, **kwargs):
            res = super()._prepare_product_values(product, category, search, **kwargs)
            res['list_price_base'] = product.list_price
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
