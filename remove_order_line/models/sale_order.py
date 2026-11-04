# -*- coding: utf-8 -*-
"""Eliminar líneas de cantidad cero justo antes de exportar a Radis."""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _remove_zero_qty_lines(self):
        for order in self:
            zero_lines = order.order_line.filtered(
                lambda line: not line.display_type and line.product_uom_qty == 0
            )
            if zero_lines:
                _logger.info('Eliminando %d líneas de cantidad cero de %s', len(zero_lines), order.name)
                zero_lines.unlink()
        return True

    def action_export_to_radis(self):
        self._remove_zero_qty_lines()
        return super().action_export_to_radis()
