/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { localization } from "@web/core/l10n/localization";

publicWidget.registry.TpCategorySlider12 = publicWidget.Widget.extend({
    selector: '.owl-carousel.tp-category-slider-12',

    start: function () {
        const $owlSlider = this.$el;
        $owlSlider.owlCarousel({
            items: 8,
            margin: 10,
            loop: true,
            nav: true,
            dots: false,
            autoplay: true,
            autoplayTimeout: 3000,
            autoplayHoverPause: true,
            rewind: true,
            rtl: localization.direction === 'rtl',
            responsive: {
                0: { items: 2 },
                576: { items: 4 },
                768: { items: 6 },
                992: { items: 8 }
            }
        });
        return this._super.apply(this, arguments);
    },
});
