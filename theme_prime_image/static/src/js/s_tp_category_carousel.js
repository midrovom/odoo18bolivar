/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.TpCategoryStyle12Slider = publicWidget.Widget.extend({
    selector: '.js_style12_slider',
    start: function () {
        // Solo inicializar si hay ítems
        if (this.$el.find('.item').length) {
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
