"""Order all shop search results by real available stock before pagination.

Odoo 18's website_sale controller paginates the product.template result set
*after* calling _shop_lookup_products.  Therefore the inventory sorting must
happen here, not in a QWeb template or on the already paginated page.
"""

from collections import defaultdict

from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


STOCK_SORT_DESC = 'stock_desc'
STOCK_SORT_ASC = 'stock_asc'
STOCK_SORT_VALUES = (STOCK_SORT_DESC, STOCK_SORT_ASC)


class WebsiteSaleStockOrder(WebsiteSale):
    def _get_search_order(self, post):
        """Stock sort is not a SQL field; use the standard sequence as tie-breaker.

        The native website search expects an ORM order expression.  `stock_desc`
        and `stock_asc` are logical sort keys, so never send them to the ORM.
        """
        selected_order = post.get('order') or request.website.shop_default_sort
        if selected_order in STOCK_SORT_VALUES:
            return super()._get_search_order({**post, 'order': 'website_sequence asc'})
        return super()._get_search_order(post)

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        fuzzy_search_term, product_count, products = super()._shop_lookup_products(
            attrib_set, options, post, search, website,
        )

        selected_order = post.get('order') or website.shop_default_sort
        if selected_order not in STOCK_SORT_VALUES or not products:
            return fuzzy_search_term, product_count, products

        # Match the same warehouse/company context as website_sale_stock's
        # display quantity: free_qty = on-hand - reserved quantities.
        # For a website without a specific warehouse, use Odoo's standard
        # company-warehouse location domain.
        company = website.company_id
        variants_model = request.env['product.product'].sudo().with_company(company)
        variants_model = variants_model.with_context(warehouse_id=website.warehouse_id.id)
        location_domain, _in_domain, _out_domain = variants_model._get_domain_locations()

        # One grouped SQL query via the Odoo ORM, not a per-product query.
        # Restrict the inventory calculation to the website's catalog and
        # warehouse locations.  Variant quantities are summed by template.
        quantities = request.env['stock.quant'].sudo().with_company(company)._read_group(
            domain=[
                ('product_id.product_tmpl_id', 'in', products.ids),
            ] + location_domain,
            groupby=['product_id'],
            aggregates=['quantity:sum', 'reserved_quantity:sum'],
        )
        qty_by_template = defaultdict(float)
        for variant, quantity, reserved_quantity in quantities:
            # A service or non-tracked item is not a product with stock.
            if variant.is_storable:
                qty_by_template[variant.product_tmpl_id.id] += quantity - reserved_quantity

        # `.sorted` preserves the parent recordset order for ties (featured
        # sequence). It works on the full result set, before the shop pager.
        products = products.sorted(
            key=lambda product: qty_by_template[product.id],
            reverse=(selected_order == STOCK_SORT_DESC),
        )
        return fuzzy_search_term, product_count, products
