# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    inventory_web_line = fields.Char(string='Línea API', copy=False)
    inventory_web_brand = fields.Char(string='Marca API', copy=False)
    inventory_web_format = fields.Char(string='Formato API', copy=False)
    inventory_web_price_1 = fields.Float(
        string='Precio público API', digits='Product Price', copy=False,
        help='Campo Precio del JSON. Se actualiza en product.template.list_price (precio público).',
    )
    inventory_web_price_2 = fields.Float(
        string='Precio mayorista API', digits='Product Price', copy=False,
        help='Campo Precio_2 del JSON; se aplica en la lista de precios existente seleccionada en API Administrator, sin crear una nueva.',
    )
    inventory_web_mxpallets = fields.Float(string='Máximo por pallet API', copy=False)
    inventory_web_mxplaca = fields.Float(string='Máximo por placa API', copy=False)
    inventory_web_mxcaja = fields.Float(string='Máximo por caja API', copy=False)
    inventory_web_stock_total = fields.Float(
        string='StockTotal API (referencia)',
        help='StockTotal reportado por la API; no reemplaza el stock calculado de Odoo.',
        copy=False,
    )
    inventory_web_last_sync = fields.Datetime(string='Última sincronización API', copy=False)
    inventory_web_log_ids = fields.One2many(
        'stock.inventory.web.product.log', 'product_tmpl_id',
        string='Historial de sincronización API', readonly=True,
        help='Registro por producto de cada ejecución manual o de cron, con cambios de precio y cantidades por bodega.',
    )


    inventory_web_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        string='Bodegas vinculadas por API',
        compute='_compute_inventory_web_warehouse_ids',
        help='Bodegas identificadas para las variantes de este producto mediante stock.warehouse.code.',
    )

    @api.depends('product_variant_ids.inventory_web_warehouse_ids')
    def _compute_inventory_web_warehouse_ids(self):
        for tmpl in self:
            tmpl.inventory_web_warehouse_ids = tmpl.product_variant_ids.mapped(
                'inventory_web_warehouse_ids'
            )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    inventory_web_log_ids = fields.One2many(
        'stock.inventory.web.product.log', 'product_id',
        string='Historial de sincronización API', readonly=True,
    )

    inventory_web_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'product_product_inventory_web_warehouse_rel',
        'product_id', 'warehouse_id',
        string='Bodegas vinculadas por API',
        readonly=True, copy=False,
        help='Se relacionan por Bodegas[].Bodega con stock.warehouse.code de la empresa '
             'asignada en api_administrator. Una variante puede estar en varios almacenes.',
    )
