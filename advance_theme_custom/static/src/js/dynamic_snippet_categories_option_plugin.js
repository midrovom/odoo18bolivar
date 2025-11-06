import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";
import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";

class DynamicSnippetCategoriesOptionPlugin extends Plugin {
    static id = "dynamicSnippetCategoriesOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    selector = ".s_dynamic_snippet_categories";
    modelNameFilter = "product.public.category";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET_CAROUSEL, {
            OptionComponent: DynamicSnippetCategoriesOption,
            props: {
                modelNameFilter: this.modelNameFilter,
            },
            selector: this.selector,
        }),
        dynamic_snippet_template_updated: this.onTemplateUpdated.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            for (const [optionName, value] of [
                ["categoryId", "all"],
            ]) {
                setDatasetIfUndefined(snippetEl, optionName, value);
            }
            await this.dependencies.dynamicSnippetCarouselOption.setOptionsDefaultValues(
                snippetEl,
                this.modelNameFilter,
                []
            );
        }
    }

    onTemplateUpdated({ el, template }) {
        if (el.matches(this.selector)) {
            this.dependencies.dynamicSnippetCarouselOption.updateTemplateSnippetCarousel(el, template);
        }
    }
}

export class DynamicSnippetCategories extends DynamicSnippetCarousel {
    static selector = ".s_dynamic_snippet_categories";

    getSearchDomain() {
        const searchDomain = [];
        let categoryId = this.el.dataset.categoryId;
        if (categoryId && categoryId !== "all") {
            searchDomain.push(["id", "=", parseInt(categoryId)]);
        }
        const categoryNames = this.el.dataset.categoryNames;
        if (categoryNames) {
            for (const name of categoryNames.split(",")) {
                if (name.length) {
                    searchDomain.push(["name", "ilike", name]);
                }
            }
        }
        return searchDomain;
    }
}

registry.category("website-plugins").add(DynamicSnippetCategoriesOptionPlugin.id, DynamicSnippetCategoriesOptionPlugin);
registry.category("public.interactions").add("website_sale.dynamic_snippet_categories", DynamicSnippetCategories);
registry.category("public.interactions.edit").add("website_sale.dynamic_snippet_categories", { Interaction: DynamicSnippetCategories });
