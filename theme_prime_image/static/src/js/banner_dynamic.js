/** @odoo-module **/

import { registry } from "@web/core/registry";

// Extender el registry de estilos de tarjetas
registry.category("theme_prime_card_registry").add("my_card_style_custom", {
    supportedActions: ["add_to_cart", "wishlist", "rating"], // acciones que soporta
});
