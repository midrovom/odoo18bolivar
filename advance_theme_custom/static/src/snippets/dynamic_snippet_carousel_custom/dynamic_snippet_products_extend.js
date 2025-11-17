/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetProducts from "@website_sale/snippets/s_dynamic_snippet_products/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DynamicSnippetProductsExtended = DynamicSnippetProducts.extend({
    /**
     * @override
     * Ajustamos las opciones de renderizado para no dividir en chunks.
     */
    _getQWebRenderOptions() {
        const options = this._super.apply(this, arguments);

        // En lugar de dividir en grupos, pasamos todos los productos juntos
        options.chunkSize = this.data.length;

        return options;
    },

    /**
     * @override
     * Inicializamos OwlCarousel para que avance producto por producto.
     */
    _modifyElementsAfterAppend() {
        this._super.apply(this, arguments);

        const isMobile = uiUtils.isSmall();
        const itemsVisible = isMobile ? 2 : 6; // 2 en móvil, 6 en escritorio

        this.$('.owl-carousel').owlCarousel({
            items: itemsVisible,  // cuántos productos se ven a la vez
            slideBy: 1,           // avanzar de 1 en 1
            loop: false,
            nav: true,
            dots: true,
            margin: 100,
        });
    },
});

// Sobrescribimos el registro original
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
