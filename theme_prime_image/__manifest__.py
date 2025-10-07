{
    'name': 'Theme Prime Image',
    'version': '18.0.1.0.0',
    'summary': 'Extensión visual para theme prime',
    'category': 'Theme/eCommerce',
    'depends': ['theme_prime'],
    'data': [
        'views/theme_shop_layout_views.xml',
        #'views/snippet/banner_custom/snippet_banner_16.xml',
        'views/snippet/subscribe_custom/snippet_subscribe.xml',
        #'views/snippet/banner_custom/snippet_banner_17.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'theme_prime_image/static/src/js/s_banner.js',
            'theme_prime_image/static/src/js/s_banner_17.js'
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False
}
