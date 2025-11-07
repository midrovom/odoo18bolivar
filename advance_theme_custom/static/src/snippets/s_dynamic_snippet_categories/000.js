/** @odoo-module **/

import { DynamicSnippet } from "@website/s_dynamic_snippet/000";

export class DynamicSnippetCategories extends DynamicSnippet {

    async _fetchData() {
        const onlyRoot = this.props.onlyRoot === "true";
        const domain = onlyRoot ? [["parent_id", "=", false]] : [];

        return this.rpc("/website/snippet/categories", { domain });
    }

    _renderData(categories) {
        const container = this.el.querySelector(".carousel-inner .carousel-item .row");
        container.innerHTML = "";

        for (const cat of categories) {
            container.insertAdjacentHTML("beforeend", `
                <div class="d-flex flex-grow-0 flex-shrink-0 col-3">
                    <div class="o_carousel_product_card bg-transparent w-100 card border-0 text-center">
                        <a class="stretched-link" href="${cat.url}">
                            <div class="overflow-hidden rounded">
                                <img src="${cat.image}" class="card-img-top"/>
                            </div>
                        </a>
                        <div class="o_carousel_product_card_body p-3">
                            <div class="h6 card-title mb-0">${cat.name}</div>
                        </div>
                    </div>
                </div>
            `);
        }
    }
}

DynamicSnippet.registry['dynamic_snippet_categories'] = DynamicSnippetCategories;
