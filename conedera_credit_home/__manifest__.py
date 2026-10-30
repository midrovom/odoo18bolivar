{
    'name': 'CONEDERA | Home de crédito',
    'summary': 'Página institucional de créditos enlazada al portal de solicitudes',
    'description': 'Home público responsive de CONEDERA. Accesos a solicitud, historial y documentos por empresa.',
    'version': '18.0.1.0.0',
    'category': 'Website/Website',
    'author': 'CONEDERA S.A.',
    'license': 'LGPL-3',
    'depends': ['website', 'custom_web_credito_conedera'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/website_home_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'conedera_credit_home/static/src/css/conedera_home.css',
        ],
    },
    'application': False,
    'installable': True,
}
