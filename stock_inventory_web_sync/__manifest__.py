# -*- coding: utf-8 -*-
{
    'name': 'Inventario Web API - Productos y Bodegas',
    'summary': 'Un endpoint: dos precios por bodega, con listas de Odoo ya existentes',
    'version': '18.0.1.17.0',
    'category': 'Inventory/Inventory',
    'author': 'Desarrollo 1',
    'license': 'LGPL-3',
    'depends': ['base', 'product', 'stock', 'sale_stock', 'api_administrator'],
    'data': [
        'security/ir.model.access.csv',
        'views/inventory_web_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
