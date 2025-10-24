/** @odoo-module **/
import { registry } from '@web/core/registry';

let PRODUCTS_ACTIONS = ['rating', 'quick_view', 'add_to_cart', 'comparison', 'wishlist', 'category_info', 'label'];
let PRODUCTS_ACTIONS_2 = ['rating', 'category_info', 'add_to_cart', 'wishlist', 'comparison', 'description_ecommerce', 'label'];
let PRODUCTS_DATA = { models: ['product.template', 'product.product'], fields: ['name', 'list_price', 'dr_stock_label'], fieldsToMarkUp: ['price', 'list_price', 'dr_stock_label']}
let CATEGORIES_DATA = { fields: ['name'], fieldsToMarkUp: []};
let SELECTOR_DATA = { TpRecordSelector: { ...PRODUCTS_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.template'}}};
let EXTRA_OPTIONS = { TpExtraOpts: { startDate: '', endDate: '', priceList: '*' } };
let CATEGORY_SELECTOR_DATA = { TpRecordSelector: { ...CATEGORIES_DATA, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.public.category'}}};


registry.category('theme_prime_card_registry')
    .add('s_card_style_9', { supportedActions: [...new Set([...PRODUCTS_ACTIONS, ...['show_similar']])]})

registry.category('theme_prime_snippet_registry')
    .add('s_d_products_snippet', {
        widgets: {
            ...SELECTOR_DATA,
            TpUiComponent: { cardRegistry: 'theme_prime_card_registry', defaultVal: { style: 's_card_style_1', mode: 'slider', ppr: 4, activeActions: PRODUCTS_ACTIONS, mobileConfig: { style: 'default', mode: 'default' } } },
            ...EXTRA_OPTIONS
        },
        defaultValue: { hasSwitcher: true, }
    })
    .add('s_d_single_product_count_down', { widgets: { ...SELECTOR_DATA, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 5} })
    .add('s_two_column_cards', { widgets: { ...SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_two_column_card_registry', defaultVal: { style: 'tp_two_column_card_style_1', mode: 'slider', activeActions: PRODUCTS_ACTIONS_2 } }, ...EXTRA_OPTIONS } })
    .add('s_d_products_grid', { widgets: { ...SELECTOR_DATA, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 9 } })
    .add('s_d_category_snippet', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_card_registry', defaultVal: { style: 's_card_style_1', sortBy: 'list_price asc', tabStyle: 'tp-droggol-18-builder-snippet-tab-1', mode: 'slider', limit: 8, ppr: 4, includesChild: true, activeActions: PRODUCTS_ACTIONS, mobileConfig: { style: 'default', mode: 'default' } } }, ...EXTRA_OPTIONS } })
    .add('s_products_by_brands_tabs', { widgets: { TpRecordSelector: { model: 'product.attribute.value', fields: ['name'], isBrand: true, fieldsToMarkUp: [], defaultVal: { selectionType: 'manual', recordsIDs: [],model: 'product.attribute.value' } }, TpUiComponent: { cardRegistry: 'theme_prime_card_registry', defaultVal: { tabStyle: 'tp-droggol-18-builder-snippet-tab-1', style: 's_card_style_1', sortBy: 'list_price asc', mode: 'slider', ppr: 4, activeActions: PRODUCTS_ACTIONS, limit: 6, mobileConfig: { style: 'default', mode: 'default' } } } } })
    .add('s_d_brand_snippet', { widgets: { TpRecordSelector: { model: 'product.attribute.value', fields: ['name'], isBrand: true, fieldsToMarkUp: [], defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.attribute.value' } }, TpUiComponent: { cardRegistry: 'theme_prime_brand_card_registry', defaultVal: { style: 'tp_brand_card_style_1', mode: 'slider' } }, ...EXTRA_OPTIONS } })
    .add('s_brands_small', { widgets: { TpRecordSelector: { model: 'product.attribute.value', fields: ['name'], isBrand: true, fieldsToMarkUp: [], defaultVal: { selectionType: 'manual', recordsIDs: [],model: 'product.attribute.value' } } }, defaultValue: { recordsLimit: 8 } })
    .add('s_category_small', { widgets: { ...CATEGORY_SELECTOR_DATA }, defaultValue: { recordsLimit: 8 } })
    .add('s_d_single_category_snippet', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_small_card_registry', defaultVal: { style: 'tp_category_product_card_style_1', sortBy: 'list_price asc', activeActions: ['add_to_cart', 'rating', 'category_info'], includesChild: true, } }, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 1} })
    .add('s_d_single_product_snippet', { widgets: { TpRecordSelector: { ...PRODUCTS_DATA, ...{ models: ['product.template']} , defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.template' }}, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 1} })
    .add('s_d_single_product_cover_snippet', { widgets: { TpRecordSelector: { ...PRODUCTS_DATA, ...{ models: ['product.template'] }, defaultVal: { selectionType: 'manual', recordsIDs: [], model: 'product.template' } }, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 1} })
    .add('s_d_product_count_down', { widgets: { ...SELECTOR_DATA, ...EXTRA_OPTIONS }, defaultValue: { noSnippet: true }})
    .add('s_d_product_small_block', { widgets: { ...SELECTOR_DATA, ...EXTRA_OPTIONS }, defaultValue: { noSnippet: true }})
    .add('s_d_image_products_block', { widgets: { ...SELECTOR_DATA, ...EXTRA_OPTIONS }, defaultValue: { hasSwitcher: true, } })
    .add('s_d_top_categories', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_top_category_card_registry', defaultVal: { style: 'tp_category_category_card_style_1', sortBy: 'list_price asc', includesChild: true } }, ...EXTRA_OPTIONS }, defaultValue: { recordsLimit: 3} })
    .add('s_category_snippet', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_category_card_registry', defaultVal: { style: 's_tp_category_style_1' } }, ...EXTRA_OPTIONS } })
    .add('s_product_listing_cards', { widgets: { TpUiComponent: { cardRegistry: 'theme_prime_product_list_cards', defaultVal: { header: 'tp_product_list_header_1', style: 'tp_product_list_cards_1', limit: 5, activeActions: ['rating'], bestseller: true, newArrived: true, discount: true } }, ...EXTRA_OPTIONS }, defaultValue: { noSelection: true, maxValue: 5, minValue: 2} })
    .add('s_image_product_listing_cards', { widgets: { TpUiComponent: { cardRegistry: 'theme_prime_product_list_cards', defaultVal: { header: 'tp_product_list_header_1', style: 'tp_product_list_cards_1', limit: 5, activeActions: ['rating'], bestseller: true, newArrived: true, discount: true } }, ...EXTRA_OPTIONS}, defaultValue: { noSelection: true, maxValue: 5, minValue: 2} })
    .add('s_tp_mega_menu_category_snippet', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_mega_menu_cards', defaultVal: { style: 's_tp_hierarchical_category_style_1', childOrder: 'sequence', productListing: 'newArrived', limit: 5, activeActions: ['brand', 'label', 'count'] } }, ...EXTRA_OPTIONS }, defaultValue: { maxValue: 10, minValue: 2} })
    .add('s_mega_menu_category_tabs_snippet', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_mega_menu_tabs_styles', defaultVal: { style: 'tp_mega_menu_tab_style_1', childOrder: 'sequence', menuLabel: true, onlyDirectChild: false, categoryTabsConfig: { activeRecordID: false, records: [] } } }, ...EXTRA_OPTIONS }, defaultValue: { noSwicher: true, lazy: true} })
    .add('s_product_listing_tabs', { widgets: { ...CATEGORY_SELECTOR_DATA, TpUiComponent: { cardRegistry: 'theme_prime_card_registry', defaultVal: { mode: 'slider', ppr: 4, tabStyle: 'tp-droggol-18-builder-snippet-tab-1', style: 's_card_style_1', limit: 20, activeActions: PRODUCTS_ACTIONS, bestseller: true, newArrived: true, discount: true, mobileConfig: { style: 'default', mode: 'default' } } }, ...EXTRA_OPTIONS}, defaultValue: { forceVisible: true, recordsLimit: 1} });
