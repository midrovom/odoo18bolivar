/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { localization } from "@web/core/l10n/localization";

publicWidget.registry.TpCategorySlider12 = publicWidget.Widget.extend({
    selector: '.tp-category-slider-12',
    jsLibs: ['/theme_prime/static/lib/OwlCarousel2-2.3.4/owl.carousel.js'],

    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        console.log("TpCategorySlider12 activo (snippet dinámico)");
        this._initializeOWL();
    },

    _initializeOWL: function () {
        const $owlSlider = this.$el;

        const responsiveParams = {
            0: { items: 2 },
            576: { items: 4 },
            768: { items: 6 },
            992: { items: 8 }
        };

        $owlSlider.removeClass('d-none container');
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
            responsive: responsiveParams
        });

        this.$('.tp-prev').click(function () {
            $owlSlider.trigger('prev.owl.carousel');
        });
        this.$('.tp-next').click(function () {
            $owlSlider.trigger('next.owl.carousel');
        });
    },
});
