# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _


class AnalyticsSalesCategory(models.Model):
    _name = 'analytics.sales.category'
    _description = 'Maestro de atributos de ventas (Línea)'
    _order = 'name, id'

    name = fields.Char(string='Atributo (Línea)', required=True, readonly=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True,
                                 index=True, ondelete='cascade')
    _sql_constraints = [
        ('category_company_name_unique', 'unique(company_id, name)',
         'La línea ya existe en la compañía.'),
    ]

    @api.model
    def _register_names(self, company, names):
        """Append distinct normalized names; never remove or replace existing IDs."""
        names = {name or 'SIN LÍNEA' for name in names}
        if not names:
            return 0
        catalog = self.sudo()
        # Same company-level lock used by the settings initialization. A unique
        # database constraint is the additional protection against duplicates.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (171708, company.id))
        existing = set(catalog.search([('company_id', '=', company.id),
                                       ('name', 'in', sorted(names))]).mapped('name'))
        missing = sorted(names - existing)
        if missing:
            catalog.create([{'name': name, 'company_id': company.id} for name in missing])
        return len(missing)

    @api.model
    def _refresh_from_sales(self, company):
        # Backfill historical and API data, including cancelled source rows.
        # Dashboard source/date/security rules are intentionally unchanged.
        moves = self.env['analytics.sales.move'].sudo().with_context(active_test=False)
        domain = [('company_id', '=', company.id), ('document_type', 'in', ['FA', 'DE'])]
        names = (row['line_name'] for row in moves.read_group(
            domain, ['line_name'], ['line_name'], lazy=False))
        return self._register_names(company, names)

    @api.model
    def _initialize_from_sales(self):
        """Idempotent install/upgrade backfill, without calling external APIs."""
        moves = self.env['analytics.sales.move'].sudo().with_context(active_test=False)
        by_company = defaultdict(set)
        for row in moves.read_group([('document_type', 'in', ['FA', 'DE'])],
                                    ['company_id', 'line_name'],
                                    ['company_id', 'line_name'], lazy=False):
            if row['company_id']:
                by_company[row['company_id'][0]].add(row['line_name'])
        for company_id in sorted(by_company):
            company = self.env['res.company'].sudo().browse(company_id)
            self._register_names(company, by_company[company_id])
        return True

    @api.model
    def action_open_master(self):
        self.env['analytics.sales.security'].check_admin()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maestro de atributos'),
            'res_model': self._name,
            'view_mode': 'list,form',
            'views': [(self.env.ref('analytics_sales.view_analytics_sales_category_list').id, 'list'),
                      (self.env.ref('analytics_sales.view_analytics_sales_category_form').id, 'form')],
            'domain': [('company_id', '=', self.env.company.id)],
            'target': 'current',
        }
