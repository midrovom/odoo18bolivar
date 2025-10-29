odoo.define('theme_prime_image.category_carousel', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.CategoryCarousel = publicWidget.Widget.extend({
        selector: '.owl-carousel.droggol_product_slider',
        on_attach_callback: function () {
            this._initCarousel();
        },
        start: function () {
            this._initCarousel();
            return this._super.apply(this, arguments);
        },
        _initCarousel: function () {
            if (this.$el.length && !this.$el.hasClass('owl-loaded')) {
                this.$el.owlCarousel({
                    items: 8,
                    margin: 10,
                    loop: true,
                    nav: true,
                    dots: false,
                    responsive: {
                        0: { items: 2 },
                        576: { items: 4 },
                        768: { items: 6 },
                        992: { items: 8 }
                    }
                });
            }
        },
    });
});
