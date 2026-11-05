# -*- coding: utf-8 -*-
"""Pure mapping from a selected sale warehouse to the JSON price field."""


def price_field_for_warehouse(warehouse_id, selected_ids, product_warehouse_ids):
    """Return Precio only when this SKU belongs to a selected warehouse.

    A zero inventory quantity still counts as a declared relationship.
    For all other warehouses return Precio_2. SKU prices are never summed.
    """
    return ('Precio' if warehouse_id in selected_ids and
            warehouse_id in product_warehouse_ids else 'Precio_2')
