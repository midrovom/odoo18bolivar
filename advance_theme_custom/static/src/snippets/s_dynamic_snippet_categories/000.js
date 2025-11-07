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
    _getParentCategorySearchDomain() {
        const searchDomain = [];
        let parentCategoryId = this.$el.get(0).dataset.parentCategoryId;
        
        if (parentCategoryId && parentCategoryId !== 'all') {
            if (parentCategoryId === 'current') {
                parentCategoryId = undefined;
                
                // Try to get current category from URL or context
                this.trigger_up('main_object_request', {
                    callback: function (value) {
                        if (value.model === "product.public.category") {
                            parentCategoryId = value.id;
                        }
                    },
                });
                
                if (parentCategoryId) {
                    searchDomain.push(['parent_id', '=', parseInt(parentCategoryId)]);
                }
            } else if (parentCategoryId === 'root') {
                searchDomain.push(['parent_id', '=', false]);
            } else {
                searchDomain.push(['parent_id', '=', parseInt(parentCategoryId)]);
            }
        }
        
        return searchDomain;
    },

    /**
     * Gets the category names search domain
     *
     * @private
     */
    _getCategoryNamesSearchDomain() {
        const searchDomain = [];
        const categoryNames = this.$el.get(0).dataset.categoryNames;
        
        if (categoryNames) {
            const nameDomain = [];
            for (const categoryName of categoryNames.split(',')) {
                // Ignore empty names
                if (!categoryName.trim().length) {
                    continue;
                }
                
                if (nameDomain.length) {
                    nameDomain.unshift('|');
                }
                nameDomain.push(['name', 'ilike', categoryName.trim()]);
            }
            searchDomain.push(...nameDomain);
        }
        
        return searchDomain;
    },

    /**
     * Method to be overridden in child components in order to provide a search
     * domain if needed.
     * @override
     * @private
     */
    _getSearchDomain: function () {
        const searchDomain = this._super.apply(this, arguments);
        searchDomain.push(...this._getParentCategorySearchDomain());
        searchDomain.push(...this._getCategoryNamesSearchDomain());
        return searchDomain;
    },

    /**
     * @override
     * @private
     */
    _getMainPageUrl() {
        return "/shop";
    },
});

const DynamicSnippetCategoriesCard = publicWidget.Widget.extend({
    selector: '.o_carousel_category_card',
    
    init(root, options) {
        const parent = options.parent || root;
        this._super(parent, options);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    // You can add custom handlers here if needed
    // For example, tracking category clicks, hover effects, etc.
});

publicWidget.registry.dynamic_snippet_categories_card = DynamicSnippetCategoriesCard;
publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;

export default DynamicSnippetCategories;