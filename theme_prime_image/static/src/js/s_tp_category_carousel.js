/** @odoo-module **/

import { Component, onMounted } from "@odoo/owl";

export class Style12Slider extends Component {
    setup() {
        onMounted(() => {
            const $el = $(this.el).find(".js_style_12");
            if ($el.length && $.fn.owlCarousel) {
                $el.owlCarousel({
                    items: 4,   // ajusta según lo que quieras mostrar
                    margin: 10,
                    loop: true,
                    nav: true,
                    dots: false,
                    autoplay: true,
                    autoplayTimeout: 4000,
                    responsive: {
                        0: { items: 2 },
                        576: { items: 3 },
                        768: { items: 4 },
                        992: { items: 6 }
                    }
                });
            }
        });
    }
}
Style12Slider.template = "s_tp_hierarchical_category_style_12";
