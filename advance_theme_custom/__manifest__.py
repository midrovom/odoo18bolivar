{
    'name': 'Advance Theme Custom',
    'version': '18.0.1.0.0',
    'summary': 'Extensión de estilos',
    'category': 'eCommerce',
    'depends': ['website', 'website_sale'],
    'data': [
        'data/data.xml',
        'data/product_public_categ_data.xml',
        #'views/snippets/register.xml',
        'views/templates.xml',
        #'views/snippets/dynamic_snippet_custom.xml',
        'views/snippets/snippets.xml',
        #'views/snippets/s_dynamic_snippet_categories_preview_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'advance_theme_custom/static/src/scss/cover_custom/snippet_cover_custom.scss',
            'advance_theme_custom/static/src/scss/gallery_custom/gallery_custom.scss',
            'advance_theme_custom/static/src/scss/texto_custom/texto_custom.scss',
            'advance_theme_custom/static/src/scss/banner_custom/custom_category_slider.scss',
            'advance_theme_custom/static/src/scss/clients_custom/clients_custom.scss',
            'advance_theme_custom/static/src/scss/shop_offert_custom/s_shop_offer_custom.scss',
            'advance_theme_custom/static/src/scss/shop_offert_custom/s_shop_offer_hot.scss',
            'advance_theme_custom/static/src/scss/footer_custom/footer_custom.scss',
            'advance_theme_custom/static/src/scss/dynamic_custom/prueba.scss',
            # 'advance_theme_custom/static/src/js/category_slider_12.js',

            #'advance_theme_custom/static/src/snippets/carousel_product_card.js',
            #'advance_theme_custom/static/src/snippets/dynamic_snippet_products.js',
            #'advance_theme_custom/static/src/snippets/000.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False
}
