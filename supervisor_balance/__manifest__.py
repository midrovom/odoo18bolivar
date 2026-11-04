{
    'name': 'Balance Portfolio Supervisores y Vendedores',
    'version': '18.0.1.0.0',
    'description': '''
        Modulo desarrollado para odoo 16 community
        Se actualiza saldos de cartera con supervisores y vendedores
    ''',
    'summary': 'Saldo de cartera Supervisor & Vendedor',
    'author': 'Ing. Mauricio Idrovo',
    'website': 'https://callphoneecuador.com',
    'license': 'LGPL-3',
    'category': 'balance',
    'depends': [
        'balance_portfolio'
    ],
    'data': [
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'views/balance_portfolio_view.xml',
        'views/res_user_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'assets': {
        "web.assets_backend": [
            "supervisor_balance/static/src/views/tree/style.scss",
            'supervisor_balance/static/src/js/supervisor_balance_button_tree.js',
            'supervisor_balance/static/src/xml/supervisor_balance_button_tree.xml',
            
        ],
    }
}