odoo.define('theme_prime_extension.dynamic_gallery', function (require) {
  const publicWidget = require('web.public.widget');
  const ajax = require('web.ajax');

  publicWidget.registry.DynamicGallery = publicWidget.Widget.extend({
    selector: '.s_products_gallery',
    start: function () {
      const button = this.$el.find('.o_we_button');
      if (!button.length) return;

      const url = button.attr('href');
      const match = url.match(/category\/([\w-]+)-\d+/);
      const slug = match ? match[1].replace(/-/g, ' ') : null;

      if (slug) {
        ajax.jsonRpc('/get_products_by_slug', 'call', { slug }).then(products => {
          this._renderCards(products);
        });
      }
    },

    _renderCards: function (products) {
      const container = this.$el.find('.row');
      container.empty();

      for (let i = 0; i < 10; i++) {
        const product = products[i];
        const card = $('<div class="col"><div class="product-card text-center p-3 h-100"></div></div>');

        if (product) {
          card.find('.product-card').append(`
            <img src="/web/image/product.template/${product.id}/image_1920" alt="${product.name}" class="img-fluid mb-2"/>
            <hr class="my-2"/>
            <h5 class="fw-bold text-truncate">${product.name}</h5>
          `);
        } else {
          card.find('.product-card').append(`
            <div class="img-fluid mb-2" style="height:150px; background:#f0f0f0;"></div>
            <hr class="my-2"/>
            <h5 class="fw-bold text-truncate text-muted">Próximamente</h5>
          `);
        }

        container.append(card);
      }
    },
  });

  return publicWidget.registry.DynamicGallery;
});
