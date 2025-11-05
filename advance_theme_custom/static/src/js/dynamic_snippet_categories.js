import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";

export class DynamicSnippetCategories extends DynamicSnippetCarousel {
    static selector = ".s_dynamic_snippet_categories";

    getSearchDomain() {
        const categoryIds = this.el.dataset.categoryIds;
        if (categoryIds) {
            const parsed = JSON.parse(categoryIds);
            if (parsed.length) {
                return [["id", "in", parsed.map(c => c.id)]];
            }
        }
        return [];
    }

    getRpcParameters() {
        return Object.assign(super.getRpcParameters(...arguments), {
            categoryIds: this.el.dataset.categoryIds,
        });
    }
}

registry.category("public.interactions").add("advance_theme_custom.dynamic_snippet_categories", DynamicSnippetCategories);
registry.category("public.interactions.edit").add("advance_theme_custom.dynamic_snippet_categories", {
    Interaction: DynamicSnippetCategories,
});
