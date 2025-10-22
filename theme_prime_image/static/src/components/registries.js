/** @odoo-module **/

import { registry } from "@web/core/registry";

const megaMenuRegistry = registry.category("theme_prime_mega_menu_cards");

megaMenuRegistry.add("s_tp_hierarchical_category_style_1", {
    supportedActions: [
        "limit",
        "brand",
        "label",
        "count",
        "style",
        "background",
        "layout",   // nueva opcion
    ],
});


// Extender el snippet de mega menú
const megaMenusRegistry = registry.category("theme_prime_mega_menus");

megaMenusRegistry.add("s_tp_mega_menu_category_snippet", {
    widgets: {
        TpUiComponent: {
            cardRegistry: "theme_prime_mega_menu_cards",
            defaultVal: {
                style: "s_tp_hierarchical_category_style_1",
                layout: "slider",   
                childOrder: "sequence",
                productListing: "newArrived",
                limit: 5,
                activeActions: ["brand", "label", "count"],
            },
        },
    },
});
