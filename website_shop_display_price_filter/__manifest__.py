{
    'name': 'Website Shop - Filtrar por Precio Mostrado',
    'summary': 'Filtra el catálogo por el precio que realmente se muestra en /shop.',
    'description': '''
Utiliza el precio calculado de cada tarjeta del catálogo de tienda para
filtrar productos y determinar los extremos del filtro de precio.
Respeta la lista de precios, la posición fiscal, los impuestos y la moneda
que aplica el sitio web, sin modificar website_sale.
''',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'author': 'Personalización Odoo',
    'license': 'LGPL-3',
    'depends': ['website_sale'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
