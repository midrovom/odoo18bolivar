from urllib.parse import urlparse

from odoo import http
from odoo.http import request


class ConederaCreditHome(http.Controller):
    """Public marketing page. Never modifies credit applications or portal routes."""

    @staticmethod
    def _safe_url(raw):
        """Only local HTTP paths or HTTPS/HTTP URLs; no javascript:/scheme-relative URLs."""
        raw = (raw or '').strip()
        if not raw or any(ord(c) < 32 for c in raw):
            return None
        if raw.startswith('/') and not raw.startswith('//') and not raw.startswith('/\\'):
            return raw
        parsed = urlparse(raw)
        if parsed.scheme in ('https', 'http') and parsed.netloc and not parsed.username and not parsed.password:
            return raw
        return None

    @classmethod
    def _menu_url(cls, website, needles):
        """Reuse existing credit portal website menu if registered as a website.menu."""
        Menu = request.env['website.menu'].sudo()
        for needle in needles:
            records = Menu.search([
                ('name', 'ilike', needle),
                '|', ('website_id', '=', website.id), ('website_id', '=', False),
            ], limit=12)
            for menu in records:
                safe = cls._safe_url(menu.url)
                if safe and safe not in ('#', '/credito-conedera'):
                    return safe
        return None

    @http.route(['/credito-conedera'], type='http', auth='public', website=True, sitemap=True)
    def conedera_home(self, **kw):
        website = request.website
        company = website.company_id.sudo()
        apply_url = self._safe_url(company.conedera_home_apply_url) or self._menu_url(
            website, ['Solicitud de crédito', 'Solicitar crédito', 'Solicitud credito']
        ) or '/my'
        history_url = self._safe_url(company.conedera_home_history_url) or self._menu_url(
            website, ['Historial de solicitudes', 'Mis solicitudes']
        ) or '/my'
        documents_url = self._safe_url(company.conedera_home_documents_url) or self._menu_url(
            website, ['Ingreso de documentos', 'Documentos solicitados']
        ) or '/my'
        return request.render('conedera_credit_home.conedera_home_page', {
            'apply_url': apply_url,
            'history_url': history_url,
            'documents_url': documents_url,
            'company': company,
        })
