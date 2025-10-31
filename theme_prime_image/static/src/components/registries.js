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

registry.category('theme_prime_snippet_registry')
    .add('s_d_categories_snippet', {
        widgets: {
            ...CATEGORY_SELECTOR_DATA_CUSTOM,
            TpUiComponent: { cardRegistry: 'theme_prime_card_registry', defaultVal: { style: 's_card_style_1', mode: 'slider', ppr: 4, activeActions: CATEGORY_ACTIONS, mobileConfig: { style: 'default', mode: 'default' } } },
            ...EXTRA_OPTIONS
        },
        defaultValue: { hasSwitcher: true, }
    });

//Registro para snippet product card 
//web
registry.category('theme_prime_card_registry')
    .add('s_card_style_9', { supportedActions: [...new Set([...PRODUCTS_ACTIONS, ...['show_similar']])]});
//mobile
// registry.category('theme_prime_mobile_card_registry')
//     .add('s_mobile_card_style_3', {supportedActions: []})


registry.category('theme_prime_mega_menu_cards')
   // .add('s_tp_hierarchical_category_style_12', {supportedActions: ['limit', 'brand', 'label', 'count', 'style', 'background', PRODUCTS_ACTIONS]})
    .add('s_tp_hierarchical_category_style_13', {supportedActions: ['limit', 'brand', 'label', 'count', 'style', 'background', PRODUCTS_ACTIONS]});
    
registry.category('theme_prime_category_card_registry')
    .add('s_tp_category_style_6', { supportedActions: [] });