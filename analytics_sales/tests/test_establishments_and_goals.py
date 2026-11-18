# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError
from ..models.goal_report import build_monthly_goals


class TestAnalyticsSalesEstablishmentsGoals(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.admin_group = self.env.ref('analytics_sales.group_analytics_sales_admin')
        self.store_group = self.env.ref('analytics_sales.group_analytics_sales_tienda')
        self.env.user.sudo().write({'groups_id': [(4, self.admin_group.id)]})
        local_model = self.env['analytics.sales.local']
        self.local1 = local_model.create({'name': 'MAESTRO TEST DURAN', 'company_id': self.company.id})
        self.local2 = local_model.create({'name': 'MAESTRO TEST ALBORADA', 'company_id': self.company.id})
        est_model = self.env['analytics.sales.establishment']
        self.est1 = est_model.create({
            'name': 'Durán test', 'company_id': self.company.id,
            'local_ids': [(6, 0, [self.local1.id])],
        })
        self.est2 = est_model.create({
            'name': 'Alborada test', 'company_id': self.company.id,
            'local_ids': [(6, 0, [self.local2.id])],
        })
        sale = self.env['analytics.sales.move'].sudo()
        common = {'company_id': self.company.id, 'document_type': 'FA', 'date': '2026-11-11',
                  'source_kind': 'historico', 'line_name': 'CALZADO', 'quantity': 1,
                  'total_cost': 4, 'cost_known': True}
        sale.create(dict(common, local_id=self.local1.id, total_net=12,
                         document_number='MAESTRO-A', source_key='maestro-est-A'))
        sale.create(dict(common, local_id=self.local2.id, total_net=30,
                         document_number='MAESTRO-B', source_key='maestro-est-B'))

    def test_total_meta_sums_monthly_targets_only(self):
        goals = self.env['analytics.sales.goal']
        goal = goals.create({'name': 'Total Durán', 'company_id': self.company.id,
                             'year': 2026, 'establishment_id': self.est1.id,
                             'target_amount': 999999})
        other = goals.create({'name': 'Total Alborada', 'company_id': self.company.id,
                              'year': 2026, 'establishment_id': self.est2.id})
        self.assertEqual(len(goal.monthly_line_ids), 12)
        self.assertEqual(goal.total_meta, 0.0)
        goal.monthly_line_ids.filtered(lambda r: r.month == '01').target_amount = 1000.25
        goal.monthly_line_ids.filtered(lambda r: r.month == '02').target_amount = 2000.50
        self.assertAlmostEqual(goal.total_meta, 3000.75, places=2)
        self.assertEqual(other.total_meta, 0.0)
        goal.bulk_monthly_target = '1500'
        goal.action_apply_monthly_target()
        self.assertAlmostEqual(goal.total_meta, 18000.0, places=2)
        goal.monthly_line_ids.filtered(lambda r: r.month == '12').target_amount = 2000.0
        self.assertAlmostEqual(goal.total_meta, 18500.0, places=2)
        self.assertTrue(goals._fields['total_meta'].readonly)
        self.assertFalse(goals._fields['total_meta'].inverse)

    def test_local_can_only_belong_to_one_establishment(self):
        with self.assertRaises(ValidationError):
            self.est2.write({'local_ids': [(4, self.local1.id)]})

    def test_goals_by_year_and_establishment(self):
        goals = self.env['analytics.sales.goal']
        goals.create({'name': 'General', 'company_id': self.company.id,
                      'year': 2026, 'target_amount': 100000})
        goals.create({'name': 'Durán', 'company_id': self.company.id,
                      'year': 2026, 'establishment_id': self.est1.id, 'target_amount': 25000})
        goals.create({'name': 'Alborada', 'company_id': self.company.id,
                      'year': 2026, 'establishment_id': self.est2.id, 'target_amount': 35000})
        with self.assertRaises(ValidationError):
            goals.create({'name': 'General repetida', 'company_id': self.company.id,
                          'year': 2026, 'target_amount': 200000})
        with self.assertRaises(ValidationError):
            goals.create({'name': 'Durán repetida', 'company_id': self.company.id,
                          'year': 2026, 'establishment_id': self.est1.id, 'target_amount': 30000})

    def test_admin_filters_by_establishment_without_mixing_localities(self):
        dashboard = self.env['analytics.sales.dashboard']
        result = dashboard.get_dashboard({'establishment_id': self.est1.id,
                                          'date_from': '2026-11-01', 'date_to': '2026-11-30',
                                          'scope': 'all'})
        self.assertEqual(result['metrics']['sales'], 12)
        self.assertEqual(result['selected_establishment_id'], self.est1.id)
        self.assertIn('daily_history', result)
        self.assertNotIn('daily_projection', result)
        history = result['daily_history']
        self.assertEqual(history['history_days'], 15)
        self.assertEqual(history['history'][-1], {'date': '2026-11-11', 'sales': 12.0})
        self.assertTrue(all(day['date'] <= '2026-11-11' for day in history['history']))
        self.assertAlmostEqual(history['net_total'], 12)
        with self.assertRaises(AccessError):
            dashboard.get_dashboard({'establishment_id': self.est1.id, 'local_id': self.local2.id})

    def test_comparison_respects_local_when_establishment_and_local_selected(self):
        """Establecimiento solo: total agrupado. Establecimiento + local: local elegido."""
        local3 = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN SEGUNDO', 'company_id': self.company.id})
        empty_local = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN SIN VENTAS', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, local3.id), (4, empty_local.id)]})
        self.env['analytics.sales.move'].sudo().create({
            'company_id': self.company.id, 'source_key': 'comparison-est-local3',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'C-3', 'date': '2026-11-11',
            'local_id': local3.id, 'line_name': 'CALZADO',
            'quantity': 2, 'total_net': 44,
        })
        dashboard = self.env['analytics.sales.dashboard']
        args = {'establishment_id': self.est1.id, 'local_id': self.local1.id,
                'date_from': '2026-11-01', 'date_to': '2026-11-30', 'scope': 'all'}
        result = dashboard.get_dashboard(args)
        # Los KPI principales permanecen filtrados por el nlocal seleccionado.
        self.assertEqual(result['metrics']['sales'], 12)
        self.assertEqual([r['name'] for r in result['rankings']['stores']], [self.local1.name])
        # La tarjeta ahora presenta únicamente los importes del local elegido.
        chart = result['establishment_comparison']
        self.assertEqual([r['name'] for r in chart], [self.local1.name])
        self.assertEqual(chart[0]['sales'], 12)
        self.assertEqual(chart[0]['invoices'], 1)
        self.assertNotIn(self.est2.name, [r['name'] for r in chart])
        # Sin seleccionar local sigue sumando TODO el establecimiento.
        result_all = dashboard.get_dashboard(dict(args, local_id='all'))
        self.assertEqual(result_all['metrics']['sales'], 56)
        self.assertEqual([r['name'] for r in result_all['establishment_comparison']], [self.est1.name])
        self.assertEqual(result_all['establishment_comparison'][0]['sales'], 56)
        self.assertEqual(result_all['establishment_comparison'][0]['invoices'], 2)
        # Sin filtro de establecimiento: cada uno aparece una vez, no por nlocal.
        both = dashboard.get_dashboard(dict(args, establishment_id='all', local_id='all'))
        items = {row['name']: row for row in both['establishment_comparison']}
        self.assertEqual(items[self.est1.name]['sales'], 56)
        self.assertEqual(items[self.est2.name]['sales'], 30)

    def test_establishment_and_local_respect_returns_and_include_zero_sale_locals(self):
        """FA/DE del local elegido, sin confundirlo con todo el establecimiento."""
        other = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN EXTRA', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, other.id)]})
        moves = self.env['analytics.sales.move'].sudo()
        moves.create({
            'company_id': self.company.id, 'source_key': 'comparison-local-de',
            'source_kind': 'historico', 'document_type': 'DE',
            'document_number': 'RETURN-1', 'date': '2026-11-11',
            'local_id': self.local1.id, 'line_name': 'CALZADO',
            'quantity': 1, 'total_net': 2.0,
        })
        moves.create({
            'company_id': self.company.id, 'source_key': 'comparison-other-fa',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'OTHER-1', 'date': '2026-11-11',
            'local_id': other.id, 'line_name': 'CALZADO',
            'quantity': 1, 'total_net': 88.0,
        })
        dash = self.env['analytics.sales.dashboard']
        params = {'establishment_id': self.est1.id, 'local_id': self.local1.id,
                  'date_from': '2026-11-01', 'date_to': '2026-11-30', 'scope': 'all'}
        local = dash.get_dashboard(params)['establishment_comparison']
        self.assertEqual([row['name'] for row in local], [self.local1.name])
        self.assertEqual(local[0]['fa_sales'], 12)
        self.assertEqual(local[0]['de_sales'], 2)
        self.assertEqual(local[0]['sales'], 10)
        establishment = dash.get_dashboard(dict(params, local_id='all'))['establishment_comparison']
        self.assertEqual(establishment[0]['name'], self.est1.name)
        self.assertEqual(establishment[0]['sales'], 98)

    def test_comparison_mobile_period_uses_selected_local_sale(self):
        """Con establecimiento + local, los dos bloques usan el período del local."""
        later = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO LOCAL VENTA POSTERIOR', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, later.id)]})
        self.env['analytics.sales.move'].sudo().create({
            'company_id': self.company.id, 'source_key': 'comparison-new-later',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'LATER-1', 'date': '2026-12-20',
            'local_id': later.id, 'line_name': 'CALZADO',
            'quantity': 2, 'total_net': 44,
        })
        dashboard = self.env['analytics.sales.dashboard']
        args = {'establishment_id': self.est1.id, 'local_id': self.local1.id,
                'period': '30', 'scope': 'all'}
        response = dashboard.get_dashboard(args)
        # The selected local's metrics still use Nov 11 as the end date.
        self.assertEqual(response['date_to'], '2026-11-11')
        self.assertEqual(response['metrics']['sales'], 12)
        # El comparativo también sigue al nlocal (Nov 11), no el dato de Dic 20.
        chart = response['establishment_comparison']
        self.assertEqual([r['name'] for r in chart], [self.local1.name])
        self.assertEqual(chart[0]['sales'], 12)
        # Si el local se devuelve a Todos, suma todo Durán y adopta la última venta.
        all_locs = dashboard.get_dashboard(dict(args, local_id='all'))
        self.assertEqual(all_locs['date_to'], '2026-12-20')
        self.assertEqual([r['name'] for r in all_locs['establishment_comparison']], [self.est1.name])
        self.assertEqual(all_locs['establishment_comparison'][0]['sales'], 44)
        # Los rangos manuales siguen respetándose.
        custom = dashboard.get_dashboard(dict(args, period='custom',
            date_from='2026-11-01', date_to='2026-11-30'))
        custom_chart = custom['establishment_comparison']
        self.assertEqual([r['name'] for r in custom_chart], [self.local1.name])
        self.assertEqual(custom_chart[0]['sales'], 12)

    def test_supervisor_comparison_does_not_expand_authorized_local_scope(self):
        """Ver otros nlocal del establecimiento requiere permiso explícito."""
        local3 = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN NO AUTORIZADO', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, local3.id)]})
        self.env['analytics.sales.move'].sudo().create({
            'company_id': self.company.id, 'source_key': 'comparison-hidden-sale',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'C-4', 'date': '2026-11-11',
            'local_id': local3.id, 'line_name': 'CALZADO',
            'quantity': 1, 'total_net': 999,
        })
        supervisor = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name': 'Supervisor de establecimiento test',
            'login': 'test_supervisor_est_%s' % self.company.id,
            'company_id': self.company.id,
            'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.env['analytics.sales.user.access'].create({
            'user_id': supervisor.id, 'company_id': self.company.id,
            'role': 'supervisor', 'local_ids': [(6, 0, [self.local1.id])],
        })
        dashboard = self.env['analytics.sales.dashboard'].with_user(supervisor)
        result = dashboard.get_dashboard({
            'establishment_id': self.est1.id, 'local_id': self.local1.id,
            'date_from': '2026-11-01', 'date_to': '2026-11-30', 'scope': 'all'})
        self.assertEqual(result['metrics']['sales'], 12)
        self.assertEqual([r['name'] for r in result['establishment_comparison']], [self.local1.name])
        self.assertEqual(result['establishment_comparison'][0]['sales'], 12)
        self.assertNotIn('cost', result['establishment_comparison'][0])
        with self.assertRaises(AccessError):
            dashboard.get_dashboard({'establishment_id': self.est1.id, 'local_id': local3.id})

    def test_daily_history_only_real_data_with_variable_days(self):
        dashboard = self.env['analytics.sales.dashboard']
        common = {'establishment_id': self.est1.id, 'scope': 'all',
                  'date_from': '2026-11-01', 'date_to': '2026-11-30'}
        one = dashboard.get_dashboard(dict(common, history_days=1))['daily_history']
        self.assertEqual(one['history'], [{'date': '2026-11-11', 'sales': 12.0}])
        self.assertEqual(one['net_total'], 12)
        fifteen = dashboard.get_dashboard(dict(common, history_days=15))['daily_history']
        self.assertEqual(len(fifteen['history']), 11)  # Nov 1 through last real record Nov 11
        self.assertEqual(fifteen['history'][0], {'date': '2026-11-01', 'sales': 0.0})
        ninety = dashboard.get_dashboard(dict(common, history_days=90))['daily_history']
        self.assertTrue(all(x['date'] <= '2026-11-11' for x in ninety['history']))
        self.assertNotIn('forecast', ninety)
        self.assertNotIn('total_forecast', ninety)
        with self.assertRaises(ValidationError):
            dashboard.get_dashboard(dict(common, history_days=91))

    def test_store_establishments_do_not_expose_other_localities(self):
        store = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name': 'Tienda de establecimientos', 'login': 'test_store_est_%s' % self.company.id,
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.env['analytics.sales.user.access'].create({
            'user_id': store.id, 'company_id': self.company.id,
            'role': 'tienda', 'local_ids': [(6, 0, [self.local1.id])],
        })
        dashboard = self.env['analytics.sales.dashboard'].with_user(store)
        result = dashboard.get_dashboard({'date_from': '2026-11-01', 'date_to': '2026-11-30'})
        self.assertEqual(result['metrics']['sales'], 12)
        self.assertEqual([o['id'] for o in result['options']['establishments']], [self.est1.id])
        self.assertNotIn('cost', result['metrics'])
        # Tienda ve solo ventas de su nlocal autorizado agregadas bajo el establecimiento.
        self.assertEqual([r['name'] for r in result['establishment_comparison']], [self.est1.name])
        self.assertEqual(result['establishment_comparison'][0]['sales'], 12)
        self.assertNotIn('cost', result['establishment_comparison'][0])
        with self.assertRaises(AccessError):
            dashboard.get_dashboard({'establishment_id': self.est2.id})

    def test_annual_net_sales_sums_all_establishment_locals_and_returns(self):
        """Calculated field is not the manually entered target, and is year-scoped."""
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Real Durán', 'company_id': self.company.id,
            'year': 2026, 'establishment_id': self.est1.id,
        })
        self.assertEqual(goal.target_amount, 0)
        self.assertAlmostEqual(goal.annual_fa_sales, 12)
        self.assertAlmostEqual(goal.annual_de_sales, 0)
        self.assertAlmostEqual(goal.annual_net_sales, 12)
        self.assertEqual(goal.local_count, 1)

        sale = self.env['analytics.sales.move'].sudo()
        sale.create({
            'company_id': self.company.id, 'source_key': 'test-est-DE',
            'source_kind': 'historico', 'document_type': 'DE',
            'document_number': 'DE-1', 'date': '2026-11-12',
            'local_id': self.local1.id, 'quantity': 1, 'total_net': 5,
        })
        sale.create({
            'company_id': self.company.id, 'source_key': 'test-est-other-year',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'FA-2025', 'date': '2025-12-31',
            'local_id': self.local1.id, 'quantity': 1, 'total_net': 400,
        })
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.annual_fa_sales, 12)
        self.assertAlmostEqual(goal.annual_de_sales, 5)
        self.assertAlmostEqual(goal.annual_net_sales, 7)

        new_local = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST SEGUNDO DURAN', 'company_id': self.company.id,
        })
        self.est1.write({'local_ids': [(4, new_local.id)]})
        sale.create({
            'company_id': self.company.id, 'source_key': 'test-est-second-local',
            'source_kind': 'historico', 'document_type': 'FA',
            'document_number': 'FA-second', 'date': '2026-10-11',
            'local_id': new_local.id, 'quantity': 2, 'total_net': 20,
        })
        self.env.invalidate_all()
        self.assertEqual(goal.local_count, 2)
        self.assertAlmostEqual(goal.annual_net_sales, 27)
        goal.target_amount = 100
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.target_amount, 100)
        self.assertAlmostEqual(goal.distribution_amount, 0)  # no target entered: zero

    def test_annual_net_sales_updates_when_api_changes(self):
        """An annual/monthly API correction is visible without a stored snapshot."""
        goal = self.env['analytics.sales.goal'].create({
            'name': 'API Durán', 'company_id': self.company.id,
            'year': 2026, 'establishment_id': self.est1.id,
            'target_amount': 200,
        })
        self.assertAlmostEqual(goal.annual_net_sales, 12)
        sale = self.env['analytics.sales.move'].sudo()
        fa = sale.create({
            'company_id': self.company.id, 'source_key': 'test-api-annual-FA',
            'source_kind': 'api', 'document_type': 'FA',
            'document_number': 'FA-test', 'date': '2026-11-12',
            'local_id': self.local1.id, 'quantity': 2, 'total_net': 35,
        })
        sale.create({
            'company_id': self.company.id, 'source_key': 'test-api-annual-DE',
            'source_kind': 'api', 'document_type': 'DE',
            'document_number': 'DE-test', 'date': '2026-11-12',
            'local_id': self.local1.id, 'quantity': 1, 'total_net': 5,
        })
        self.env.invalidate_all()
        # When there is API data, historical Excel rows are not double counted.
        self.assertAlmostEqual(goal.annual_net_sales, 30)
        self.assertAlmostEqual(goal.annual_fa_sales, 35)
        self.assertAlmostEqual(goal.annual_de_sales, 5)
        fa.write({'total_net': 60})
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.annual_net_sales, 55)
        self.assertAlmostEqual(goal.target_amount, 200)
        # Explicit cancellation is omitted by normal active_test=True read_group.
        fa.write({'active': False})
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.annual_net_sales, -5)

    def test_annual_company_goal_when_establishment_is_unselected(self):
        goal = self.env['analytics.sales.goal'].create({
            'name': 'General anual real', 'company_id': self.company.id,
            'year': 2026,
        })
        self.assertAlmostEqual(goal.annual_net_sales, 42)
        goal.year = 2025
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.annual_net_sales, 0)

    def test_monthly_locals_and_seller_goals_change_with_api(self):
        """Detail in Metas groups months/nlocal/sellers and follows API corrections."""
        sale = self.env['analytics.sales.move'].sudo()
        sale.create({
            'company_id': self.company.id, 'source_key': 'monthly-seller-178',
            'source_kind': 'api', 'document_type': 'FA', 'date': '2026-11-11',
            'local_id': self.local1.id, 'seller': 'ANA TEST', 'seller_code': '178',
            'quantity': 2, 'total_net': 150, 'document_number': 'FA-11',
        })
        refund = sale.create({
            'company_id': self.company.id, 'source_key': 'monthly-refund-178',
            'source_kind': 'api', 'document_type': 'DE', 'date': '2026-11-12',
            'local_id': self.local1.id, 'seller': 'ANA TEST', 'seller_code': '178',
            'quantity': 1, 'total_net': 25, 'document_number': 'DE-11',
        })
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Metas Durán por mes y vendedor', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id,
            'target_amount': 1200,
        })
        self.assertAlmostEqual(goal.distribution_amount, 0)  # no target entered: zero
        self.assertAlmostEqual(goal.distribution_unassigned, 0)
        self.assertIn('Metas mensuales ingresadas', goal.distribution_method)
        self.assertIn('Noviembre', str(goal.monthly_local_report))
        # Los totales mensuales son del establecimiento, sin filas por local.
        self.assertNotIn(self.local1.name, str(goal.monthly_local_report))
        self.assertIn('ANA TEST', str(goal.monthly_seller_report))
        self.assertIn('Facturado FA', str(goal.monthly_seller_report))
        self.assertIn('Meta mensual asignada', str(goal.monthly_seller_report))
        self.assertIn('Cumplimiento', str(goal.monthly_seller_report))
        groups = goal._grouped_seller_sales(self.est1.local_ids.ids)
        self.assertEqual(sum(g['total_net'] for g in groups if g['document_type'] == 'FA'), 150)
        self.assertTrue(all(g['month'] == 11 for g in groups))

        refund.write({'total_net': 30})
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.annual_net_sales, 120)
        self.assertIn('120,00', str(goal.monthly_local_report))
        self.assertIn('120,00', str(goal.monthly_seller_report))

    def test_monthly_goal_without_manual_target_is_zero(self):
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Referencia ventas reales', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id,
        })
        self.assertAlmostEqual(goal.distribution_amount, 0)
        self.assertIn('Metas mensuales ingresadas', goal.distribution_method)
        self.assertEqual(goal.distribution_unassigned, 0)
        goal.target_amount = 900000
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.distribution_amount, 0)  # legacy value never overrides

    def test_editable_monthly_target_drives_equal_seller_distribution(self):
        """No auto-target on creation; editing January affects only January."""
        sales = self.env['analytics.sales.move'].sudo()
        # Two sellers; one visits both locals and still receives one quota.
        second = self.env['analytics.sales.local'].create({
            'name': 'SEGUNDO LOCAL META 137', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, second.id)]})
        for i, (local, code, amount) in enumerate((
                (self.local1, 'V1', 20), (second, 'V1', 10),
                (second, 'V2', 15)), 1):
            sales.create({
                'company_id': self.company.id, 'source_kind': 'api',
                'source_key': 'goal-137-%s' % i, 'document_type': 'FA',
                'date': '2026-01-10', 'local_id': local.id,
                'seller_code': code, 'seller': 'VENDEDOR ' + code,
                'quantity': 1, 'total_net': amount, 'document_number': 'META-%s' % i,
            })
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Metas mensuales editables', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id,
        })
        self.assertEqual(len(goal.monthly_line_ids), 12)
        self.assertEqual([line.month for line in goal.monthly_line_ids],
                         ['%02d' % n for n in range(1, 13)])
        self.assertAlmostEqual(goal.distribution_amount, 0.0)
        self.assertEqual(goal.monthly_line_ids.filtered(lambda l: l.month == '01').target_amount, 0)
        jan = goal.monthly_line_ids.filtered(lambda l: l.month == '01')
        jan.write({'target_amount': 1000.0})
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.distribution_amount, 1000.0)
        self.assertAlmostEqual(jan.fa_amount, 45.0)
        self.assertAlmostEqual(jan.net_amount, 45.0)
        self.assertEqual(jan.compliance, '4.5 %')
        feb = goal.monthly_line_ids.filtered(lambda l: l.month == '02')
        self.assertEqual(feb.target_amount, 0.0)
        self.assertEqual(feb.compliance, '—')
        report = str(goal.monthly_seller_report)
        self.assertIn('500,00', report)  # 1000 / 2
        self.assertIn('VENDEDOR V1', report)
        self.assertIn('VENDEDOR V2', report)
        self.assertNotIn('% de meta', report)
        jan.write({'target_amount': 0.0})
        self.env.invalidate_all()
        self.assertAlmostEqual(goal.distribution_amount, 0.0)

    def test_apply_one_target_to_all_months_and_clear_input(self):
        """Bulk button copies one editable target to twelve months, then clears input."""
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Meta anual sin automatismos', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id,
        })
        self.assertEqual(len(goal.monthly_line_ids), 12)
        self.assertTrue(all(line.target_amount == 0 for line in goal.monthly_line_ids))
        goal.write({'bulk_monthly_target': '1.000,50'})
        action = goal.action_apply_monthly_target()
        self.assertEqual(action['tag'], 'reload')
        self.assertFalse(goal.bulk_monthly_target)
        self.assertTrue(all(abs(line.target_amount - 1000.50) < 0.001
                            for line in goal.monthly_line_ids))
        # Bulk edit does not lock the twelve individual monthly target cells.
        goal.monthly_line_ids.filtered(lambda line: line.month == '02').write({
            'target_amount': 1200.0})
        self.assertEqual(goal.monthly_line_ids.filtered(
            lambda line: line.month == '02').target_amount, 1200.0)
        goal.write({'bulk_monthly_target': '0'})
        goal.action_apply_monthly_target()
        self.assertTrue(all(line.target_amount == 0 for line in goal.monthly_line_ids))
        self.assertFalse(goal.bulk_monthly_target)
        goal.write({'bulk_monthly_target': '-20'})
        with self.assertRaises(ValidationError):
            goal.action_apply_monthly_target()

    def test_upgrade_migrates_legacy_month_fields_without_overwriting(self):
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Mes legado', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id,
            'monthly_goal_04': 678.25,
        })
        # A new goal seeds rows at zero; upgrading legacy goals with an absent
        # row transfers its old manual amount exactly once.
        april = goal.monthly_line_ids.filtered(lambda l: l.month == '04')
        april.sudo().unlink()
        goal._ensure_month_rows()
        april = goal.monthly_line_ids.filtered(lambda l: l.month == '04')
        self.assertAlmostEqual(april.target_amount, 678.25)
        april.write({'target_amount': 123.45})
        goal._ensure_month_rows()
        self.assertAlmostEqual(april.target_amount, 123.45)

    def test_establishment_lists_sellers_from_related_locals(self):
        """El maestro muestra vendedores, sin incluir otros establecimientos."""
        second = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN OTRA', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, second.id)]})
        moves = self.env['analytics.sales.move'].sudo()
        for index, local in enumerate((self.local1, second, self.local2), 1):
            moves.create({
                'company_id': self.company.id, 'source_kind': 'historico',
                'source_key': 'est-sellers-24-%s' % index,
                'document_type': 'FA', 'document_number': 'FA-SE-%s' % index,
                'date': '2026-09-01', 'local_id': local.id,
                'seller_code': 'S001' if index < 3 else 'S099',
                'seller': 'VENDEDORA DURAN' if index < 3 else 'VENDEDOR AJENO',
                'quantity': 1, 'total_net': 10,
            })
        self.env.invalidate_all()
        self.assertEqual(self.est1.seller_count, 1)
        html = str(self.est1.seller_report)
        self.assertIn('VENDEDORA DURAN', html)
        self.assertIn('S001', html)
        self.assertIn(self.local1.name, html)
        self.assertIn(second.name, html)
        self.assertNotIn('VENDEDOR AJENO', html)
        # Una fila por persona; todos sus locales aparecen en la misma celda.
        from lxml import html as lxml_html
        table = lxml_html.fromstring(html).xpath('//table')[0]
        self.assertEqual(len(table.xpath('./thead/tr/th')), 3)
        self.assertEqual([col.text_content().strip() for col in table.xpath('./thead/tr/th')],
                         ['Vendedor', 'Código', 'Locales'])
        rows = table.xpath('./tbody/tr')
        self.assertEqual(len(rows), 1)
        self.assertEqual([cell.text_content().strip() for cell in rows[0].xpath('./td')],
                         ['VENDEDORA DURAN', 'S001',
                          ', '.join(sorted([self.local1.name, second.name], key=str.casefold))])
        self.assertEqual(html.count('VENDEDORA DURAN'), 1)

    def test_establishment_label_hides_c_slash_without_changing_nlocal(self):
        """El prefijo C/ sólo se omite en la presentación del local."""
        original_name = self.local1.name
        self.local1.name = 'C/ Rotonda 001-050'
        self.env.invalidate_all()
        html = str(self.est1.seller_report)
        self.assertIn('Rotonda 001-050', html)
        self.assertNotIn('Local (nlocal): C/', html)
        self.assertEqual(self.local1.name, 'C/ Rotonda 001-050')
        # Generar una venta real para que el informe incluya el encabezado
        # agrupado del local y de su vendedor.
        self.env['analytics.sales.move'].sudo().create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'etiqueta-local-c-slash',
            'document_type': 'FA', 'document_number': 'FA-LOCAL-C',
            'date': '2026-10-01', 'local_id': self.local1.id,
            'seller_code': 'TESTC', 'seller': 'VENDEDOR ETIQUETA',
            'quantity': 1, 'total_net': 10,
        })
        self.env.invalidate_all()
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Prueba etiqueta local', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id})
        report = str(goal.monthly_seller_report)
        self.assertNotIn('Local:', report)
        self.assertIn('VENDEDOR ETIQUETA', report)
        self.assertNotIn('Local (nlocal): C/', report)
        self.local1.name = original_name

    def test_goals_grouped_by_establishment_and_equal_seller_percent(self):
        """Un vendedor en varios nlocal no recibe dos porcentajes."""
        second = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST DURAN VENDEDOR', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, second.id)]})
        moves = self.env['analytics.sales.move'].sudo()
        for seq, (local, code, name, amount) in enumerate((
                (self.local1, '11', 'ANA', 30),
                (self.local1, '12', 'BRUNO', 20),
                (second, '12', 'BRUNO', 25),
                (second, '13', 'CARLA', 10),
                (second, '', '', 5),
        ), 1):
            moves.create({
                'company_id': self.company.id, 'source_kind': 'historico',
                'source_key': 'est-quota-24-%s' % seq,
                'document_type': 'FA', 'document_number': 'EST-Q-%s' % seq,
                'date': '2026-10-01', 'local_id': local.id,
                'seller_code': code, 'seller': name,
                'quantity': 1, 'total_net': amount,
            })
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Duran distribuido', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id})
        self.env.invalidate_all()
        self.assertIn('Establecimiento: Durán test — Año 2026', str(goal.monthly_local_report))
        self.assertIn('Durán test', str(goal.annual_establishment_report))
        report = str(goal.monthly_seller_report)
        self.assertIn('Año 2026', report)
        self.assertNotIn('Local:', report)
        self.assertIn('ANA', report)
        self.assertIn('BRUNO', report)
        self.assertIn('CARLA', report)
        data = goal._grouped_seller_sales(self.est1.local_ids.ids)
        value = build_monthly_goals(
            {local.id: local.name for local in self.est1.local_ids}, data,
            goal.annual_net_sales)
        self.assertEqual(value['seller_count'], 3)
        self.assertEqual(len(value['annual_sellers']), 3)
        self.assertEqual(sum(s['goal_cents'] for s in value['annual_sellers']),
                         value['annual_goal_cents'])
        self.assertEqual(value['unassigned_cents'], 0)

    def test_company_goal_annual_and_monthly_are_separated_by_establishment(self):
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Metas anuales empresa', 'year': 2026, 'company_id': self.company.id})
        annual = str(goal.annual_establishment_report)
        monthly = str(goal.monthly_local_report)
        self.assertIn('Durán test', annual)
        self.assertIn('Alborada test', annual)
        self.assertIn('Establecimiento: Durán test', monthly)
        self.assertIn('Establecimiento: Alborada test', monthly)

    def test_monthly_goal_is_equal_for_each_seller_even_with_multiple_locals(self):
        """Reparto mensual equitativo; multi-local no multiplica la meta."""
        multi_local = self.env['analytics.sales.local'].create({
            'name': 'LOCAL TEST ROTONDA AUXILIAR', 'company_id': self.company.id})
        self.est1.write({'local_ids': [(4, multi_local.id)]})
        move_model = self.env['analytics.sales.move'].sudo()
        for seq, (local, code, name, amount) in enumerate((
                (self.local1, '11', 'ANA', 50.01),
                (self.local1, '12', 'BRUNO', 20),
                (multi_local, '12', 'BRUNO', 25),
                (multi_local, '13', 'CARLA', 5),
        ), 1):
            move_model.create({
                'company_id': self.company.id, 'source_kind': 'historico',
                'source_key': 'meta-seller-equal-v127-%s' % seq,
                'document_type': 'FA', 'document_number': 'M127-%s' % seq,
                'date': '2026-10-01', 'local_id': local.id,
                'seller_code': code, 'seller': name,
                'quantity': 1, 'total_net': amount,
            })
        goal = self.env['analytics.sales.goal'].create({
            'name': 'Meta mensual por vendedor', 'year': 2026,
            'company_id': self.company.id, 'establishment_id': self.est1.id})
        rows = goal._grouped_seller_sales(self.est1.local_ids.ids)
        bd = build_monthly_goals({local.id: local.name for local in self.est1.local_ids},
                                 rows, goal.annual_net_sales)
        self.assertEqual(bd['seller_count'], 3)
        self.assertEqual(len(bd['months']), 12)
        for month in bd['months']:
            vendor_rows = [s for s in month['sellers'] if not s.get('unassigned')]
            self.assertEqual(len(vendor_rows), 3)
            self.assertLessEqual(max(s['goal_cents'] for s in vendor_rows) -
                                 min(s['goal_cents'] for s in vendor_rows), 1)
            self.assertEqual(sum(s['goal_cents'] for s in vendor_rows),
                             month['goal_cents'])
            self.assertEqual(len([s for s in vendor_rows if s['name'] == 'BRUNO']), 1)
        self.assertEqual(sum(s['goal_cents'] for s in bd['annual_sellers']),
                         bd['annual_goal_cents'])
        html = str(goal.monthly_seller_report)
        self.assertNotIn('Local:', html)
        self.assertIn('Vendedor', html)
        self.assertIn('% de meta', html)
        self.assertIn('Facturado FA', html)
        self.assertIn('Devuelto DE', html)
        self.assertIn('Ventas netas', html)
        self.assertIn('Meta mensual asignada', html)
        self.assertIn('Cumplimiento', html)
        self.assertNotIn(self.local1.name, html)
        self.assertNotIn(multi_local.name, html)
        self.assertNotIn('<th>Establecimiento</th>', html)
        # 7 columnas sin Local, Código ni Establecimiento.
        from lxml import html as lxml_html
        table = lxml_html.fromstring(html).xpath('//table')[0]
        self.assertEqual(len(table.xpath('./colgroup/col')), 7)
        self.assertEqual(len(table.xpath('./thead/tr/th')), 7)
        self.assertTrue(all(len(row.xpath('./td')) == 7
                            for row in table.xpath('./tbody/tr')
                            if row.xpath('./td') and not row.xpath('./td[@colspan]')))
        # Una sola cabecera por mes; cada vendedor aparece una vez por mes.
        self.assertEqual(len(table.xpath('./tbody/tr[@class="table-secondary"]')), 12)
        self.assertFalse(table.xpath('./tbody/tr[@class="table-light"]'))
        self.assertEqual(len(table.xpath('./tbody/tr/td[text()="BRUNO"]')), 12)
        self.assertEqual(len(table.xpath('./tbody/tr/td[text()="ANA"]')), 12)
        self.assertEqual(len(table.xpath('./tbody/tr/td[text()="CARLA"]')), 12)
        self.assertEqual(table.xpath('./thead/tr/th')[1].text_content().strip(),
                         '% de meta')
        self.assertIn('33,33 %', html)
        # Distribución por mes: 12 filas, sin ninguna fila por local.
        monthly = lxml_html.fromstring(str(goal.monthly_local_report)).xpath('//table')[0]
        self.assertEqual(len(monthly.xpath('./thead/tr/th')), 6)
        self.assertEqual(len(monthly.xpath('./tbody/tr/td')), 12 * 5)
        self.assertEqual(len(monthly.xpath('./tbody/tr/th[@scope="row"]')), 12)
        self.assertNotIn(self.local1.name, str(goal.monthly_local_report))
        self.assertNotIn(multi_local.name, str(goal.monthly_local_report))

    def test_goal_form_has_separate_month_and_seller_reports(self):
        """Ambas distribuciones son pestañas independientes, sin resumen anual."""
        from lxml import etree
        view = self.env.ref('analytics_sales.view_analytics_sales_goal_form')
        root = etree.fromstring(view.arch_db.encode('utf-8'))
        pages = root.xpath('//notebook/page')
        self.assertEqual([page.get('string') for page in pages],
                         ['Distribución por mes', 'Distribución por vendedor'])
        self.assertEqual(pages[0].xpath('.//field[@name="monthly_local_report"]') != [], True)
        self.assertEqual(pages[1].xpath('.//field[@name="monthly_seller_report"]') != [], True)
        self.assertFalse(root.xpath('//field[@name="annual_establishment_report"]'))

    def test_goals_dashboard_all_establishments_expandable_and_targets_independent(self):
        """Todos muestra cada establecimiento con sus vendedores y cuotas propias."""
        goal_model = self.env['analytics.sales.goal'].sudo()
        goal_duran = goal_model.create({
            'name': 'Test dashboard meta Durán', 'company_id': self.company.id,
            'establishment_id': self.est1.id, 'year': 2026,
        })
        goal_alborada = goal_model.create({
            'name': 'Test dashboard meta Alborada', 'company_id': self.company.id,
            'establishment_id': self.est2.id, 'year': 2026,
        })
        goal_duran.monthly_line_ids.filtered(lambda row: row.month == '11').write({'target_amount': 900.0})
        goal_alborada.monthly_line_ids.filtered(lambda row: row.month == '11').write({'target_amount': 600.0})
        move_model = self.env['analytics.sales.move'].sudo()
        move_model.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'test-goals-all-duran-1', 'document_type': 'FA',
            'document_number': 'TEST-GOAL-ALL-D1', 'date': '2026-11-12',
            'local_id': self.local1.id, 'seller': 'VENDEDOR DURAN',
            'seller_code': 'TEST-ALL-D', 'quantity': 1, 'total_net': 45.0,
        })
        move_model.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'test-goals-all-alborada-1', 'document_type': 'FA',
            'document_number': 'TEST-GOAL-ALL-A1', 'date': '2026-11-12',
            'local_id': self.local2.id, 'seller': 'VENDEDOR ALBORADA',
            'seller_code': 'TEST-ALL-A', 'quantity': 1, 'total_net': 55.0,
        })
        dashboard = self.env['analytics.sales.dashboard']
        value = dashboard.get_dashboard({
            'establishment_id': 'all', 'scope': 'all',
            'date_from': '2026-11-01', 'date_to': '2026-11-30',
        })['goal_dashboard']
        self.assertTrue(value['available'])
        self.assertTrue(value['all_establishments'])
        items = {entry['establishment_id']: entry for entry in value['establishments']}
        self.assertIn(self.est1.id, items)
        self.assertIn(self.est2.id, items)
        self.assertEqual(items[self.est1.id]['target'], 900.0)
        self.assertEqual(items[self.est2.id]['target'], 600.0)
        self.assertTrue(any(seller['name'] == 'VENDEDOR DURAN'
                            for seller in items[self.est1.id]['sellers']))
        self.assertFalse(any(seller['name'] == 'VENDEDOR ALBORADA'
                             for seller in items[self.est1.id]['sellers']))
        self.assertEqual(value['target'], sum(item['target'] for item in value['establishments']))
        self.assertEqual(value['actual'], round(sum(item['actual'] for item in value['establishments']), 2))
        self.assertEqual(items[self.est1.id]['actual'], 57.0)
        self.assertEqual(items[self.est2.id]['actual'], 85.0)
        selected = dashboard.get_dashboard({
            'establishment_id': self.est1.id, 'scope': 'all',
            'date_from': '2026-11-01', 'date_to': '2026-11-30',
        })['goal_dashboard']
        self.assertTrue(selected['available'])
        self.assertFalse(selected['all_establishments'])
        self.assertEqual(len(selected['establishments']), 1)
        self.assertEqual(selected['establishments'][0]['establishment_id'], self.est1.id)

    def test_goals_dashboard_all_includes_locals_without_establishment(self):
        """Unassigned locals have their own accordion, real sales and no invented goals."""
        other = self.env['analytics.sales.local'].create({
            'name': 'MAESTRO TEST SIN ESTABLECIMIENTO', 'company_id': self.company.id,
        })
        # A seller of the orphan local may also sell in an assigned location;
        # each row must be scoped to the corresponding locality group.
        sale = self.env['analytics.sales.move'].sudo()
        sale.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'test-unassigned-FA', 'document_type': 'FA',
            'document_number': 'TEST-ORPHAN-FA', 'date': '2026-11-12',
            'local_id': other.id, 'seller': 'VENDEDOR SIN ESTABLECIMIENTO',
            'seller_code': 'TEST-ORPHAN-1', 'quantity': 2, 'total_net': 88.0,
        })
        sale.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'test-unassigned-DE', 'document_type': 'DE',
            'document_number': 'TEST-ORPHAN-DE', 'date': '2026-11-13',
            'local_id': other.id, 'seller': 'VENDEDOR SIN ESTABLECIMIENTO',
            'seller_code': 'TEST-ORPHAN-1', 'quantity': 1, 'total_net': 10.0,
        })
        dashboard = self.env['analytics.sales.dashboard']
        params = {'establishment_id': 'all', 'scope': 'all',
                  'date_from': '2026-11-01', 'date_to': '2026-11-30'}
        data = dashboard.get_dashboard(params)
        result = data['goal_dashboard']
        self.assertTrue(result['available'])
        groups = {item['establishment_id']: item for item in result['establishments']}
        self.assertIn('unassigned', groups)
        self.assertIn(self.est1.id, groups)
        self.assertIn(self.est2.id, groups)
        orphan = groups['unassigned']
        self.assertEqual(orphan['establishment_name'], 'Sin establecimiento')
        self.assertAlmostEqual(orphan['actual'], 78.0)
        self.assertEqual(orphan['target'], 0.0)
        self.assertEqual(orphan['seller_count'], 1)
        self.assertEqual(orphan['sellers'][0]['name'], 'VENDEDOR SIN ESTABLECIMIENTO')
        self.assertEqual(orphan['sellers'][0]['target'], 0.0)
        self.assertAlmostEqual(orphan['sellers'][0]['actual'], 78.0)
        self.assertTrue(all(item['name'] != 'VENDEDOR SIN ESTABLECIMIENTO'
                            for item in groups[self.est1.id]['sellers']))
        self.assertAlmostEqual(result['actual'],
                               sum(group['actual'] for group in result['establishments']))
        self.assertAlmostEqual(result['actual'], 120.0)

        # When a specific establishment is selected, unassigned locals
        # never leak into the result.
        selected = dashboard.get_dashboard(dict(params, establishment_id=self.est1.id))
        self.assertEqual(len(selected['goal_dashboard']['establishments']), 1)
        self.assertNotIn('Sin establecimiento',
                         [g['establishment_name'] for g in selected['goal_dashboard']['establishments']])

        # A supervisor limited to the orphan local sees only that group.
        restricted = dashboard._goal_dashboard(
            self.company, 'historico', (self.est1 | self.est2), False,
            {other.id}, '2026-11-01', '2026-11-30', 'supervisor', 'custom',
        )
        self.assertEqual([g['establishment_id'] for g in restricted['establishments']],
                         ['unassigned'])
        self.assertAlmostEqual(restricted['actual'], 78.0)

    def test_goals_dashboard_all_respects_allowed_locals(self):
        """Nunca mostrar otro establecimiento si no tiene locales autorizados."""
        dashboard = self.env['analytics.sales.dashboard']
        value = dashboard._goal_dashboard(
            self.company, 'historico', (self.est1 | self.est2), False,
            {self.local1.id}, '2026-11-01', '2026-11-30',
            'supervisor', 'custom',
        )
        self.assertTrue(value['available'])
        self.assertEqual([est['establishment_id'] for est in value['establishments']],
                         [self.est1.id])

    def test_goals_real_sales_match_main_net_sales_under_all_commercial_filters(self):
        """Regression: Metas' Venta real cannot ignore Moda, line, brand or seller.

        Only the planned target is independent; both actual sales readings must
        use the same filtered FA/DE moves, whether viewing one or all groups.
        """
        sale = self.env['analytics.sales.move'].sudo()
        base = {
            'company_id': self.company.id,
            'source_kind': 'historico',
            'local_id': self.local1.id,
            'date': '2026-11-12',
            'quantity': 1,
        }
        sale.create(dict(base, document_type='FA', document_number='AS-152-FASHION',
                         source_key='goals-152-fashion', line_name='CALZADO',
                         brand='MARCA FILTRADA', seller='Vendedor A', seller_code='A-152',
                         total_net=100.0))
        sale.create(dict(base, document_type='DE', document_number='AS-152-RETURN',
                         source_key='goals-152-return', line_name='CALZADO',
                         brand='MARCA FILTRADA', seller='Vendedor A', seller_code='A-152',
                         total_net=15.0))
        sale.create(dict(base, document_type='FA', document_number='AS-152-OTHER',
                         source_key='goals-152-other', line_name='VARIOS',
                         brand='OTRA MARCA', seller='Vendedor B', seller_code='B-152',
                         total_net=1500.0))
        dashboard = self.env['analytics.sales.dashboard']
        common = {
            'date_from': '2026-11-01', 'date_to': '2026-11-30',
            'establishment_id': self.est1.id,
        }
        variants = (
            {'scope': 'moda'},
            {'scope': 'all'},
            {'scope': 'all', 'line': 'CALZADO'},
            {'scope': 'all', 'brand': 'MARCA FILTRADA'},
            {'scope': 'all', 'seller': 'Vendedor A'},
            {'scope': 'all', 'local_id': self.local1.id},
        )
        for changed in variants:
            data = dashboard.get_dashboard(dict(common, **changed))
            goal = data['goal_dashboard']
            self.assertTrue(goal['available'])
            self.assertAlmostEqual(goal['actual'], data['metrics']['sales'], places=2,
                                   msg='Filters %s must use exactly the same sales.' % changed)
            self.assertAlmostEqual(sum(group['actual'] for group in goal['establishments']),
                                   data['metrics']['sales'], places=2)
        by_seller = dashboard.get_dashboard(dict(common, scope='all', seller='Vendedor A'))
        self.assertEqual([seller['name'] for seller in by_seller['goal_dashboard']['sellers']],
                         ['Vendedor A'])
        self.assertAlmostEqual(by_seller['goal_dashboard']['sellers'][0]['actual'], 85.0)

    def test_goals_all_establishments_and_unassigned_match_main_net_sales(self):
        """General: all groups, including unassigned, must sum to main Venta neta."""
        orphan = self.env['analytics.sales.local'].create({
            'name': 'SIN ESTABLECIMIENTO 152', 'company_id': self.company.id,
        })
        sale = self.env['analytics.sales.move'].sudo()
        sale.create({
            'company_id': self.company.id, 'source_kind': 'historico',
            'source_key': 'goals-152-unassigned', 'document_type': 'FA',
            'document_number': 'ORPHAN-152', 'date': '2026-11-13',
            'local_id': orphan.id, 'line_name': 'VARIOS', 'brand': 'OTRA MARCA',
            'seller': 'Vendedor sin establecimiento', 'seller_code': 'O-152',
            'quantity': 1, 'total_net': 999.0,
        })
        dashboard = self.env['analytics.sales.dashboard']
        params = {'establishment_id': 'all', 'scope': 'moda',
                  'date_from': '2026-11-01', 'date_to': '2026-11-30'}
        for scope in ('moda', 'all'):
            data = dashboard.get_dashboard(dict(params, scope=scope))
            goal = data['goal_dashboard']
            self.assertTrue(goal['all_establishments'])
            self.assertAlmostEqual(goal['actual'], data['metrics']['sales'])
            self.assertAlmostEqual(sum(group['actual'] for group in goal['establishments']),
                                   data['metrics']['sales'])
        # Selecting a locality under Todos no longer adds unrelated groups.
        only_local = dashboard.get_dashboard(dict(params, scope='all', local_id=self.local1.id))
        self.assertAlmostEqual(only_local['goal_dashboard']['actual'],
                               only_local['metrics']['sales'])
        self.assertEqual([g['establishment_id']
                          for g in only_local['goal_dashboard']['establishments']],
                         [self.est1.id])

    def test_goals_flat_sellers_merge_without_redistributing_quotas(self):
        """One seller per identity across groups; selected establishment stays scoped."""
        orphan = self.env['analytics.sales.local'].create({
            'name': 'SIN ESTABLECIMIENTO 160', 'company_id': self.company.id,
        })
        for est, amount in ((self.est1, 900.0), (self.est2, 600.0)):
            goal = self.env['analytics.sales.goal'].create({
                'name': 'Meta listado 160 ' + est.name,
                'company_id': self.company.id, 'establishment_id': est.id, 'year': 2026,
            })
            goal.monthly_line_ids.filtered(lambda row: row.month == '11').write({'target_amount': amount})
        move = self.env['analytics.sales.move'].sudo()
        base = {'company_id': self.company.id, 'source_kind': 'historico',
                'date': '2026-11-12', 'document_type': 'FA',
                'line_name': 'CALZADO', 'quantity': 1}
        for index, (local, name, code, amount) in enumerate((
            (self.local1, 'Compartido', 'SHARED-160', 90.0),
            (self.local2, 'Compartido', 'SHARED-160', 50.0),
            (self.local2, 'Solo Alborada', 'OTHER-160', 20.0),
            (orphan, 'Sin establecimiento', 'ORPHAN-160', 30.0),
        )):
            move.create(dict(base, local_id=local.id, seller=name, seller_code=code,
                             total_net=amount, document_number='F-160-%s' % index,
                             source_key='flat-goals-160-%s' % index))
        dashboard = self.env['analytics.sales.dashboard']
        params = {'establishment_id': 'all', 'scope': 'all',
                  'date_from': '2026-11-01', 'date_to': '2026-11-30'}
        data = dashboard.get_dashboard(params)
        goal = data['goal_dashboard']
        rows = {r['code']: r for r in goal['sellers']}
        self.assertEqual(len([r for r in goal['sellers'] if r['code'] == 'SHARED-160']), 1)
        shared = rows['SHARED-160']
        components = [r for entry in goal['establishments'] for r in entry['sellers']
                      if r['code'] == 'SHARED-160']
        self.assertEqual(shared['target'], round(sum(r['target'] for r in components), 2))
        self.assertEqual(shared['actual'], 140.0)
        self.assertEqual(shared['compliance'], round(140.0 / shared['target'] * 100, 2))
        self.assertEqual(rows['ORPHAN-160']['target'], 0.0)
        self.assertEqual(rows['ORPHAN-160']['actual'], 30.0)
        self.assertEqual(goal['seller_count'], len(goal['sellers']))
        self.assertAlmostEqual(goal['actual'], data['metrics']['sales'], places=2)
        selected = dashboard.get_dashboard(dict(params, establishment_id=self.est1.id))['goal_dashboard']
        self.assertNotIn('OTHER-160', [r['code'] for r in selected['sellers']])
        self.assertNotIn('ORPHAN-160', [r['code'] for r in selected['sellers']])
        self.assertEqual(next(r['actual'] for r in selected['sellers'] if r['code'] == 'SHARED-160'), 90.0)
        restricted = dashboard._goal_dashboard(
            self.company, 'historico', self.est1 | self.est2, False,
            {self.local1.id}, '2026-11-01', '2026-11-30', 'supervisor', 'custom')
        self.assertNotIn('OTHER-160', [r['code'] for r in restricted['sellers']])
        self.assertNotIn('ORPHAN-160', [r['code'] for r in restricted['sellers']])
        self.assertEqual(next(r['actual'] for r in restricted['sellers'] if r['code'] == 'SHARED-160'), 90.0)
