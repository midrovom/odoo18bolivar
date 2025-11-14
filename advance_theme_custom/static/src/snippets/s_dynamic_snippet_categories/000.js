/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";
import { utils as uiUtils } from "@web/core/ui/ui_service";

const DEFAULT_NUMBER_OF_ELEMENTS = 4;
const DEFAULT_NUMBER_OF_ELEMENTS_SM = 4;  // 👈 aquí cambiamos el valor por defecto en móviles

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
        const options = this._super.apply(this, arguments);

        // Reemplazamos la lógica de rowPerSlide para móviles
        options.rowPerSlide = parseInt(
            uiUtils.isSmall()
                ? (this.el.dataset.numberOfElementsSmallDevices || DEFAULT_NUMBER_OF_ELEMENTS_SM)
                : (this.el.dataset.rowPerSlide || DEFAULT_NUMBER_OF_ELEMENTS)
        );

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
