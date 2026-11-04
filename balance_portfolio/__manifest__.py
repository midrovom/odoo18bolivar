# -*- coding: utf-8 -*-
{
    'name': "Portfolio de Balances",

    'summary': """
        Saldo de Cartera donde se muestran los documentos adeudados y postfechados de clientes""",

    'description': """
        - Modulo para Odoo 16 Community
        - Sistema para Relohimsa actualizar cartera.
        - Contiene 2 crom para actualizar la cartera.
        - Las apis dependen del administrador de apis.
        - Crea reglas de grupo que permiten validar al usuario  y el modelo al cual pueden accesar
        - Reporte de saldo de cartera de documentos adeudados y cheques posfechados (PDF)
        - Vista tree con las lineas de balance clasificadas por documentos adeudados y cheques posfechados
        - Campo adicional para el reporte PDF (Saldo acumulado)
        - Las columnas de los documentos de tipo FA se ordenan por día de mayor a menor y viceversa para los de tipo CH
    """,

    'author': "Callphone (Ing.Diego Arcos / Mauricio Idrovo)",
    'website': "https://www.callphoneecuador.com",

    'category': 'balance_portfolio',
    'version': '18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base','api_administrator','web','l10n_latam_base'],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/rules.xml',
        'security/ir.model.access.csv',
        'views/user_profile.xml',
        'views/balance_portfolio.xml',
        'report/balance_portfolio_report.xml',
        'data/cron.xml',
    ],

    "assets": {
        'web.assets_backend': [
            'balance_portfolio/static/src/views/form/form_controller.scss',
        ],
    },

    # only loaded in demonstration mode
    'images': ['static/description/icon.png'],

    'license': 'AGPL-3',
    "installable": True,
    'auto_install': False,
    'application': True,

}
