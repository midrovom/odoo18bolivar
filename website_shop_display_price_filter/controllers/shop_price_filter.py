"""Adapt the native shop price filter to the price displayed in /shop.

Odoo 18 applies the original price filter to product.template.list_price and
calculates the slider limits with SQL over that same field.  The /shop cards,
however, receive their price from product.template._get_sales_prices(website).

We calculate prices with that same native API.  This deliberately keeps the
website's currency, pricelist, tax mapping, fiscal position, and any extensions
of the price computation in sync with the cards.
"""

from odoo.http import request, route
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleDisplayPriceFilter(WebsiteSale):
    """Extends the existing shop, without modifying website_sale files."""

    # A batch reduces work per ORM call on moderate-sized product catalogues.
    _DISPLAY_PRICE_BATCH_SIZE = 250

    def _get_search_options(self, *args, **kwargs):
        """Remember the user-entered prices in the *website* currency.

        Native Odoo converts the values before creating search options, since
        its price filter works against list_price in company currency.
        """
        options = super()._get_search_options(*args, **kwargs)
        options['_display_price_min'] = kwargs.get('min_price', 0.0)
        options['_display_price_max'] = kwargs.get('max_price', 0.0)
        return options

    def _shop_lookup_products(self, attrib_set, options, post, search, website):
        """Filter the same product set as Odoo by the card's actual price.

        First let the native search handle search text, category, tags,
        attributes and sorting, *without* its list_price constraints. Then
        evaluate the standard card prices in batches, computing limits before
        applying the requested price range.
        """
        clean_options = dict(options)
        display_min = clean_options.pop('_display_price_min', 0.0) or 0.0
        display_max = clean_options.pop('_display_price_max', 0.0) or 0.0

        if not website.is_view_active('website_sale.filter_products_price'):
            return super()._shop_lookup_products(
                attrib_set, clean_options, post, search, website,
            )

        # The standard domains in product.template._search_get_detail() use
        # list_price. Disabling only those bounds preserves the other filters.
        clean_options['min_price'] = 0.0
        clean_options['max_price'] = 0.0
        fuzzy_term, _, unfiltered_products = super()._shop_lookup_products(
            attrib_set, clean_options, post, search, website,
        )

        currency = website.currency_id
        accepted_ids = []
        prices_found = []

        for start in range(0, len(unfiltered_products), self._DISPLAY_PRICE_BATCH_SIZE):
            batch = unfiltered_products[start:start + self._DISPLAY_PRICE_BATCH_SIZE]
            # This is *exactly* the API used by the native /shop price cards:
            # values[template.id]['price_reduce'].
            batch_prices = batch._get_sales_prices(website)
            for product in batch:
                price_data = batch_prices.get(product.id)
                if not price_data or price_data.get('price_reduce') is None:
                    continue

                # Compare the monetary value at the same currency precision
                # as the amount displayed to the visitor.
                shown_price = currency.round(price_data['price_reduce'])
                prices_found.append(shown_price)
                if (not display_min or shown_price >= display_min) and (
                    not display_max or shown_price <= display_max
                ):
                    accepted_ids.append(product.id)

        available_min = min(prices_found) if prices_found else 0.0
        available_max = max(prices_found) if prices_found else 0.0
        # Request-scoped. Controllers must not store visitor data on `self`.
        request._shop_display_price_available = (available_min, available_max)

        # `browse` keeps the order given by Odoo's search engine.  Product
        # count, pagination and attribute facets subsequently use this subset.
        result = unfiltered_products.browse(accepted_ids)
        return fuzzy_term, len(result), result

    @route()
    def shop(self, page=0, category=None, search='', min_price=0.0,
             max_price=0.0, ppg=False, **post):
        """Replace only the slider limits calculated from list_price.

        `super()` builds the original /shop page and all existing facets. Its
        search result was already corrected by `_shop_lookup_products()`.
        """
        result = super().shop(
            page=page, category=category, search=search,
            min_price=min_price, max_price=max_price, ppg=ppg, **post,
        )
        available = getattr(request, '_shop_display_price_available', None)
        values = getattr(result, 'qcontext', None)
        if available is None or not isinstance(values, dict):
            return result

        available_min, available_max = available
        # In native Odoo the selected values are represented by min_price /
        # max_price in the rendered template, and zeros mean 'no constraint'.
        try:
            selected_min = float(min_price or 0)
        except (TypeError, ValueError):
            selected_min = 0.0
        try:
            selected_max = float(max_price or 0)
        except (TypeError, ValueError):
            selected_max = 0.0

        values.update({
            'available_min_price': round(available_min, 2),
            'available_max_price': round(available_max, 2),
            'min_price': selected_min or available_min,
            'max_price': selected_max or available_max,
        })
        return result
