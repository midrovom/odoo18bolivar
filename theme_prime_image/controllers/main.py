class WebsiteProductsExtended(WebsiteProducts):

    @http.route('/theme_prime/get_products_by_category', type='json', auth='public', website=True)
    def get_products_by_category(self, domain, fields=[], options={}, **kwargs):
        result = super().get_products_by_category(domain, fields=fields, options=options, **kwargs)

        for product in result.get('products', []):
            pt = request.env['product.template'].browse(product['id'])
            attributes = []
            for line in pt.attribute_line_ids:
                attributes.append({
                    'attribute': line.attribute_id.name,
                    'values': [val.name for val in line.value_ids],
                })
            product['attributes'] = attributes

        return result
