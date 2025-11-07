/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import s_dynamic_snippet_carousel_options from "@website/snippets/s_dynamic_snippet_carousel/options";
import wUtils from "@website/js/utils";

const dynamicSnippetCategoriesOptions = s_dynamic_snippet_carousel_options.extend({

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.modelNameFilter = 'product.public.category';
        this.productCategories = {};
        this.orm = this.bindService("orm");
    },

    /**
     * @private
     */
    _fetchCategories: function () {
        return this.orm.searchRead("product.public.category", wUtils.websiteDomain(this), ["id", "name"]);
    },

    /**
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        await this._super.apply(this, arguments);
        await this._renderCategorySelector(uiFragment);
    },

    /**
     * @private
     */
    _renderCategorySelector: async function (uiFragment) {
        const categories = await this._fetchCategories();
        for (let category of categories) {
            this.productCategories[category.id] = category;
        }
        const categorySelectorEl = uiFragment.querySelector('[data-name="category_opt"]');
        return this._renderSelectUserValueWidgetButtons(categorySelectorEl, this.productCategories);
    },
});

options.registry.dynamic_snippet_categories = dynamicSnippetCategoriesOptions;
export default dynamicSnippetCategoriesOptions;
