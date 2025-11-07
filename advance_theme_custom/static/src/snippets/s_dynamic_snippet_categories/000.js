/** @odoo-module **/

import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";
import { xmlrpc } from "@web/core/network/rpc_service";

const DynamicSnippetProductCategories = DynamicSnippet.extend({
    selector: '.s_dynamic_snippet_product_categories',

    async _fetch_records() {
        const limit = this._getLimit();
        const records = await xmlrpc("/web/dataset/call_kw", {
            model: "product.public.category",
            method: "search_read",
            args: [
                [], // sin filtros → traer todas las categorías públicas
                ['id', 'display_name', 'image_1920'],
            ],
            kwargs: { limit },
        });
        return records;
    },
});

export default DynamicSnippetProductCategories;
