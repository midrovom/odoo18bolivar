/** @odoo-module **/

import options from "@web_editor/js/editor/snippets.options";

const DynamicSnippetCategoriesOptions = options.Class.extend({
    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    /**
     * @override
     */
    async _renderCustomXML(uiFragment) {
        await this._super(...arguments);
        await this._renderOnlyRootToggle(uiFragment);
    },

    /**
     * Render toggle for onlyRoot option
     * @param {HTMLElement} uiFragment
     */
    async _renderOnlyRootToggle(uiFragment) {
        const toggleEl = uiFragment.querySelector('[data-name="only_root_opt"]');
        if (toggleEl) {
            this._renderToggleWidget(toggleEl, {
                value: this.$target[0].dataset.onlyRoot === "true",
                onChange: (val) => {
                    this._setOptionValue("onlyRoot", val ? "true" : "false");
                },
            });
        }
    },

    /**
     * @override
     */
    _setOptionsDefaultValues() {
        this._setOptionValue("onlyRoot", "false");
        this._super(...arguments);
    },
});

options.registry.dynamic_snippet_categories = DynamicSnippetCategoriesOptions;

export default DynamicSnippetCategoriesOptions;
