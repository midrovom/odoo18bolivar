/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";

const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_product_categories',

    //----------------------------------------------------------------------
    // Private
    //----------------------------------------------------------------------

    /**
     * @override
     */
    async _fetchData() {
        const limit = parseInt(this.el.dataset.snippetMaxItems) || 10;

        // Aquí llamamos directamente al modelo product.public.category
        const categories = await rpc("/web/dataset/call_kw/product.public.category/search_read", {
            model: "product.public.category",
            method: "search_read",
            args: [[]], // sin dominio (trae todas)
            kwargs: {
                fields: ["id", "name", "image_1920"],
                limit: limit,
            },
        });

        return categories;
    },

    /**
     * @override
     */
    _prepareTemplateData(categories) {
        // Convertimos el formato para que el carrusel lo pueda entender
        return categories.map(category => ({
            id: category.id,
            name: category.name,
            image: category.image_1920
                ? `data:image/png;base64,${category.image_1920}`
                : false,
            url: `/shop/category/${category.id}`,
        }));
    },

    /**
     * @override
     */
    _getMainPageUrl() {
        return "/shop";
    },
});

publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;
export default DynamicSnippetCategories;
