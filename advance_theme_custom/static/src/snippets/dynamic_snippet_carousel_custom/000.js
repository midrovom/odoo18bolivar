// /** @odoo-module **/

// import publicWidget from "@web/legacy/js/public/public_widget";
// import DynamicSnippetProducts from "@website/snippets/s_dynamic_snippet_products/000"; 
// import { utils as uiUtils } from "@web/core/ui/ui_service";

// const DynamicSnippetProductsCustom = DynamicSnippetProducts.extend({
//     selector: ".s_dynamic_snippet_products",  

//     /**
//      * @override
//      * @private
//      */
//     _getQWebRenderOptions: function () {
//         const options = this._super.apply(this, arguments);

//         if (uiUtils.isSmall()) {
//             options.rowPerSlide = 2;  // en móviles ahora serán 2 elementos por slide
//         }

//         return options;
//     },
// });

// publicWidget.registry.dynamic_snippet_products = DynamicSnippetProductsCustom;

// export default DynamicSnippetProductsCustom;
