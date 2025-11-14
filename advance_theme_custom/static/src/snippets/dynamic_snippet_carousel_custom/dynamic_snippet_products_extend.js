/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetProducts from "@website_sale/snippets/s_dynamic_snippet_products/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DynamicSnippetProductsExtended = DynamicSnippetProducts.extend({
    /**
     * @override
     */
    _getQWebRenderOptions() {
        const options = this._super.apply(this, arguments);
        if (uiUtils.isSmall()) {
            options.chunkSize = 2;      // dos cards por fila en móvil
            //options.rowPerSlide = 2;    // agrupa de dos en dos
        }
        return options;
    },
});

// Sobrescribimos el registro original
publicWidget.registry.dynamic_snippet_products = DynamicSnippetProductsExtended;

export default DynamicSnippetProductsExtended;
