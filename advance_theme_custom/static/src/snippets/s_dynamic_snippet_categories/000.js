/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import DynamicSnippetCarousel from "@website/snippets/s_dynamic_snippet_carousel/000";
import { rpc } from "@web/core/network/rpc";

const DynamicSnippetCategories = DynamicSnippetCarousel.extend({
    selector: '.s_dynamic_snippet_categories',

    /**
     * Build the dynamic domain to search categories
     *
     * @override
     */
    _getSearchDomain() {
        const domain = this._super(...arguments);

        // Recoger opción desde dataset (si activaste checkbox Only Root)
        const onlyRoot = this.el.dataset.onlyRoot === "true";
        if (onlyRoot) {
            domain.push(["parent_id", "=", false]);
        }

        return domain;
    },

    /**
     * RPC to the backend, replace products by categories
     *
     * @override
     */
    async _fetchData() {
        const domain = this._getSearchDomain();
        return rpc("/website/snippet/categories", { domain });
    },

    /**
     * Render categories into the carousel
     *
     * @override
     */
    _renderData(categories) {
        const $container = this.$el.find('.carousel-item.active .row');
        $container.empty();

        for (const cat of categories) {
            $container.append(`
                <div class="d-flex flex-grow-0 flex-shrink-0 col-3">
                    <div class="o_carousel_product_card bg-transparent w-100 card border-0 text-center">
                        <a class="stretched-link" href="${cat.url}">
                            <div class="overflow-hidden rounded">
                                <img class="card-img-top o_img_product_square o_img_product_cover h-auto"
                                     loading="lazy"
                                     src="${cat.image}"/>
                            </div>
                        </a>
                        <div class="o_carousel_product_card_body p-3">
                            <div class="h6 card-title mb-0">${cat.name}</div>
                        </div>
                    </div>
                </div>
            `);
        }
    },
});

publicWidget.registry.dynamic_snippet_categories = DynamicSnippetCategories;

export default DynamicSnippetCategories;
