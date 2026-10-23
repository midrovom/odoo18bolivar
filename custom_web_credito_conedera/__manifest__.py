{
    'name': 'Portal de Solicitudes de Crédito CONEDERA',
    'version': '18.0.1.8.4',
    'summary': 'Registro verificado, solicitudes de crédito, etapas e ingreso documental para CONEDERA S.A.',
    'description': '''
Portal de solicitudes de crédito CONEDERA S.A. para Odoo 18.
- Registro nativo de Odoo con aceptación de términos y condiciones del módulo custom_web_hr_datos_candidatos y verificación de correo mediante OTP en modal.
- Formulario web basado en la Solicitud de Crédito CONEDERA proporcionada.
- Historial del solicitante y línea de tiempo de etapas.
- Flujo kanban interno de gestión.
- Ingreso de documentos habilitado al aprobar la solicitud y con documentos configurables por tipo de solicitante.
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
        'data/credit_catalog_sequences.xml',
        'data/credit_stages.xml',
        'data/credit_applicant_types.xml',
        'data/credit_marital_statuses.xml',
        'data/credit_housing_types.xml',
        'data/website_menu.xml',
        'views/credit_stage_views.xml',
        'views/credit_application_views.xml',
        'views/credit_access_wizard_views.xml',
        'views/credit_theme_views.xml',
        'views/res_users_credit_views.xml',
        'views/credit_applicant_type_views.xml',
        'views/credit_marital_status_views.xml',
        'views/credit_housing_type_views.xml',
        'views/credit_documents_views.xml',
        'views/ir_mail_server_view.xml',
        'views/portal_templates.xml',
        'data/credit_upgrade.xml',
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
