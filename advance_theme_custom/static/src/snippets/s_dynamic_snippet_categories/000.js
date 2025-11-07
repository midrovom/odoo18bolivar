/** @odoo-module **/

import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";

const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_categories',

    /**
     * Override to search public categories
     */
    _getSearchDomain() {
        return []; // no filtros por ahora
    },

    /**
     * Override RPC target
     */
    async _getRecords() {
        return await this.rpc("/web/dataset/search_read", {
            model: "product.public.category",
            fields: ["id", "display_name", "image_1920"],
            domain: this._getSearchDomain(),
            limit: parseInt(this.el.dataset.numberOfRecords) || 12,
        });
    },

    /**
     * Build dataset for template render
     */
    _getRecordRenderData(record) {
        return {
            name: record.display_name,
            image: `/web/image/product.public.category/${record.id}/image_1920`,
            url: `/shop/category/${record.id}`,
        };
    },
});

export default DynamicSnippetCategories;
