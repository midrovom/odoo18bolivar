# -*- coding: utf-8 -*-
"""Read company and external pricelist identifiers from configured inventory URL.

The external route is show_inventory_web/<external_company_id>/<external_price_list_id>.
No URL, company or price-list number is baked into the synchronization.
"""
import re
from urllib.parse import urlsplit

_ROUTE = re.compile(r'(?:^|/)show_inventory_web/(\d+)/(\d+)/?$')


def endpoint_company_and_price(url, end_point):
    """Return (company_id, external_price_list_id) or raise a useful error.

    Handles full URLs as well as relative paths stored in api_administrator.
    The company identifier belongs to the external service; it MUST NOT be
    interpreted as an Odoo res.company.id. Odoo company comes from the API
    Administrator configuration (company_id).
    """
    full = (url or '').strip() + (end_point or '').strip()
    path = urlsplit(full).path.rstrip('/')
    match = _ROUTE.search(path)
    if not match:
        raise ValueError(
            'El endpoint debe terminar en show_inventory_web/<id_empresa>/<id_lista>; '
            'recibido: %s' % (path or '(vacío)')
        )
    company_id, list_id = map(int, match.groups())
    if company_id <= 0 or list_id <= 0:
        raise ValueError('Los IDs de empresa y lista del endpoint deben ser mayores que cero.')
    return company_id, list_id
