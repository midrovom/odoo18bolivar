/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { localization } from "@web/core/l10n/localization";

publicWidget.registry.TpCategorySlider12 = publicWidget.Widget.extend({
    selector: '.tp-category-slider-12',
    jsLibs: ['/theme_prime/static/lib/OwlCarousel2-2.3.4/owl.carousel.js'],

    on_attach_callback: function () {
        console.log("TpCategorySlider12 activo (snippet dinámico)");
        this._initializeOWL();
    },

    _initializeOWL: function () {
        const $owlSlider = this.$el;

        if ($owlSlider.hasClass("owl-loaded")) {
            $owlSlider.trigger("refresh.owl.carousel");
            return;
        }

        $owlSlider.owlCarousel({
            dots: false,
            margin: 10,
            loop: true,
            nav: true,
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
    },
});
