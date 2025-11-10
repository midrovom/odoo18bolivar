# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import Counter
from functools import partial

from odoo import _, api, fields, models
from odoo.osv import expression


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    category_dynamic = fields.Boolean(
        string="About public product categories",
        help="True only for filters that relate to public product categories",
    )

    def _prepare_values(self, limit=None, **kwargs):
        website = self.env['website'].get_current_website()
        if self.model_name == 'product.public.category' and not website.has_ecommerce_access():
            return []
        category_limit = limit or self.limit
        res = super(
            WebsiteSnippetFilter,
            self.with_context(category_limit=category_limit),
        )._prepare_values(limit=limit, **kwargs)
        return res

    def _get_hardcoded_sample(self, model):
        samples = super()._get_hardcoded_sample(model)
        if model._name == 'product.public.category':
            data = [{
                'image_512': b'/product/static/img/category_chairs.jpg',
                'display_name': _("Chairs"),
            }, {
                'image_512': b'/product/static/img/category_lamps.jpg',
                'display_name': _("Lamps"),
            }, {
                'image_512': b'/product/static/img/category_storage.jpg',
                'display_name': _("Storage"),
            }, {
                'image_512': b'/product/static/img/category_tables.jpg',
                'display_name': _("Tables"),
            }]
            merged = []
            for index in range(max(len(samples), len(data))):
                merged.append({**samples[index % len(samples)], **data[index % len(data)]})
            samples = merged
        return samples

    def _filter_records_to_values(self, records, is_sample=False):
        res_categories = super()._filter_records_to_values(records, is_sample)
        if self.model_name == 'product.public.category':
            for res_category in res_categories:
                category = res_category.get('_record')
                if not is_sample:
                    res_category.update({
                        'product_count': len(category.product_tmpl_ids),
                        'url': '/shop/category/%s' % category.id,
                    })
                else:
                    res_category.update({'is_sample': True})
        return res_categories

    @api.model
    def _get_categories(self, mode, **kwargs):
        dynamic_filter = self.env.context.get('dynamic_filter')
        website = self.env['website'].get_current_website()
        search_domain = self.env.context.get('search_domain')
        limit = self.env.context.get('limit')
        domain = expression.AND([
            [('website_published', '=', True)],
            website.website_domain(),
            [('company_id', 'in', [False, website.company_id.id])],
            search_domain or [],
        ])
        categories = self.env['product.public.category'].search(domain, limit=limit)
        return dynamic_filter._filter_records_to_values(categories, is_sample=False)
