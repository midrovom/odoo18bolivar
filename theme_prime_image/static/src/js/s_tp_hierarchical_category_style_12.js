odoo.define('theme_prime_image.category_carousel', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.CategoryCarousel = publicWidget.Widget.extend({
        selector: '.owl-carousel.droggol_product_slider',
        start: function () {
            this.$el.owlCarousel({
                items: 4,
                margin: 10,
                loop: true,
                nav: true,
                dots: false,
                responsive: {
                    0: { items: 1 },
                    576: { items: 2 },
                    768: { items: 3 },
                    992: { items: 4 }
                }
            });
        },
    });
});
