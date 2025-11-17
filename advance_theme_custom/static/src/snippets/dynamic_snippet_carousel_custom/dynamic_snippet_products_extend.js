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
        // Renderizamos todos los productos juntos
        options.chunkSize = this.data.length;
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
            items: itemsVisible,   // cuántos productos se ven a la vez
            slideBy: 1,            // avanzar de 1 en 1
            loop: false,
            nav: true,
            dots: true,
            margin: 20,            // espacio entre productos
        });
    },
});

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
