/** @odoo-module **/

import publicWidget from 'web.public.widget';

publicWidget.registry.TpCategoryCarousel = publicWidget.Widget.extend({
    selector: '.droggol_product_slider',
    start: function () {
        if (this.$el.data('mode') === 'slider') {
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
        return this._super.apply(this, arguments);
    },
});
