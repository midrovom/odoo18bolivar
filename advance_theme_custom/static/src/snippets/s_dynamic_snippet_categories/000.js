/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";

const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_categories',

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets the parent category search domain
     *
     * @private
     */
    _getParentCategoryDomain() {
        const searchDomain = [];
        let parentCategoryId = this.$el.get(0).dataset.parentCategoryId;
        if (parentCategoryId && parentCategoryId !== 'all') {
            if (parentCategoryId === 'current') {
                // Si el dataset dice "current", intentamos obtener la categoría actual
                const categoryField = document.querySelector("#category_details .category_id");
                if (categoryField) {
                    parentCategoryId = parseInt(categoryField.value);
                }
            }
            if (parentCategoryId) {
                searchDomain.push(['parent_id', '=', parseInt(parentCategoryId)]);
            }
        }
        return searchDomain;
    },

    /**
     * Gets the tag search domain
     *
     * @private
     */
    _getTagSearchDomain() {
        const searchDomain = [];
        let categoryTagIds = this.$el.get(0).dataset.categoryTagIds;
        categoryTagIds = categoryTagIds ? JSON.parse(categoryTagIds) : [];
        if (categoryTagIds.length) {
            searchDomain.push(['tag_ids', 'in', categoryTagIds.map(tag => tag.id)]);
        }
        return searchDomain;
    },

    /**
     * Gets the name search domain
     *
     * @private
     */
    _getNameSearchDomain() {
        const searchDomain = [];
        const categoryNames = this.$el.get(0).dataset.categoryNames;
        if (categoryNames) {
            for (const name of categoryNames.split(',')) {
                if (!name.length) {
                    continue;
                }
                if (searchDomain.length) {
                    searchDomain.unshift('|');
                }
                searchDomain.push(['name', 'ilike', name]);
            }
        }
        return searchDomain;
    },

    /**
     * Override: build the full search domain for categories
     *
     * @override
     * @private
     */
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        searchDomain.push(...this._getParentCategoryDomain());
        searchDomain.push(...this._getTagSearchDomain());
        searchDomain.push(...this._getNameSearchDomain());
        if (this.el.dataset.onlyWithImage === 'true') {
            searchDomain.push(['image_1920', '!=', false]);
        }
        return searchDomain;
    },

    /**
     * @override
     * @private
     */
    _getMainPageUrl() {
        return "/shop/categories";
    },
});

publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;

export default DynamicSnippetCategories;
