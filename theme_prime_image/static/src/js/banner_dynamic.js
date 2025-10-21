// import { registry } from '@web/core/registry';

// const originalProductsData = registry.category('theme_prime_data').get('PRODUCTS_DATA');
// const extendedProductsData = {
//     ...originalProductsData,
//     fields: [...originalProductsData.fields, 'attributes'], 
// };

/** @odoo-module **/

import { registry } from "@web/core/registry";

const brandCardRegistry = registry.category("theme_prime_brand_card_registry");

// Añadimos el estilo 6, igual que los demás
brandCardRegistry.add("tp_brand_card_style_6", { supportedActions: [] });
