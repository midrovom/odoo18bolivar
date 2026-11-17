{
    'name': 'Website - Ordenar productos por stock',
    'summary': 'Orden automático de la tienda por cantidad disponible, de mayor a menor',
    'version': '18.0.1.0.0',
    'category': 'Website/eCommerce',
    'author': 'Personalización Odoo',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': ['website_sale_stock'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
}
