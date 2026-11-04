# -*- coding: utf-8 -*-
import logging

from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _validate_stock_from_radis(self):
        for order in self:
            insufficient_products = []
            for line in order.order_line.filtered(
                lambda l: l.product_id and not l.display_type and l.product_uom_qty > 0
            ):
                warehouse = line.warehouse_id or order.warehouse_id
                sku = line.product_id.default_code
                if not sku:
                    continue
                if not warehouse:
                    raise ValidationError(_('Debe seleccionar una bodega para %s.') % line.product_id.display_name)
                result = self.env['api.administrator'].call_api_stock(
                    api_name='consultar_stock', method='get', sku=sku,
                    warehouse=warehouse.code, company_id=order.company_id.id,
                )
                data = result.get('data') or []
                if not isinstance(data, list):
                    raise ValidationError(_('La respuesta de stock de %s no tiene el formato esperado.') % sku)
                try:
                    stock = float(data[0].get('Stock', 0) or 0) if data else 0.0
                except (TypeError, ValueError, AttributeError) as exc:
                    raise ValidationError(_('Stock inválido en API para %s: %s') % (sku, exc)) from exc
                _logger.info('Radis SKU=%s bodega=%s solicitado=%s disponible=%s',
                             sku, warehouse.code, line.product_uom_qty, stock)
                if stock < line.product_uom_qty:
                    insufficient_products.append(_(
                        '%(product)s | Solicitado: %(qty)s | Disponible: %(stock)s'
                    ) % {'product': line.product_id.display_name, 'qty': line.product_uom_qty, 'stock': stock})
            if insufficient_products:
                raise ValidationError(_(
                    'Los siguientes productos no tienen stock suficiente:\n\n%s'
                ) % '\n'.join(insufficient_products))
        return True

    def action_export_to_radis(self):
        self._validate_stock_from_radis()
        return super().action_export_to_radis()
