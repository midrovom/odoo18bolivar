odoo.define('theme_prime_image.s_category_snippet_extended', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const CategorySnippet = publicWidget.registry.s_category_snippet;

    publicWidget.registry.s_category_snippet = CategorySnippet.extend({
        _getDomainValues: function (categoryID) {
            const original = this._super.apply(this, arguments);
            original.options.get_attribute_values = true;
            return original;
        },

        _processData: function (data) {
            if (data.attribute_values) {
                data.products.forEach(product => {
                    product.attribute_values = data.attribute_values[product.id] || [];
                });
            }
            return this._super.apply(this, arguments);
        },
    });
});
