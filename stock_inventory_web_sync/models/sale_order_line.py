# -*- coding: utf-8 -*-
"""Precio de una misma lista según la bodega elegida en la venta (Odoo 16).

Odoo no tiene reglas estándar de product.pricelist.item filtradas por almacén.
La lista configurada conserva Precio_2 como base; en sale.order.line
se elige Precio para las bodegas de la API seleccionadas y Precio_2
para las demás. No altera el precio de los otros catálogos ni APIs.
"""

from odoo import api, fields, models

from .warehouse_price_routing import price_field_for_warehouse


def _inventory_web_sale_price_dependencies(model):
    """Include stock_api_assing line warehouse only when that addon exists."""
    dependencies = ['product_id', 'product_uom', 'product_uom_qty',
                    'order_id.warehouse_id', 'order_id.pricelist_id']
    if 'warehouse_id' in model._fields:
        dependencies.append('warehouse_id')
    return dependencies


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _inventory_web_sale_warehouse(self):
        self.ensure_one()
        # stock_api_assing agrega bodega en cada línea. Si no existe o está
        # vacía, usar el almacén de la orden proporcionado por sale_stock.
        if 'warehouse_id' in self._fields and self.warehouse_id:
            return self.warehouse_id
        if self.order_id and 'warehouse_id' in self.order_id._fields:
            return self.order_id.warehouse_id
        return self.env['stock.warehouse']

    def _inventory_web_warehouse_price(self):
        """Return (price, field) or (None, None), zero is a valid API price.

        Applies only to the *same* company and pricelist configured in API
        Administrator. Other pricelists keep Odoo's standard price logic.
        """
        self.ensure_one()
        if not self.order_id or not self.product_id or not self.order_id.pricelist_id:
            return None, None
        tmpl = self.product_id.product_tmpl_id
        if not tmpl.inventory_web_last_sync:
            return None, None
        warehouse = self._inventory_web_sale_warehouse()
        if not warehouse or warehouse.company_id != self.order_id.company_id:
            return None, None
        api_record = self.env['api.administrator'].sudo().search([
            ('inventory_web_products_enabled', '=', True),
            ('status', '=', 'A'),
            ('company_id', '=', self.order_id.company_id.id),
            ('price_list_id', '=', self.order_id.pricelist_id.id),
        ], order='id asc', limit=1)
        if not api_record:
            return None, None
        selected_ids = set(api_record.inventory_web_price_warehouse_ids.ids)
        # Un producto en varias bodegas puede tener 2 precios distintos:
        # NO se decide globalmente por SKU; se resuelve para la bodega actual.
        field_name = price_field_for_warehouse(
            warehouse.id, selected_ids, self.product_id.inventory_web_warehouse_ids.ids)
        is_public = field_name == 'Precio'
        price = (tmpl.inventory_web_price_1 if is_public
                 else tmpl.inventory_web_price_2)
        company_currency = self.order_id.company_id.currency_id
        pricelist_currency = self.order_id.pricelist_id.currency_id
        if company_currency != pricelist_currency:
            sale_date = self.order_id.date_order
            date = sale_date.date() if sale_date else fields.Date.context_today(self)
            price = company_currency._convert(
                price, pricelist_currency, self.order_id.company_id, date)
        if self.product_uom and self.product_id.uom_id != self.product_uom:
            price = self.product_id.uom_id._compute_price(price, self.product_uom)
        return price, field_name

    def _get_display_price(self):
        self.ensure_one()
        price, _field = self._inventory_web_warehouse_price()
        if price is not None:
            return price
        return super()._get_display_price()

    @api.depends(_inventory_web_sale_price_dependencies)
    def _compute_price_unit(self):
        # Calling super preserves taxes, fiscal positions, invoiced quantities
        # and all the standard price calculation behavior of sale.order.line.
        super()._compute_price_unit()

    @api.depends(_inventory_web_sale_price_dependencies)
    def _compute_discount(self):
        super()._compute_discount()
        for line in self:
            price, field = line._inventory_web_warehouse_price()
            if field is not None:
                # We are selecting a final explicit price from the API, not
                # creating a second discount on top of that price.
                line.discount = 0.0

