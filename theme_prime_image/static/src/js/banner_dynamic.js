/** @odoo-module **/

import { registry } from '@web/core/registry';

const originalProductsData = registry.category('theme_prime_data').get('PRODUCTS_DATA');
const extendedProductsData = {
    ...originalProductsData,
    fields: [...originalProductsData.fields, 'attributes'], 
};

// Registramos de nuevo, forzando la sobreescritura
registry.category('theme_prime_data').add('PRODUCTS_DATA', extendedProductsData, { force: true });
