odoo.define('theme_prime_image.style1_slider', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.Style1Slider = publicWidget.Widget.extend({
        selector: '.js_style1_slider',
        start: function () {
            this.$el.owlCarousel({
                items: 1,   
                margin: 10,
                loop: true,
                nav: true,
                dots: true,
                autoplay: true,
                autoplayTimeout: 4000,
            });
            return this._super.apply(this, arguments);
        },
    });
});
