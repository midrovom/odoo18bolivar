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
            // En móvil: 2 visibles, slide de 1 en 1
            options.chunkSize = this.data.length; // todos juntos
        } else {
            // En escritorio: 6 visibles, slide de 1 en 1
            options.chunkSize = this.data.length; // todos juntos
        }
        return options;
    },

    /**
     * @override
     */
    _modifyElementsAfterAppend() {
        this._super.apply(this, arguments);

        const isMobile = uiUtils.isSmall();
        const itemsVisible = isMobile ? 2 : 6;

        this.$('.owl-carousel').owlCarousel({
            items: itemsVisible,
            slideBy: 1,   // mueve de 1 en 1
            loop: false,
            nav: true,
            dots: true,
            margin: 10,
        });
    },
});

// Sobrescribe el registro original
publicWidget.registry.dynamic_snippet_products = DynamicSnippetProductsExtended;

export default DynamicSnippetProductsExtended;


// /** @odoo-module **/
// import publicWidget from "@web/legacy/js/public/public_widget";
// import DynamicSnippetProducts from "@website_sale/snippets/s_dynamic_snippet_products/000";
// import { utils as uiUtils } from "@web/core/ui/ui_service";

// const DynamicSnippetProductsExtended = DynamicSnippetProducts.extend({
//     /**
//      * @override
//      */
//         _getQWebRenderOptions() {
//         const options = this._super.apply(this, arguments);
//         if (uiUtils.isSmall()) {
//             options.chunkSize = 2; //vista de productos mobil
//         } else {
//             options.chunkSize = 6;// cantidad de productos web/escritorio
//         }
//         return options;
//     },
// });

// // Se sobreescribe el registro original
// publicWidget.registry.dynamic_snippet_products = DynamicSnippetProductsExtended;

// export default DynamicSnippetProductsExtended;
