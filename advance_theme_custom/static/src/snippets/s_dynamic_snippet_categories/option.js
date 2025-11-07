/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";
import s_dynamic_snippet_carousel_options from "@website/snippets/s_dynamic_snippet_carousel/options";

const dynamicSnippetCategoriesOptions = s_dynamic_snippet_carousel_options.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.modelNameFilter = 'product.public.category';
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     * @private
     */
    _setOptionsDefaultValues: function () {
        this._setOptionValue('templateKey', 'advance_theme_custom.dynamic_filter_template_category_borderless_1');
        this._setOptionValue('parentCategoryId', 'all');
        this._setOptionValue('categoryNames', '');
        this._super.apply(this, arguments);
    },
});

options.registry.dynamic_snippet_categories = dynamicSnippetCategoriesOptions;
export default dynamicSnippetCategoriesOptions;
