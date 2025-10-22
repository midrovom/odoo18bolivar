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
        "mode",   // nueva opcion
    ],
});


