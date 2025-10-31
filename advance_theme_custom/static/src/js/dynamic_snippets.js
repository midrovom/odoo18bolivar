/** @odoo-module **/

import "@website/js/content/menu";
import publicWidget from "@web/legacy/js/public/public_widget";
import ProductRootWidget from "@theme_prime/js/core/product_root_widget";
import RootWidget from "@theme_prime/js/core/snippet_root_widget";
import { rpc } from "@web/core/network/rpc";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import animations from "@website/js/content/snippets.animation";
import { OwlMixin, MarkupRecords, ProductsBlockMixins, CategoryPublicWidgetMixins, ProductCarouselMixins, CartManagerMixin, HotspotMixns, cartMixin, TabsMixin } from "@theme_prime/js/core/mixins";
import { pick } from "@web/core/utils/objects";
import { groupBy } from "@web/core/utils/arrays";
import { renderToElement } from "@web/core/utils/render";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";


publicWidget.registry.s_d_categories_snippet = ProductRootWidget.extend(OwlMixin, ProductsBlockMixins, {
    selector: '.s_d_categories_snippet_wrapper',

    bodyTemplate: 'd_s_cards_wrapper_categories',
    bodySelector: '.s_d_products_snippet',
    controllerRoute: '/theme_prime/get_categories_info',
    fieldstoFetch: ['dr_category_label_id'],
    snippetNodeAttrs: (ProductRootWidget.prototype.snippetNodeAttrs || []).concat(['data-selection-info']),

    /**
     * initialize owlCarousel.
     * @private
     */
    _modifyElementsAfterAppend: function () {
        this._super.apply(this, arguments);
        if (this.uiConfigInfo.mode === 'slider') {
            this.initializeOwlSlider(this.uiConfigInfo.ppr);
        }
    },
});