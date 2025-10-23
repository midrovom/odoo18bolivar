/** @odoo-module **/

import { registry } from '@web/core/registry';

let PRODUCTS_ACTIONS = ['rating', 'quick_view', 'add_to_cart', 'comparison', 'wishlist', 'category_info', 'label'];

registry.category('theme_prime_card_registry')
    .add('s_card_style_9', {
        supportedActions: [...new Set([...PRODUCTS_ACTIONS, ...['show_similar', 'colors']])]
    });
