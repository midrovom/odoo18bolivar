/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("theme_prime_mega_menu_cards")
    .add("s_tp_hierarchical_category_style_1", {
        supportedActions: [
            "limit",
            "brand",
            "label",
            "count",
            "style",
            "background",
            "mode",   
        ],
    });

registry.category("theme_prime_mega_menus")
    .add("s_tp_mega_menu_category_snippet", {
        widgets: {
            TpUiComponent: {
                cardRegistry: "theme_prime_mega_menu_cards",
                defaultVal: {
                    style: "s_tp_hierarchical_category_style_1",
                    mode: "slider",   
                    childOrder: "sequence",
                    productListing: "newArrived",
                    limit: 5,
                    activeActions: ["brand", "label", "count"],
                },
            },
        },
    });


