# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, AccessError

from ..models.warehouse import _warehouse_rows


class TestAnalyticsSalesWarehouse(TransactionCase):
    def setUp(self):
        super().setUp()
        self.company = self.env.company
        self.env.user.sudo().write({'groups_id': [(4, self.env.ref('analytics_sales.group_analytics_sales_admin').id)]})
        self.bodegas = self.env['analytics.sales.warehouse'].sudo()
        self.local = self.env['analytics.sales.local'].sudo().create({'name': 'LOCAL PRUEBA BODEGAS', 'company_id': self.company.id})
        self.est = self.env['analytics.sales.establishment'].sudo().create({
            'name': 'EST PRUEBA BODEGAS', 'company_id': self.company.id, 'local_ids': [(6, 0, self.local.ids)]})

    def test_normalize_and_duplicates(self):
        source = {'Bodega': '0001', 'nBodega': ' Bodega Centro   ', 'Stock': '240.50', 'Valor': '1220.560487'}
        rows = _warehouse_rows([source, source])
        self.assertEqual(rows, [{'code': '0001', 'name': 'Bodega Centro', 'stock': 240.5, 'value': 1220.560487}])
        with self.assertRaises(ValidationError):
            _warehouse_rows([source, dict(source, Valor=5)])
        for invalid in (None, [], [dict(source, Valor='nan')], [dict(source, Stock=None)]):
            with self.assertRaises(ValidationError):
                _warehouse_rows(invalid)

    def test_merge_preserves_assignment_and_absent_warehouses(self):
        data = [{'Bodega': 'AS-BOD-A', 'nBodega': 'A', 'Stock': 20, 'Valor': 100},
                {'Bodega': 'AS-BOD-B', 'nBodega': 'B', 'Stock': 4, 'Valor': 40}]
        first = self.bodegas._merge_warehouse_rows(data, self.company)
        self.assertEqual(first['created'], 2)
        a = self.bodegas.search([('company_id', '=', self.company.id), ('code', '=', 'AS-BOD-A')])
        a.establishment_id = self.est
        result = self.bodegas._merge_warehouse_rows([dict(data[0], Valor=175)], self.company)
        self.assertEqual(result['created'], 0)
        self.assertEqual(a.establishment_id, self.est)
        self.assertEqual(a.value, 175)
        dashboard = self.bodegas._dashboard_warehouses(self.company, self.est.id)
        self.assertEqual(dashboard['value'], 175)
        self.assertEqual(dashboard['count'], 1)
        all_data = self.bodegas._dashboard_warehouses(self.company, False)
        b = self.bodegas.search([('company_id', '=', self.company.id), ('code', '=', 'AS-BOD-B')])
        self.assertEqual(b.value, 40)
        self.assertTrue(any(group['id'] == 0 and any(w['code'] == 'AS-BOD-B' for w in group['warehouses']) for group in all_data['groups']))

    def test_direct_groups_without_local(self):
        est = self.env['analytics.sales.establishment'].sudo().create({
            'name': 'EST BODEGA SIN LOCAL', 'company_id': self.company.id})
        data = [{'Bodega': 'DIR-A', 'nBodega': 'A', 'Stock': 1, 'Valor': 125},
                {'Bodega': 'DIR-B', 'nBodega': 'B', 'Stock': 2, 'Valor': 75},
                {'Bodega': 'DIR-C', 'nBodega': 'C', 'Stock': 3, 'Valor': 50}]
        self.bodegas._merge_warehouse_rows(data, self.company)
        a, b, c = [self.bodegas.search([('company_id', '=', self.company.id), ('code', '=', row['Bodega'])]) for row in data]
        (a | b).write({'establishment_id': est.id})
        c.establishment_id = self.est
        subset = self.bodegas._dashboard_warehouses(self.company, est.id)
        self.assertEqual(subset['value'], 200)
        self.assertEqual(subset['count'], 2)
        self.assertEqual(len(subset['groups']), 1)
        self.assertEqual({w['code'] for w in subset['groups'][0]['warehouses']}, {'DIR-A', 'DIR-B'})
        self.assertNotIn('locals', subset['groups'][0])

    def test_real_contract_and_selector(self):
        from ..models.sync import _unwrap
        payload = {'success': True, 'session_id': '', 'data': [
            {'Bodega': 'REAL-A', 'nBodega': 'DURAN   ', 'Stock': '2000.00', 'Valor': '22273.378660'},
            {'Bodega': 'REAL-B', 'nBodega': 'IDR ALBORADA   ', 'Stock': '2783.50', 'Valor': '50865.303478'},
        ]}
        self.bodegas._merge_warehouse_rows(_unwrap(payload), self.company)
        records = self.bodegas.search([('company_id', '=', self.company.id), ('code', 'in', ['REAL-A', 'REAL-B'])])
        self.est.write({'warehouse_ids': [(6, 0, records.ids)]})
        self.assertEqual(records.mapped('establishment_id'), self.est)
        self.assertEqual(self.est.warehouse_ids, records)
        dashboard = self.bodegas._dashboard_warehouses(self.company, self.est.id)
        self.assertEqual(dashboard['stock'], 4783.5)
        self.assertEqual(dashboard['value'], 73138.68)
        self.assertAlmostEqual(records.filtered(lambda w: w.code == 'REAL-A').value, 22273.378660, places=6)
        other = self.env['analytics.sales.establishment'].sudo().create({'name': 'Other warehouse', 'company_id': self.company.id})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            other.write({'warehouse_ids': [(6, 0, records.ids)]})
        self.est.write({'warehouse_ids': [(6, 0, records[:1].ids)]})
        self.assertFalse(records[1].establishment_id)
        self.assertTrue(records[0].establishment_id)

    def test_odoo18_display_name_and_access(self):
        self.bodegas._merge_warehouse_rows([
            {'Bodega': 'ODOO18-01', 'nBodega': 'Centro', 'Stock': 1, 'Valor': 10},
        ], self.company)
        warehouse = self.bodegas.search([
            ('company_id', '=', self.company.id), ('code', '=', 'ODOO18-01')])
        self.assertEqual(warehouse.display_name, 'ODOO18-01 · Centro')
        user = self.env['res.users'].sudo().with_context(no_reset_password=True).create({
            'name': 'Analytics 18 sin permisos', 'login': 'analytics18_warehouse_no_access',
            'company_id': self.company.id, 'company_ids': [(6, 0, self.company.ids)],
            'groups_id': [(6, 0, self.env.ref('base.group_user').ids)],
        })
        restricted = warehouse.with_user(user).sudo(False)
        self.assertFalse(restricted.has_access('read'))
        with self.assertRaises(AccessError):
            restricted.check_access('read')
        with self.assertRaises(AccessError):
            restricted.browse().search([])

    def test_warehouse_cron_is_independent(self):
        job = self.env.ref('analytics_sales.ir_cron_analytics_sales_warehouses')
        self.assertEqual(job.interval_number, 1)
        self.assertEqual(job.interval_type, 'days')
        self.assertEqual(job.code, 'model.cron_sync_warehouses()')
        self.assertNotIn(job.id, self.env['analytics.sales.sync']._sales_cron_records().ids)


    def test_daily_cron_upgrades_existing_job(self):
        job = self.env.ref('analytics_sales.ir_cron_analytics_sales_warehouses')
        nextcall = job.nextcall
        job.write({'interval_number': 5, 'interval_type': 'hours', 'active': False})
        self.env['analytics.sales.sync'].configure_warehouse_cron()
        self.assertEqual((job.interval_number, job.interval_type), (1, 'days'))
        self.assertEqual(job.nextcall, nextcall)
        self.assertTrue(job.active)

    def test_manual_refresh_runs_all_three_even_on_partial_error(self):
        from unittest.mock import patch
        sync = self.env['analytics.sales.sync']
        called = []

        def sales(recordset, company, origin, kind):
            called.append(kind)
            if kind == 'annual':
                return {'error': 'API error', 'rows': 0, 'created': 0, 'updated': 0, 'removed': 0}
            return {'rows': 10, 'created': 3, 'updated': 7, 'removed': 0}

        def warehouse(recordset, company):
            called.append('warehouse')
            return {'rows': 9, 'created': 1, 'updated': 8, 'removed': 0}

        with patch.object(type(sync), '_run', sales), patch.object(type(sync), '_run_warehouse', warehouse):
            result = sync.action_sync_now()
        self.assertEqual(called, ['annual', 'monthly', 'warehouse'])
        self.assertEqual(result['rows'], 10)
        self.assertEqual(result['warehouse']['rows'], 9)
        self.assertIn('API error', result['error'])
