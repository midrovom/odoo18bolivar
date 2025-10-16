odoo.define('theme_prime_extended.s_category_snippet_extended', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');
    const CategorySnippet = publicWidget.registry.s_category_snippet;

    publicWidget.registry.s_category_snippet_extended = CategorySnippet.extend({
        /**
         * @override
         */
        _getDomainValues: function (categoryID) {
            const original = this._super.apply(this, arguments);
            // Agregamos la opción para que el backend devuelva los valores de atributos
            original.options.get_attribute_values = true;
            return original;
        },

        /**
         * @override
         */
        _processData: function (data) {
            // Procesamos los atributos personalizados si están presentes
            if (data.attribute_values) {
                this._renderAttributeValues(data.attribute_values);
            }
            // Ejecutamos la lógica original
            return this._super.apply(this, arguments);
        },

        /**
         * Renderiza los valores de atributos con imagen
         */
        _renderAttributeValues: function (values) {
            const container = this.$target.find('.attribute-container');
            if (!container.length) return;

            container.empty();
            values.forEach(val => {
                const imgUrl = val.dr_image ? `/web/image/product.attribute.value/${val.id}/dr_image` : '';
                const html = `<div class="attribute-block">
                    <img src="${imgUrl}" alt="${val.name}" />
                    <span>${val.name}</span>
                </div>`;
                container.append(html);
            });
        },
    });
});
