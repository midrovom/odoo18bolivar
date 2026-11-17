"""Configure the stock-first default for pre-existing websites."""


def post_init_hook(env):
    # The user wants this sort to become the default immediately after install,
    # not just for websites created in the future.
    env['website'].sudo().search([]).write({'shop_default_sort': 'stock_desc'})


def uninstall_hook(env):
    # Do not leave a removed selection value on website records.
    env['website'].sudo().search([
        ('shop_default_sort', 'in', ['stock_desc', 'stock_asc']),
    ]).write({'shop_default_sort': 'website_sequence asc'})
