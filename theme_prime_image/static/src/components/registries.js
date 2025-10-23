/** @odoo-module **/

import { registry } from '@web/core/registry';
let PRODUCTS_ACTIONS = ['rating', 'quick_view', 'add_to_cart', 'comparison', 'wishlist', 'category_info', 'label'];
let PRODUCTS_ACTIONS_2 = ['rating', 'category_info', 'add_to_cart', 'wishlist', 'comparison', 'description_ecommerce', 'label'];
let PRODUCTS_DATA = { models: ['product.template', 'product.product'], fields: ['name', 'list_price', 'dr_stock_label'], fieldsToMarkUp: ['price', 'list_price', 'dr_stock_label']}
let CATEGORIES_DATA = { fields: ['name'], fieldsToMarkUp: []};
let SELECTOR_DATA = { TpRecordSelector: { ...PRODUCTS_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.template'}}};
let EXTRA_OPTIONS = { TpExtraOpts: { startDate: '', endDate: '', priceList: '*' } };

registry.category('theme_prime_card_registry')
    .add('s_card_style_9', { supportedActions: [...new Set([...PRODUCTS_ACTIONS, ...['show_similar']])]})

