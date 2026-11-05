# -*- coding: utf-8 -*-
"""Pure transformations of product data from multiple inventory/pricelist APIs.

No Odoo recordsets are used here; these functions can be tested independently.
"""
from collections import OrderedDict


def _clean(value):
    return str(value).strip() if value is not None else ''


def combine_catalogs(api_payloads, price_targets=None):
    """Combine (api_id, pricelist_id, payload) into unique SKU entries.

    Never SUM warehouse quantities that arrive from separate price-list APIs.
    The first source is authoritative for conflicting warehouse quantities,
    except that a nonzero StockTotal takes precedence over zero as a safeguard.
    A price belongs to its configured price list, not to a warehouse.

    When ``price_targets`` maps payload fields 1 and 2 to configured API IDs,
    Precio and Precio_2 are read from the *same product JSON*, independently of
    the endpoint they came from. /empresa/1 is preferred for Precio (public),
    /empresa/2 for Precio_2 (sale); other successful feeds are valid fallbacks.
    Stock is never summed across sources. In the legacy/no-target mode the old
    API-specific Precio behavior remains for backwards-compatible callers.
    """
    products = OrderedDict()
    warnings = []
    for api_id, pricelist_id, items in api_payloads:
        for row_number, original in enumerate(items, 1):
            if not isinstance(original, dict):
                warnings.append('API %s, registro %s: entrada no válida.' % (api_id, row_number))
                continue
            code = _clean(original.get('codigo'))
            if not code:
                warnings.append('API %s, registro %s: producto sin codigo.' % (api_id, row_number))
                continue
            if code not in products:
                row = dict(original)
                row['codigo'] = code
                row['_inventory_web_prices'] = OrderedDict()
                row['_inventory_web_price_sources'] = {}
                row['_inventory_web_sources'] = [api_id]
                row['_inventory_web_warehouse_sources'] = {}
                row['Bodegas'] = []
                products[code] = row
            row = products[code]
            if api_id not in row['_inventory_web_sources']:
                row['_inventory_web_sources'].append(api_id)
            for key, value in original.items():
                if key in ('codigo', 'Precio', 'Precio_2', 'StockTotal', 'Bodegas'):
                    continue
                if key not in row or row[key] is None or _clean(row[key]) == '':
                    row[key] = value
            if price_targets is None:
                # Compatibility with integrations using one price per endpoint.
                if 'Precio' in original and original['Precio'] is not None:
                    if pricelist_id in row['_inventory_web_prices']:
                        prev_api, prev_price = row['_inventory_web_prices'][pricelist_id]
                        if _clean(prev_price) != _clean(original['Precio']):
                            warnings.append('SKU %s: lista %s tiene precios diferentes en APIs %s y %s; '
                                            'se conserva el precio de API %s.' %
                                            (code, pricelist_id or 'venta', prev_api, api_id, prev_api))
                    else:
                        row['_inventory_web_prices'][pricelist_id] = (api_id, original['Precio'])
            else:
                # Both endpoints can contain both fields, so the final URL
                # segment no longer decides which JSON field supplies a price.
                # Store one value per field and route it to its *target* API.
                for field_number, field_name in ((1, 'Precio'), (2, 'Precio_2')):
                    if field_name not in original or original[field_name] is None:
                        continue
                    target_api_id = price_targets.get(field_number)
                    if not target_api_id:
                        # No configured price destination; leave product stock
                        # and other prices untouched rather than guessing.
                        continue
                    old = row['_inventory_web_prices'].get(field_number)
                    old_source_id = row['_inventory_web_price_sources'].get(field_number)
                    incoming = original[field_name]
                    if old is None:
                        row['_inventory_web_prices'][field_number] = (target_api_id, incoming)
                        row['_inventory_web_price_sources'][field_number] = api_id
                    else:
                        _old_target, old_price = old
                        if _clean(old_price) != _clean(incoming):
                            prefer_incoming = api_id == target_api_id and old_source_id != target_api_id
                            if prefer_incoming:
                                row['_inventory_web_prices'][field_number] = (target_api_id, incoming)
                                row['_inventory_web_price_sources'][field_number] = api_id
                            selected = api_id if prefer_incoming else old_source_id
                            warnings.append('SKU %s: %s distinto entre API %s y API %s; '
                                            'se utiliza el valor de API %s.' %
                                            (code, field_name, old_source_id, api_id, selected))
                        elif api_id == target_api_id:
                            # Source priority remains explicit and deterministic.
                            row['_inventory_web_price_sources'][field_number] = api_id
            if 'StockTotal' in original and original['StockTotal'] is not None:
                if 'StockTotal' not in row or row['StockTotal'] is None:
                    row['StockTotal'] = original['StockTotal']
                elif _clean(row['StockTotal']) != _clean(original['StockTotal']):
                    # A single stale/empty price-list feed must never zero out
                    # positive inventory from the other source.
                    try:
                        before = float(row['StockTotal'])
                        incoming = float(original['StockTotal'])
                    except (ValueError, TypeError):
                        before = incoming = None
                    if before is not None and incoming is not None and before == 0 < incoming:
                        row['StockTotal'] = original['StockTotal']
                    warnings.append('SKU %s: StockTotal distinto entre APIs; '
                                    'no se suman cantidades, se aplica el valor %s.' %
                                    (code, row['StockTotal']))
            warehouses = original.get('Bodegas')
            if warehouses is None:
                continue
            if not isinstance(warehouses, list):
                warnings.append('SKU %s, API %s: Bodegas no es una lista.' % (code, api_id))
                continue
            existing = { _clean(b.get('Bodega')).upper(): b
                         for b in row['Bodegas'] if isinstance(b, dict)}
            for wh in warehouses:
                if not isinstance(wh, dict):
                    warnings.append('SKU %s, API %s: bodega no válida.' % (code, api_id))
                    continue
                wh_code = _clean(wh.get('Bodega')).upper()
                if not wh_code:
                    warnings.append('SKU %s, API %s: código de bodega vacío.' % (code, api_id))
                    continue
                if wh_code in existing:
                    if _clean(existing[wh_code].get('StockBodega')) != _clean(wh.get('StockBodega')):
                        try:
                            old_qty = float(existing[wh_code].get('StockBodega'))
                            other_qty = float(wh.get('StockBodega'))
                        except (TypeError, ValueError):
                            old_qty = other_qty = None
                        # Never erase an explicitly positive quantity just
                        # because the other feed returned zero for that site.
                        if old_qty == 0 and other_qty is not None and other_qty > 0:
                            existing[wh_code]['StockBodega'] = wh['StockBodega']
                        warnings.append('SKU %s, bodega %s: stock diferente en APIs %s y %s; '
                                        'se conserva %s (prioridad a cantidad positiva sobre cero).' %
                                        (code, wh_code, row['_inventory_web_warehouse_sources'][wh_code],
                                         api_id, existing[wh_code]['StockBodega']))
                else:
                    new_wh = dict(wh)
                    new_wh['Bodega'] = wh_code
                    row['Bodegas'].append(new_wh)
                    existing[wh_code] = new_wh
                    row['_inventory_web_warehouse_sources'][wh_code] = api_id
    for row in products.values():
        # Preserve JSON field identity even when both prices use the SAME
        # source api_id (one endpoint carrying Precio and Precio_2).
        row['_inventory_web_price_fields'] = dict(row['_inventory_web_prices'])
        row['_inventory_web_prices'] = list(row['_inventory_web_prices'].values())
        row.pop('_inventory_web_warehouse_sources', None)
        if price_targets is None:
            row.pop('_inventory_web_price_sources', None)
    return list(products.values()), warnings
