/** @odoo-module **/

import { registry } from '@web/core/registry';
// All of our work will be trash because registry will be no longer useful in next version.
let PRODUCTS_ACTIONS = ['rating', 'quick_view', 'add_to_cart', 'comparison', 'wishlist', 'category_info', 'label'];
let PRODUCTS_ACTIONS_2 = ['rating', 'category_info', 'add_to_cart', 'wishlist', 'comparison', 'description_ecommerce', 'label'];
let PRODUCTS_DATA = { models: ['product.template', 'product.product'], fields: ['name', 'list_price', 'dr_stock_label'], fieldsToMarkUp: ['price', 'list_price', 'dr_stock_label']}
let CATEGORIES_DATA = { fields: ['name'], fieldsToMarkUp: []};
let SELECTOR_DATA = { TpRecordSelector: { ...PRODUCTS_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.template'}}};
let EXTRA_OPTIONS = { TpExtraOpts: { startDate: '', endDate: '', priceList: '*' } };
let CATEGORY_SELECTOR_DATA = { TpRecordSelector: { ...CATEGORIES_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.public.category'}}};

let CATEGORY_ACTIONS = ['category_info', 'label'];

let CATEGORY_SELECTOR_DATA_CUSTOM = { TpRecordSelector: { ...CATEGORIES_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.public.category'}}};

//Registro para snippet product card 
//web
registry.category('theme_prime_card_registry')
    .add('s_card_style_9', { supportedActions: [...new Set([...PRODUCTS_ACTIONS, ...['show_similar']])]});
//mobile
// registry.category('theme_prime_mobile_card_registry')
//     .add('s_mobile_card_style_3', {supportedActions: []})
