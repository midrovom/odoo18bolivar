# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestAnalyticsSalesDashboard(TransactionCase):
    """Run in an Odoo 16 test database with --test-enable."""

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        # Analytics Sales requires an EXPLICIT group even for Odoo's technical
        # administrator; base.group_system alone no longer opens the app.
        self.env.user.sudo().write({'groups_id': [
            (4, self.env.ref('analytics_sales.group_analytics_sales_admin').id),
        ]})
        local = self.env['analytics.sales.local'].sudo()
        self.shop_a = local.create({'name': 'TIENDA TEST A', 'company_id': self.company.id})
        self.shop_b = local.create({'name': 'TIENDA TEST B', 'company_id': self.company.id})
        self.user_store = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name': 'Analytics Sales Test Tienda', 'login': 'analytics_sales_test_tienda_%s' % self.company.id,
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.env['analytics.sales.user.access'].sudo().create({
            'user_id': self.user_store.id, 'role': 'tienda',
            'company_id': self.company.id, 'local_ids': [(6, 0, [self.shop_a.id])],
        })
        moves = self.env['analytics.sales.move'].sudo()
        sample = dict(company_id=self.company.id, source_kind='historico',
                      document_type='FA', document_number='TEST-1', date='2026-11-01',
                      line_name='CALZADO', brand='TEST', sku='SKU1', product_name='Test',
                      seller='Vendedor Test', cost_known=True)
        moves.create(dict(sample, source_key='test-A1', local_id=self.shop_a.id,
                          quantity=2, total_net=100, total_cost=60))
        moves.create(dict(sample, source_key='test-A2', local_id=self.shop_a.id,
                          quantity=1, total_net=50, total_cost=20))
        moves.create(dict(sample, source_key='test-B', local_id=self.shop_b.id,
                          document_number='TEST-2', quantity=10, total_net=1000, total_cost=400))

    def test_store_scope_unique_invoices_no_costs(self):
        dashboard = self.env['analytics.sales.dashboard'].with_user(self.user_store).with_company(self.company)
        d = dashboard.get_dashboard({'date_from': '2026-11-01', 'date_to': '2026-11-30'})
        self.assertEqual(d['role'], 'tienda')
        self.assertEqual(d['metrics']['invoices'], 1)
        self.assertEqual(d['metrics']['fa_units'], 3)
        self.assertEqual(d['metrics']['sales'], 150)
        self.assertNotIn('cost', d['metrics'])
        self.assertEqual(len(d['options']['locals']), 1)
        self.assertEqual(d['options']['locals'][0]['name'], 'TIENDA TEST A')
        with self.assertRaises(AccessError):
            dashboard.get_dashboard({'local_id': self.shop_b.id})
        with self.assertRaises(AccessError):
            self.env['analytics.sales.sync'].with_user(self.user_store).action_sync_now()

    def test_admin_see_costs_and_both_locals(self):
        dash = self.env['analytics.sales.dashboard']
        result = dash.get_dashboard({'date_from': '2026-11-01', 'date_to': '2026-11-30'})
        # The test runner has explicitly received Analytics Sales Administrador.
        self.assertEqual(result['metrics']['invoices'], 2)
        self.assertEqual(result['metrics']['fa_units'], 13)
        self.assertEqual(result['metrics']['sales'], 1150)
        self.assertEqual(result['metrics']['profit'], 670)


    def test_current_month_period_uses_calendar_dates(self):
        """Mes actual must use today's local month, never the last invoice date."""
        from odoo import fields
        today = fields.Date.context_today(self.env['analytics.sales.dashboard'])
        result = self.env['analytics.sales.dashboard'].get_dashboard({
            'period': 'month', 'local_id': self.shop_a.id, 'scope': 'all'})
        self.assertEqual(result['date_from'], today.replace(day=1).isoformat())
        self.assertEqual(result['date_to'], today.isoformat())
        # Even when there are no sales during the month, the period stays current.
        self.assertLessEqual(result['date_from'], result['date_to'])

    def test_previous_month_period_uses_calendar_dates(self):
        """Mes anterior uses the user's calendar month, including when empty."""
        from odoo import fields
        from datetime import timedelta
        today = fields.Date.context_today(self.env['analytics.sales.dashboard'])
        last_previous = today.replace(day=1) - timedelta(days=1)
        first_previous = last_previous.replace(day=1)
        result = self.env['analytics.sales.dashboard'].get_dashboard({
            'period': 'previous_month', 'local_id': self.shop_a.id, 'scope': 'all'})
        self.assertEqual(result['date_from'], first_previous.isoformat())
        self.assertEqual(result['date_to'], last_previous.isoformat())

    def test_goal_target_month_is_full_and_year_sums_all_twelve(self):
        """No day-by-day prorating for Mes actual/Mes anterior/Año."""
        from datetime import date
        from ..models.dashboard import _goal_cents_for_segment, _iter_month_segments

        partial_november = list(_iter_month_segments(date(2026, 11, 1), date(2026, 11, 16)))
        self.assertEqual(len(partial_november), 1)
        self.assertEqual(_goal_cents_for_segment(2000, partial_november[0], 'month'), 200000)
        self.assertEqual(_goal_cents_for_segment(2000, partial_november[0], 'previous_month'), 200000)
        # Keep the existing proration ONLY for arbitrary partial ranges.
        self.assertEqual(_goal_cents_for_segment(2000, partial_november[0], 'custom'), 106667)
        whole_year = list(_iter_month_segments(date(2026, 1, 1), date(2026, 12, 31)))
        self.assertEqual(len(whole_year), 12)
        self.assertEqual(sum(_goal_cents_for_segment(1000, segment, 'year')
                             for segment in whole_year), 1200000)

    def test_year_filter_uses_full_year_goals_even_before_december(self):
        """Actual sales may stop in November; goal still includes December."""
        establishment = self.env['analytics.sales.establishment'].sudo().create({
            'name': 'Establecimiento meta anual Dashboard Test',
            'company_id': self.company.id,
            'local_ids': [(6, 0, [self.shop_a.id])],
        })
        goal = self.env['analytics.sales.goal'].sudo().create({
            'name': 'Meta del dashboard 2026', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': establishment.id,
        })
        goal.monthly_line_ids.write({'target_amount': 100.0})
        goal.monthly_line_ids.filtered(lambda line: line.month == '11').write({'target_amount': 2000.0})
        goal.monthly_line_ids.filtered(lambda line: line.month == '12').write({'target_amount': 3000.0})
        dashboard = self.env['analytics.sales.dashboard']
        annual = dashboard.get_dashboard({
            'establishment_id': establishment.id, 'scope': 'all', 'period': 'year',
        })['goal_dashboard']
        self.assertEqual(annual['target'], 6000.0)
        self.assertEqual(sum(item['target'] for item in annual['sellers']), 6000.0)
        november = dashboard._goal_dashboard(
            self.company, 'historico', establishment, establishment.id,
            {self.shop_a.id}, '2026-11-01', '2026-11-16',
            'administrador', 'month')
        self.assertEqual(november['target'], 2000.0)
        self.assertEqual(sum(item['target'] for item in november['sellers']), 2000.0)

    def test_dashboard_seller_target_equals_goal_monthly_seller_distribution(self):
        """A November goal must be identical per person in the dashboard and Metas.

        11 vendors -> 2000 USD gives 181.81 / 181.82 USD, never a
        day-prorated figure like 96.97 USD in the middle of November.
        """
        from ..models.goal_report import build_monthly_goals

        establishment = self.env['analytics.sales.establishment'].sudo().create({
            'name': 'Distribución por vendedor dashboard',
            'company_id': self.company.id,
            'local_ids': [(6, 0, [self.shop_a.id])],
        })
        goal = self.env['analytics.sales.goal'].sudo().create({
            'name': 'Meta noviembre dashboard', 'year': 2026,
            'company_id': self.company.id,
            'establishment_id': establishment.id,
        })
        goal.monthly_line_ids.filtered(lambda line: line.month == '11').write({
            'target_amount': 2000.0,
        })
        moves = self.env['analytics.sales.move'].sudo()
        for number in range(1, 11):
            code = 'TEST-S-%02d' % number
            name = 'Vendedor %02d' % number
            moves.create({
                'company_id': self.company.id, 'source_kind': 'historico',
                'source_key': 'dashboard-seller-145-%02d' % number,
                'document_type': 'FA', 'document_number': 'SELLER-145-%02d' % number,
                'date': '2026-11-10', 'local_id': self.shop_a.id,
                'seller': name, 'seller_code': code, 'quantity': 1,
                'total_net': 20.0,
            })
        # An actual return only changes sales, never the assigned goal.
        moves.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'dashboard-seller-145-return',
            'document_type': 'DE', 'document_number': 'DE-145',
            'date': '2026-11-11', 'local_id': self.shop_a.id,
            'seller': 'Vendedor 01', 'seller_code': 'TEST-S-01',
            'quantity': 1, 'total_net': 6.0,
        })
        dashboard = self.env['analytics.sales.dashboard']
        value = dashboard._goal_dashboard(
            self.company, 'historico', establishment, establishment.id,
            {self.shop_a.id}, '2026-11-01', '2026-11-16',
            'administrador', 'month',
        )
        raw_monthly = goal._grouped_seller_sales([self.shop_a.id])
        breakdown = build_monthly_goals(
            {self.shop_a.id: self.shop_a.name}, raw_monthly, 0,
            monthly_targets=[0] * 10 + [2000, 0],
        )
        by_name = {row['name']: row for row in breakdown['months'][10]['sellers']}
        self.assertEqual(value['target'], 2000.0)
        self.assertEqual(value['seller_count'], 11)
        self.assertEqual(sum(round(row['target'] * 100) for row in value['sellers']), 200000)
        self.assertEqual(len(value['sellers']), len(by_name))
        for row in value['sellers']:
            self.assertEqual(round(row['target'] * 100), by_name[row['name']]['goal_cents'])
            self.assertIn(row['target'], (181.81, 181.82))
        shirley = next(row for row in value['sellers'] if row['name'] == 'Vendedor 01')
        self.assertEqual(shirley['actual'], 14.0)
        self.assertEqual(shirley['difference'], round(14.0 - shirley['target'], 2))

    def test_annual_monthly_api_cuts_do_not_delete_each_other(self):
        """Overlapping endpoints must not replace each other's history."""
        sync = self.env['analytics.sales.sync'].sudo()
        base = {
            'Tipo': 'FA', 'nlocal': 'TIENDA TEST A', 'numero': 'FA-100',
            'FechaFactura': '2026-01-10', 'Codproducto': 'API-SKU-1',
            'Cantidad': 1, 'Total_neto': 10, 'Vendedor': 'Equipo A',
            'id_linea': '100-1',
        }
        current = dict(base, numero='FA-200', FechaFactura='2026-11-10',
                       Codproducto='API-SKU-2', id_linea='200-1', Total_neto=20)
        self.assertEqual(sync._upsert_snapshot([base], self.company, 'api', mode='merge')['created'], 1)
        self.assertEqual(sync._upsert_snapshot([current], self.company, 'api', mode='merge')['created'], 1)
        moves = self.env['analytics.sales.move'].sudo().search([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'api'),
        ])
        self.assertEqual(len(moves), 2)
        self.assertEqual(sync._upsert_snapshot([current], self.company, 'api', mode='merge')['created'], 0)
        updated = dict(current, Total_neto=22)
        changed = sync._upsert_snapshot([updated], self.company, 'api', mode='merge')
        self.assertEqual(changed['created'], 0)
        self.assertEqual(changed['updated'], 1)
        moves = self.env['analytics.sales.move'].sudo().search([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'api'),
        ])
        self.assertEqual(len(moves), 2)
        self.assertEqual(moves.filtered(lambda r: r.document_number == 'FA-200').total_net, 22)

    def test_api_settings_menu_opens_saved_configuration_in_existing_record(self):
        """The menu must open the saved company settings, not a create form."""
        self.env.user.sudo().write({'groups_id': [
            (4, self.env.ref('analytics_sales.group_analytics_sales_admin').id)]})
        cid = self.company.id
        params = self.env['ir.config_parameter'].sudo()
        params.set_param('analytics_sales.cron_annual_enabled.%s' % cid, 'True')
        params.set_param('analytics_sales.cron_monthly_enabled.%s' % cid, 'False')
        settings = self.env['analytics.sales.settings']
        first = settings.action_open_saved()
        self.assertEqual(first['res_model'], 'analytics.sales.settings')
        self.assertTrue(first['res_id'])
        record = settings.browse(first['res_id'])
        self.assertTrue(record.exists())
        self.assertEqual(record.company_id.id, cid)
        annual_cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_anuales')
        monthly_cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_mensuales')
        self.assertEqual(record.annual_cron_id, str(annual_cron.id))
        self.assertEqual(record.monthly_cron_id, str(monthly_cron.id))
        # Change persisted data independently: opening must reload stored values.
        params.set_param('analytics_sales.cron_annual_id.%s' % cid, '0')
        params.set_param('analytics_sales.cron_monthly_id.%s' % cid, str(monthly_cron.id))
        reopened = settings.action_open_saved()
        self.assertEqual(reopened['res_id'], first['res_id'])
        self.assertEqual(record.annual_cron_id, str(annual_cron.id))
        self.assertEqual(record.monthly_cron_id, str(monthly_cron.id))
        menu = self.env.ref('analytics_sales.menu_analytics_sales_settings')
        self.assertEqual(menu.action.id, self.env.ref(
            'analytics_sales.action_analytics_sales_settings_saved').id)
        self.assertEqual(menu.action._name, 'ir.actions.server')

    def test_normal_settings_save_preserves_three_api_bindings(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from odoo.exceptions import UserError

        settings = self.env['analytics.sales.settings']
        sync = self.env['analytics.sales.sync'].sudo()
        params = self.env['ir.config_parameter'].sudo()
        cid = self.company.id
        annual = self.env.ref('analytics_sales.ir_cron_analytics_sales_anuales')
        monthly = self.env.ref('analytics_sales.ir_cron_analytics_sales_mensuales')
        apis = {101: SimpleNamespace(id=101, label='ventas_anuales'),
                102: SimpleNamespace(id=102, label='ventas_mensuales'),
                103: SimpleNamespace(id=103, label='actualizar_bodega')}
        for kind in ('annual', 'monthly', 'warehouse'):
            params.set_param('analytics_sales.api_%s_id.%s' % (kind, cid), '0')
        for kind in ('annual', 'monthly'):
            params.set_param('analytics_sales.cron_%s_id.%s' % (kind, cid), '0')

        def lookup(recordset, company, record_id):
            record = apis.get(int(record_id))
            if not record:
                raise UserError('API no disponible')
            return record

        with patch.object(type(settings), '_available_api_records',
                          lambda self: [(str(i), rec.label) for i, rec in apis.items()]), \
                patch.object(type(sync), '_api_record_by_id', lookup), \
                patch.object(type(sync), '_api_identifier', lambda self, rec: rec.label):
            first = settings.action_open_saved()
            record = settings.browse(first['res_id'])
            self.assertFalse(record._transient)
            # No action_save() call: standard form write persists the selection.
            record.write({'annual_api_id': '101', 'monthly_api_id': '102',
                          'warehouse_api_id': '103', 'annual_cron_id': str(annual.id),
                          'monthly_cron_id': str(monthly.id)})
            self.assertEqual(params.get_param('analytics_sales.api_warehouse_id.%s' % cid), '103')
            self.assertEqual(sync._configured_warehouse_api(self.company).id, 103)
            # The same hook executes on every module upgrade.
            sync.configure_crons()
            reopened = settings.action_open_saved()
            self.assertEqual(reopened['res_id'], first['res_id'])
            self.assertEqual(settings.search_count([('company_id', '=', cid)]), 1)
            self.assertEqual(record.annual_api_id, '101')
            self.assertEqual(record.monthly_api_id, '102')
            self.assertEqual(record.warehouse_api_id, '103')
            self.assertEqual(record.annual_cron_id, str(annual.id))
            self.assertEqual(record.monthly_cron_id, str(monthly.id))
            # A temporary API outage must not clear a persisted ID on reopen.
            warehouse = apis.pop(103)
            settings.action_open_saved()
            self.assertEqual(record.warehouse_api_id, '103')
            self.assertEqual(params.get_param('analytics_sales.api_warehouse_id.%s' % cid), '103')
            self.assertFalse(sync._configured_warehouse_api(self.company, raise_missing=False))
            apis[103] = warehouse
            settings.action_open_saved()
            self.assertEqual(record.warehouse_api_id, '103')
            # Losing parameter copies must not clear the permanent selectors or runtime.
            for prefix in ('api_annual_id', 'api_monthly_id', 'api_warehouse_id', 'cron_annual_id', 'cron_monthly_id'):
                params.set_param('analytics_sales.%s.%s' % (prefix, cid), False)
            self.assertEqual(sync._configured_warehouse_api(self.company).id, 103)
            self.assertEqual(sync._configured_api(self.company, 'annual').id, 101)
            self.assertEqual(sync._configured_cron_id(self.company, 'monthly'), monthly.id)
            sync.configure_crons()
            settings.action_open_saved()
            self.assertEqual(record.warehouse_api_id, '103')
            self.assertEqual(params.get_param('analytics_sales.api_warehouse_id.%s' % cid), '103')
            self.assertEqual(record.annual_cron_id, str(annual.id))
            # Clearing the selection is explicit and must not fall back on upgrade.
            record.write({'warehouse_api_id': False})
            self.assertEqual(params.get_param('analytics_sales.api_warehouse_id.%s' % cid), '0')
            self.assertFalse(sync._configured_warehouse_api(self.company, raise_missing=False))
            self.assertEqual(record.annual_api_id, '101')
            self.assertEqual(record.monthly_api_id, '102')

    def test_two_crons_are_registered_and_legacy_is_off(self):
        yearly = self.env.ref('analytics_sales.ir_cron_analytics_sales_anuales')
        monthly = self.env.ref('analytics_sales.ir_cron_analytics_sales_mensuales')
        old = self.env.ref('analytics_sales.ir_cron_analytics_sales_sync', raise_if_not_found=False)
        self.assertTrue(yearly.active)
        self.assertTrue(monthly.active)
        self.assertEqual((yearly.interval_number, yearly.interval_type), (1, 'days'))
        self.assertEqual((monthly.interval_number, monthly.interval_type), (2, 'hours'))
        if old:
            self.assertFalse(old.active)

    def test_cron_selectors_are_own_sales_jobs_only(self):
        settings = self.env['analytics.sales.settings']
        annual = self.env.ref('analytics_sales.ir_cron_analytics_sales_anuales')
        monthly = self.env.ref('analytics_sales.ir_cron_analytics_sales_mensuales')
        options = dict(settings._available_sales_crons())
        self.assertEqual(set(options), {str(annual.id), str(monthly.id)})
        self.assertIn('annual_cron_id', settings._fields)
        self.assertIn('monthly_cron_id', settings._fields)
        self.assertNotIn('annual_enabled', settings._fields)
        self.assertNotIn('monthly_enabled', settings._fields)

    def test_cron_dispatch_ignores_legacy_swapped_links(self):
        """Los cron ejecutan solo su propia API, aunque exista un vínculo anterior invertido."""
        from unittest.mock import patch
        annual = self.env.ref('analytics_sales.ir_cron_analytics_sales_anuales')
        monthly = self.env.ref('analytics_sales.ir_cron_analytics_sales_mensuales')
        cid = self.company.id
        params = self.env['ir.config_parameter'].sudo()
        # Intercambiados deliberadamente: verifica que no se use el nombre.
        params.set_param('analytics_sales.cron_annual_id.%s' % cid, str(monthly.id))
        params.set_param('analytics_sales.cron_monthly_id.%s' % cid, str(annual.id))
        sync = self.env['analytics.sales.sync'].sudo()
        params.set_param('analytics_sales.api_annual_id.%s' % cid, '101')
        params.set_param('analytics_sales.api_monthly_id.%s' % cid, '102')
        self.assertEqual(sync._configured_cron_id(self.company, 'annual'), annual.id)
        self.assertEqual(sync._configured_cron_id(self.company, 'monthly'), monthly.id)
        called = []

        def fake_run(recordset, company, origin, kind=None):
            called.append((company.id, origin, kind))
            return {}

        with patch.object(type(sync), '_run', fake_run):
            sync.cron_sync_mensuales()
            self.assertIn((cid, 'api', 'monthly'), called)
            self.assertNotIn((cid, 'api', 'annual'), called)
            called.clear()
            sync.cron_sync_anuales()
            self.assertIn((cid, 'api', 'annual'), called)
            self.assertNotIn((cid, 'api', 'monthly'), called)
            called.clear()
            params.set_param('analytics_sales.api_monthly_id.%s' % cid, '0')
            sync.cron_sync_mensuales()
            self.assertFalse(any(c[0] == cid for c in called))

    def test_api_binding_fields_and_history_id(self):
        """Cron relationships are stored by API Administrator ID, not display name."""
        settings = self.env['analytics.sales.settings']
        log = self.env['analytics.sales.sync.log']
        self.assertIn('annual_api_id', settings._fields)
        self.assertIn('monthly_api_id', settings._fields)
        self.assertIn('api_config_id', log._fields)


    def test_model_rankings_group_variants_and_returns_without_changing_totals(self):
        moves = self.env['analytics.sales.move'].sudo()
        one = moves.search([('source_key', '=', 'test-A1'), ('company_id', '=', self.company.id)])
        two = moves.search([('source_key', '=', 'test-A2'), ('company_id', '=', self.company.id)])
        one.write({'modelo': 'MODELO-1'})
        two.write({'modelo': 'MODELO-1', 'sku': 'SKU2'})
        common = dict(company_id=self.company.id, source_kind='historico', date='2026-11-01',
                      local_id=self.shop_a.id, line_name='CALZADO', brand='TEST',
                      product_name='Prueba modelo', seller='Vendedor Test', cost_known=True)
        moves.create(dict(common, source_key='test-model-return', document_type='DE',
                          document_number='TEST-DE', sku='SKU2', modelo='MODELO-1',
                          quantity=1, total_net=20, total_cost=10))
        moves.create(dict(common, source_key='test-model-missing', document_type='FA',
                          document_number='TEST-MISSING', sku='SKU3',
                          quantity=1, total_net=10, total_cost=5))
        params = {'date_from': '2026-11-01', 'date_to': '2026-11-30', 'local_id': self.shop_a.id}
        result = self.env['analytics.sales.dashboard'].get_dashboard(params)
        ranked = {r['name']: r for r in result['rankings']['models']}
        self.assertEqual(set(ranked), {'MODELO-1', 'Sin modelo'})
        self.assertEqual(ranked['MODELO-1']['sales'], 130)
        self.assertEqual(ranked['MODELO-1']['fa_sales'], 150)
        self.assertEqual(ranked['MODELO-1']['de_sales'], 20)
        self.assertEqual(ranked['MODELO-1']['units'], 2)
        self.assertEqual(ranked['MODELO-1']['abc'], 'A')
        self.assertEqual(ranked['Sin modelo']['sales'], 10)
        self.assertEqual(result['metrics']['sales'], 140)
        self.assertEqual(sum(r['sales'] for r in ranked.values()), result['metrics']['sales'])
        self.assertEqual(len(result['rankings']['products']), 3)
        store = self.env['analytics.sales.dashboard'].with_user(self.user_store).with_company(self.company)
        scoped = store.get_dashboard(params)
        self.assertEqual(scoped['metrics']['sales'], 140)
        self.assertNotIn('cost', scoped['rankings']['models'][0])


class TestAnalyticsSalesExplicitPermissions(TransactionCase):
    """Security regression tests for the version 1.1.15 upgrade."""

    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.user_group = self.env.ref('base.group_user')
        self.system_group = self.env.ref('base.group_system')
        self.admin_group = self.env.ref('analytics_sales.group_analytics_sales_admin')
        self.store_group = self.env.ref('analytics_sales.group_analytics_sales_tienda')
        self.supervisor_group = self.env.ref('analytics_sales.group_analytics_sales_supervisor')
        self._serial = 0

    def _user(self, roles):
        self._serial += 1
        return self.env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name': 'TEST PERMISOS ANALYTICS %s' % self._serial,
            'login': 'analytics_permissions_%s_%s' % (self.company.id, self._serial),
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.user_group.id] + [r.id for r in roles])],
        })

    def test_without_analytics_group_denied_even_settings_admin(self):
        user = self._user([self.system_group])
        dashboard = self.env['analytics.sales.dashboard'].with_user(user)
        with self.assertRaises(AccessError):
            dashboard.get_dashboard()
        with self.assertRaises(AccessError):
            self.env['analytics.sales.sync'].with_user(user).action_sync_now()

    def test_explicit_admin_group_can_bootstrap_without_profile(self):
        user = self._user([self.admin_group])
        role, scope = self.env['analytics.sales.security'].with_user(user).get_role_and_scope()
        self.assertEqual(role, 'administrador')
        self.assertIsNone(scope)

    def test_store_group_without_local_assignment_cannot_see_data(self):
        user = self._user([self.store_group])
        with self.assertRaises(AccessError):
            self.env['analytics.sales.dashboard'].with_user(user).get_dashboard()

    def test_supervisor_group_and_profile_have_scope_without_cost(self):
        local = self.env['analytics.sales.local'].sudo().create({
            'name': 'TEST PERMISOS LOCAL', 'company_id': self.company.id,
        })
        # A valid Analytics Sales Admin configures the profile from the app.
        self.env.user.sudo().write({'groups_id': [(4, self.admin_group.id)]})
        user = self._user([self.supervisor_group])
        self.env['analytics.sales.user.access'].create({
            'user_id': user.id, 'company_id': self.company.id,
            'role': 'supervisor', 'local_ids': [(6, 0, [local.id])],
        })
        role, local_ids = self.env['analytics.sales.security'].with_user(user).get_role_and_scope()
        self.assertEqual(role, 'supervisor')
        self.assertEqual(local_ids, [local.id])
        dash = self.env['analytics.sales.dashboard'].with_user(user).get_dashboard()
        self.assertNotIn('cost', dash['metrics'])
        self.assertEqual([d['id'] for d in dash['options']['locals']], [local.id])

    def test_settings_group_not_on_menus_or_model_access(self):
        root = self.env.ref('analytics_sales.menu_analytics_sales_root')
        admin = self.env.ref('analytics_sales.menu_analytics_sales_admin')
        self.assertNotIn(self.system_group, root.groups_id)
        self.assertNotIn(self.system_group, admin.groups_id)
        self.assertEqual(set(root.groups_id.ids), {
            self.admin_group.id, self.supervisor_group.id, self.store_group.id})
        self.assertEqual(set(admin.groups_id.ids), {self.admin_group.id})
        for xmlid in (
            'access_sales_local_system', 'access_sales_assignment_system',
            'access_sales_move_system', 'access_sales_settings_system',
            'access_sales_log_system', 'access_sales_excel_import_system',
        ):
            self.assertFalse(self.env.ref('analytics_sales.' + xmlid, raise_if_not_found=False))
