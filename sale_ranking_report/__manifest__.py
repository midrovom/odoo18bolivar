{
    'name': 'Sales Ranking Report',
    'version': '18.0.1.0.0',
    'description': '''
        Informe de clasificación de ventas personalizado por marca, cliente y proveedor
        Modulo adaptado a Odoo 18 Community
        Especificaciones:
            - Muestra tabla de clientes a los que se han vendido productos de diferentes marcas.
            - Visualizacion con permisos de administrador y vendedores.
            - Filtro de busqueda por vendedor para permisos de administrador.
    ''',
    'summary': 'Reporte de ranking de ventas',
    'author': 'Mauricio Idrovo',
    'website': 'https://www.callphoneecuador.com',
    'license': 'LGPL-3',
    'category': 'sale',
    'depends': [
        'base',
        'balance_portfolio',
    ],
    'data': [
        'security/security_group.xml',
        'security/ir.model.access.csv',
        'views/sale_ranking_view.xml',
    ],
    "installable": True,
    'auto_install': True,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'sale_ranking_report/static/src/js/client_action.js',
            'sale_ranking_report/static/src/xml/sale_ranking_template.xml',
            'sale_ranking_report/static/src/css/style.css',
        ]
        
    }
}