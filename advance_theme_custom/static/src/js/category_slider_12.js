odoo.define('advance_theme_custom.owl_snippet', function (require) {
    'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.OwlCarouselSnippet = publicWidget.Widget.extend({
        selector: '.tp-category-slider-12',
        start: function () {
            if (this.$el.hasClass('owl-loaded')) {
                this.$el.trigger('destroy.owl.carousel');
                this.$el.removeClass('owl-loaded');
                this.$el.find('.owl-stage-outer').children().unwrap();
            }

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

            return this._super.apply(this, arguments);
        },
    });
});
