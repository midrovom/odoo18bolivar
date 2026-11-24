# -*- coding: utf-8 -*-
"""Extend Transcash HTML entrypoints; leave its source and ORM operations intact.

The original UI runs in standalone same-origin iframes (not the Odoo OWL
asset environment). We therefore inject language metadata and one small JS
bridge into the HTML returned by the original controller. No endpoint or
permission checks are replaced: each method delegates to super() first.
"""

import ast
import html
import json
import re

from odoo import http
from odoo.http import request
from odoo.addons.transcash_inventory.controllers.routes import TranscashDashboardController


_ASSET = '/transcash_inventory_native_decimals/static/src/native_decimals.js?v=18.0.1.0.0'


def _read_grouping(raw):
    """Return Odoo/Python grouping as a JSON-compatible list of integers."""
    if isinstance(raw, (list, tuple)):
        parsed = raw
    else:
        try:
            parsed = ast.literal_eval(str(raw or '[]'))
        except (ValueError, SyntaxError, TypeError, MemoryError):
            return [3, 0]
    if not isinstance(parsed, (list, tuple)) or len(parsed) > 20:
        return [3, 0]
    # [] means no digit grouping; [3,0] means repeated groups of three.
    if any(type(part) is not int or part < -1 or part > 9 for part in parsed):
        return [3, 0]
    return list(parsed)


def _locale_data():
    user = request.env.user
    language_code = user.lang or request.env.context.get('lang') or 'en_US'
    langs = request.env['res.lang'].sudo()
    language = langs.search([('code', '=', language_code)], limit=1)
    if not language:
        language = langs.search([('code', '=', request.env.context.get('lang') or 'en_US')], limit=1)
    if not language:
        # A normal Odoo DB has en_US installed. This only protects unusual DBs.
        language = langs.search([], limit=1)
    if not language:
        return {'lang': language_code, 'decimal_point': '.', 'thousands_sep': ',', 'grouping': [3, 0]}
    return {
        'lang': language.code,
        'decimal_point': language.decimal_point or '.',
        'thousands_sep': language.thousands_sep or '',
        'grouping': _read_grouping(language.grouping),
    }


def _decorate_html(response):
    """Add bridge before the original JS executes, only for successful HTML."""
    if response.status_code != 200 or response.mimetype != 'text/html':
        return response
    original_html = response.get_data(as_text=True)
    if 'transcash-native-decimals' in original_html:
        return response
    config_json = json.dumps(_locale_data(), ensure_ascii=True, separators=(',', ':'))
    # Quoting for a double-quoted HTML attribute also handles untrusted locale
    # values without adding executable inline script content.
    meta = '<meta name="transcash-native-decimals" content="%s">' % html.escape(config_json, quote=True)
    script = '<script src="%s"></script>' % _ASSET
    modified, count = re.subn(r'</head\s*>', lambda match: meta + script + match.group(0),
                              original_html, count=1, flags=re.IGNORECASE)
    if count:
        response.set_data(modified)
    return response


class TranscashNativeDecimalController(TranscashDashboardController):
    @http.route()
    def dashboard(self, **kw):
        return _decorate_html(super().dashboard(**kw))

    @http.route()
    def imported_view(self, **kw):
        return _decorate_html(super().imported_view(**kw))

    @http.route()
    def import_page(self, **kw):
        return _decorate_html(super().import_page(**kw))

    @http.route()
    def photos_sync_ui(self, **kw):
        return _decorate_html(super().photos_sync_ui(**kw))
