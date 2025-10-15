odoo.define('theme_prime_image.s_category_snippet_extend', function (require) {
  const publicWidget = require('web.public.widget');
  const baseWidget = publicWidget.registry.s_category_snippet;

  publicWidget.registry.s_category_snippet = baseWidget.extend({
    /**
     * @override
     */
    _markUpValues: function (fields, products) {
      // Llamamos al original
      this._super.apply(this, arguments);

      // Inyectamos atributos debajo del nombre
      products.forEach(product => {
        const $card = this.$el.find(`[data-product-id="${product.id}"]`);
        if (!$card.length) return;

        const $nameBlock = $card.find('.product-name');
        if (!$nameBlock.length) return;

        const $attrList = $('<ul class="list-unstyled small text-muted text-start text-wrap mt-2"></ul>');
        if (product.attribute_line_ids) {
          product.attribute_line_ids.forEach(attr => {
            if (attr.attribute_id.name !== 'Marca') {
              attr.value_ids.forEach(val => {
                const $li = $('<li class="d-flex align-items-center mb-1 text-truncate"></li>');
                if (val.dr_image) {
                  $li.append(`<img src="/web/image/product.attribute.value/${val.id}/dr_image" alt="${val.name}" class="attr-icon me-2"/>`);
                }
                $li.append(`<span>${attr.attribute_id.name}: ${val.name}</span>`);
                $attrList.append($li);
              });
            }
          });
        }

        $nameBlock.after($attrList);
      });
    },
  });
});
