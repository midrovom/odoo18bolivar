{
    'name': 'Reporte de Ventas',
    'version': '18.0.1.0.0',
    'description': 'Ranking de vendedores por empresa',
    'summary': 'Reporte de ventas',
    'author': 'Ing.Bolivar Rodriguez',
    'website': "https://www.callphoneecuador.com",
    'category': 'Report',
    'depends': ['api_administrator','web', 'sale'],
    'data': [
        'security/security_group.xml',
        'security/ir.model.access.csv',
        'views/sale_report_action.xml',
        'views/sale_report_tipe_view.xml',
        'views/add_emresa.xml',
        'views/res_users_views.xml',
    ],
    'license': 'LGPL-3',
    "installable": True,
    'auto_install': False,
    'application': True,
    'assets': {
        'web.assets_backend': [
            'sale_report/static/src/js/sale_report.js',
            'sale_report/static/src/xml/sale_report_ventas.xml',
            'sale_report/static/src/css/sale_report.css',
        ]
    }  
}
