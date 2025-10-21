/** @odoo-module **/

import { registry } from '@web/core/registry';

const originalProductsData = registry.category('theme_prime_data').get('PRODUCTS_DATA');
const extendedProductsData = {
    ...originalProductsData,
    fields: [...originalProductsData.fields, 'attributes'], 
};

// Registramos de nuevo, forzando la sobreescritura
registry.category('theme_prime_data').add('PRODUCTS_DATA', extendedProductsData, { force: true });





const brandCardRegistry = registry.category("theme_prime_brand_card_registry");
brandCardRegistry.add("tp_brand_card_style_custom", { supportedActions: [] });
