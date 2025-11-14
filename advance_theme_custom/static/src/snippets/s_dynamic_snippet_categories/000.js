/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
    selector: ".s_dynamic_snippet_categories",

    /**
     * @override
     * @private
     */
    _getMainPageUrl() {
        return "/shop";
    },

    /**
     * @override
     * @private
     */
    _getQWebRenderOptions: function () {
        // obtenemos las opciones originales del padre
        const options = this._super.apply(this, arguments);

        if (uiUtils.isSmall()) {
            options.rowPerSlide = 2;  // en móviles ahora serán 2 elementos por slide
        }

        // en pantallas grandes se mantiene la lógica original
        return options;
    },
});

publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;

export default DynamicSnippetCategories;




// /** @odoo-module **/
// import publicWidget from "@web/legacy/js/public/public_widget";
// import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";

// const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
//     selector: ".s_dynamic_snippet_categories",

//     /**
//      * @override
//      * @private
//      */
//     _getMainPageUrl() {
//         return "/shop";
//     },


// });

// publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;

// export default DynamicSnippetCategories;
