{
    'name': 'Advance Theme Custom',
    'version': '18.0.1.0.0',
    'summary': 'Extensión de estilos',
    'category': 'eCommerce',
    'depends': ['website'],
    'data': [
    ],
    'assets': {
        'web.assets_frontend': [
            'advance_theme_custom/static/src/scss/cover_custom/snippet_cover_custom.scss',
            'advance_theme_custom/static/src/scss/gallery_custom/gallery_custom.scss',
            'advance_theme_custom/static/src/scss/texto_custom/texto_custom.scss',
            'advance_theme_custom/static/src/scss/banner_custom/custom_category_slider.scss',
           # 'advance_theme_custom/static/src/scss/clients_custom/clients_custom.scss'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False
}
