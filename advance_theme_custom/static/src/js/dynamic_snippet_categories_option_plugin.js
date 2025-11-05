import { DYNAMIC_SNIPPET_CAROUSEL } from "@website/builder/plugins/options/dynamic_snippet_carousel_option_plugin";
import { setDatasetIfUndefined } from "@website/builder/plugins/options/dynamic_snippet_option_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class DynamicSnippetCategoriesOptionPlugin extends Plugin {
    static id = "dynamicSnippetCategoriesOption";
    static dependencies = ["dynamicSnippetCarouselOption"];
    selector = ".s_dynamic_snippet_categories";
    modelNameFilter = "product.public.category";

    resources = {
        builder_options: withSequence(DYNAMIC_SNIPPET_CAROUSEL, {
            OptionComponent: null,
            props: {
                modelNameFilter: this.modelNameFilter,
                fetchCategories: this.fetchCategories.bind(this),
            },
            selector: this.selector,
        }),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        this.categories = undefined;
    }

    async onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(this.selector)) {
            setDatasetIfUndefined(snippetEl, "categoryIds", "[]");
            setDatasetIfUndefined(snippetEl, "numberOfRecords", "8");
            setDatasetIfUndefined(snippetEl, "carouselInterval", "5000");
            setDatasetIfUndefined(snippetEl, "carouselSlideBy", "1");
        }
    }

    async fetchCategories() {
        if (!this.categories) {
            const websiteDomain = [
                "|",
                ["website_id", "=", false],
                ["website_id", "=", this.services.website.currentWebsite.id],
            ];
            this.categories = this.services.orm.searchRead(
                "product.public.category",
                websiteDomain,
                ["id", "name"],
                { order: "name asc" }
            );
        }
        return this.categories;
    }
}

registry.category("website-plugins").add(DynamicSnippetCategoriesOptionPlugin.id, DynamicSnippetCategoriesOptionPlugin);
