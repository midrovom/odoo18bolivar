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
        // El modelo sobre el que filtramos ahora es categorías públicas
        this.modelNameFilter = 'product.public.category';
        this.categoryParents = {};
        this.orm = this.bindService("orm");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetches parent categories.
     * @private
     * @returns {Promise}
     */
    _fetchParentCategories: function () {
        return this.orm.searchRead("product.public.category", wUtils.websiteDomain(this), ["id", "name"]);
    },

    /**
     * @override
     * @private
     */
    _renderCustomXML: async function (uiFragment) {
        await this._super.apply(this, arguments);
        await this._renderParentCategorySelector(uiFragment);
    },

    /**
     * Renders the parent categories option selector content into the provided uiFragment.
     * @private
     * @param {HTMLElement} uiFragment
     */
    _renderParentCategorySelector: async function (uiFragment) {
        const parentCategories = await this._fetchParentCategories();
        for (let index in parentCategories) {
            this.categoryParents[parentCategories[index].id] = parentCategories[index];
        }
        const parentCategorySelectorEl = uiFragment.querySelector('[data-name="parent_category_opt"]');
        if (parentCategorySelectorEl) {
            return this._renderSelectUserValueWidgetButtons(parentCategorySelectorEl, this.categoryParents);
        }
    },

    /**
     * @override
     * @private
     */
    _setOptionsDefaultValues: function () {
        this._setOptionValue('parentCategoryId', 'all');
        this._setOptionValue('onlyWithImage', false);
        this._super.apply(this, arguments);
    },
});

options.registry.dynamic_snippet_categories = dynamicSnippetCategoriesOptions;

export default dynamicSnippetCategoriesOptions;
