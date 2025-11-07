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
        this.categoryRecords = {};
        this.orm = this.bindService("orm");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
    _setOptionsDefaultValues: function () {
        this._setOptionValue('templateKey', 'advance_theme_custom.dynamic_filter_template_product_public_category_borderless_1');
        this._setOptionValue('onlyRoot', false); // valor por defecto del checkbox personalizado
        this._super.apply(this, arguments);
    },

    /**
     * @private
     * @returns {Promise}
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
     * Renders the category selector (if needed).
     * @private
     * @param {HTMLElement} uiFragment
     */
    _renderCategorySelector: async function (uiFragment) {
        const categories = await this._fetchCategories();
        for (const category of categories) {
            this.categoryRecords[category.id] = category;
        }
        const selectorEl = uiFragment.querySelector('[data-name="category_opt"]');
        if (selectorEl) {
            return this._renderSelectUserValueWidgetButtons(selectorEl, this.categoryRecords);
        }
    },
});

options.registry.dynamic_snippet_categories = dynamicSnippetCategoriesOptions;
export default dynamicSnippetCategoriesOptions;
