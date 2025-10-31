{
    'name': 'Theme Prime Image',
    'version': '18.0.1.0.0',
    'summary': 'Extensión visual para theme prime',
    'category': 'Theme/eCommerce',
    'depends': ['theme_prime'],
    'data': [
        'views/theme_shop_layout_views.xml',
        'views/snippet/banner_custom/snippet_banner_9_custom.xml',
        'views/snippet/subscribe_custom/snippet_subscribe.xml',
        'views/snippet/shop_offert_custom/s_shop_offer_custom.xml',
        'views/snippet/cover_custom/snippet_cover_custom.xml',
        'views/snippet/clients_custom/clients_custom.xml',
        'views/snippet/Header_custom/header_custom.xml',
        'views/snippet/texto_custom/texto_custom.xml',
        'views/snippet/gallery_custom/image_delivery_guarantee.xml',
        'views/snippet/banner_custom/custom_category_slider.xml',
        'views/snippet/footer_custom/footer_style_1_custom.xml',
        'views/snippet/shop_offert_custom/shop_offer_6.xml',
        'views/snippet/shop_offert_custom/s_shop_offer_hot.xml',
        # 'views/snippets.xml',
       #'views/snippet/dynamic_snippet/dynamic_snippet_custom.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            #'theme_prime_image/static/src/js/s_tp_category_carousel.js',
        ],
        'website.assets_wysiwyg': [
            'theme_prime_image/static/src/components/*'
            
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False
}
