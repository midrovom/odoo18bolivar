/** @odoo-module */

import DynamicSnippet from "@website/snippets/s_dynamic_snippet/000";

const DynamicSnippetProductCategories = DynamicSnippet.extend({
    selector: ".s_dynamic_snippet_product_categories",

    // Datos reales
    async _fetch_records() {
        const domain = []; // si necesitas filtrar agrega dominio aquí

        const categories = await this._rpc({
            model: "product.public.category",
            method: "search_read",
            domain,
            fields: ["id", "name", "image_1920", "parent_id"],
            limit: this.props.limit || 6,
        });

        return categories;
    },

    // Datos de preview
    _get_default_data() {
        return [
            { name: "Categoría A", image_1920: false },
            { name: "Categoría B", image_1920: false },
            { name: "Categoría C", image_1920: false },
        ];
    },
});

export default DynamicSnippetProductCategories;
