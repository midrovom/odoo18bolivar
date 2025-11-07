/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";

const DynamicSnippetCategories = DynamicSnippet.extend({
    selector: ".s_dynamic_snippet_categories",
    disabledInEditableMode: false,

    /**
     * Override: Return categories instead of products
     */
    _getSearchDomain() {
        const domain = [];
        if (this.el.dataset.onlyRoot === "true") {
            domain.push(["parent_id", "=", false]);
        }
        return domain;
    },

    /**
     * Fetch data for product.public.category instead of product.product
     */
    async _fetchRecords() {
        const domain = this._getSearchDomain();
        const records = await this.rpc("/web/dataset/call_kw/product.public.category/search_read", {
            model: "product.public.category",
            method: "search_read",
            args: [domain],
            kwargs: { fields: ["id", "name", "display_name", "image_1920"] },
        });
        return records;
    },
});

publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;
