from odoo import api, models
from odoo.osv import expression

class WebsiteSnippetFilterCategory(models.Model):
    _inherit = 'website.snippet.filter'

    @api.model
    def _get_categories(self, mode, **kwargs):
        """Dispatcher para categorías públicas."""
        res = super()._get_products(mode, **kwargs)

        handler = getattr(self, '_get_categories_%s' % mode, self._get_categories_all)
        website = self.env['website'].get_current_website()
        search_domain = self.env.context.get('search_domain')
        limit = self.env.context.get('limit')

        domain = expression.AND([
            [('website_published', '=', True)],
            website.website_domain(),
            [('company_id', 'in', [False, website.company_id.id])],
            search_domain or [],
        ])

        categories = handler(website, limit, domain, **kwargs)
        return categories or res

    def _get_categories_all(self, website, limit, domain, **kwargs):
        """Devuelve todas las categorías publicadas en el sitio web"""
        return self.env['product.public.category'].search(domain, limit=limit)

    def _get_categories_related(self, website, limit, domain, product_template_id=None, **kwargs):
        """Devuelve las categorías públicas relacionadas con un producto"""
        categories = self.env['product.public.category']
        current_template = self.env['product.template'].browse(
            product_template_id and int(product_template_id)
        ).exists()
        if current_template:
            included_categories = current_template.public_categ_ids
            if included_categories:
                domain = expression.AND([
                    domain,
                    [('id', 'in', included_categories.ids)],
                ])
                categories = self.env['product.public.category'].search(domain, limit=limit)
        return categories
