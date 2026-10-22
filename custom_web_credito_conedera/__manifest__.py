{
    'name': 'Portal de Solicitudes de Crédito CONEDERA',
    'version': '18.0.1.0.7',
    'summary': 'Registro verificado, solicitudes de crédito, etapas e ingreso documental para CONEDERA S.A.',
    'description': '''
Portal de solicitudes de crédito CONEDERA S.A. para Odoo 18.
- Registro nativo de Odoo con aceptación de términos y condiciones del módulo custom_web_hr_datos_candidatos y verificación de correo mediante OTP en modal.
- Formulario web basado en la Solicitud de Crédito CONEDERA proporcionada.
- Historial del solicitante y línea de tiempo de etapas.
- Flujo kanban interno de gestión.
- Ingreso de documentos habilitado al aprobar la solicitud y condicionado a persona natural/jurídica.
- Sección interna para verificación de la ubicación del negocio.
''',
    'author': 'OpenAI',
    'license': 'LGPL-3',
    'category': 'Website',
    'depends': ['base', 'mail', 'portal', 'website', 'web', 'auth_signup', 'custom_web_hr_datos_candidatos'],
    'data': [
        'security/credit_security.xml',
        'security/ir.model.access.csv',
        'data/credit_sequence.xml',
        'data/credit_stages.xml',
        'data/website_menu.xml',
        'views/credit_stage_views.xml',
        'views/credit_application_views.xml',
        'views/credit_documents_views.xml',
        'views/ir_mail_server_view.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'custom_web_credito_conedera/static/src/css/credit_portal.css',
            'custom_web_credito_conedera/static/src/js/credit_portal.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
}
