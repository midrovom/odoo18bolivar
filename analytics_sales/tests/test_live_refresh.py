# -*- coding: utf-8 -*-
"""Asegura la actualización en cada consulta sin repetir ni perder datos."""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models.sync import _unwrap


class TestAnalyticsSalesLiveRefresh(TransactionCase):

    def setUp(self):
        super().setUp()
        self.sync = self.env['analytics.sales.sync'].sudo()
        self.company = self.env.company

    def _row(self, **changes):
        row = {
            'clave': 'FA-6789-SKU-001', 'Tipo': 'FA', 'numero': '6789',
            'FechaFactura': '2026.11.12', 'Factura': '125',
            'nlocal': 'LOCAL TEST ACTUALIZACION 001',
            'Codvendedor': 'T001  ', 'Vendedor': 'Vendedor Uno',
            'Codproducto': 'SKU-001  ', 'Producto': 'Producto Uno',
            'Linea': 'CALZADO ', 'Marca': 'Marca Uno ',
            'Cantidad': '1.00', 'Total_neto': '26.0878', 'Total_costo': '14.0000',
        }
        row.update(changes)
        return row

    def _record(self):
        return self.env['analytics.sales.move'].sudo().with_context(active_test=False).search([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'api'),
            ('source_line_id', '=', 'FA-6789-SKU-001')])

    def test_each_sync_refreshes_existing_clave_without_inserting_duplicate(self):
        first = self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(first['created'], 1)
        self.assertEqual(self._record().total_net, 26.0878)
        changed = self.sync._upsert_snapshot([self._row(
            Cantidad='3.00', Total_neto='70.0000', Total_costo='38.0000',
            Vendedor='Vendedor Dos', Marca='Marca Dos',
        )], self.company, 'api', 'merge')
        self.assertEqual(changed['created'], 0)
        self.assertEqual(changed['updated'], 1)
        self.assertEqual(len(self._record()), 1)
        self.assertEqual(self._record().quantity, 3)
        self.assertEqual(self._record().total_net, 70)
        self.assertEqual(self._record().seller, 'Vendedor Dos')
        self.assertEqual(self._record().brand, 'Marca Dos')

    def test_identical_response_refreshes_last_checked_timestamp(self):
        first = self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(self.sync._mark_api_keys_checked(
            self.company, first['source_keys'], 'monthly'), 1)
        record = self._record()
        self.assertTrue(record.api_last_checked_at)
        self.assertEqual(record.api_last_checked_kind, 'monthly')
        again = self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(again['updated'], 0)
        self.assertEqual(self.sync._mark_api_keys_checked(
            self.company, again['source_keys'], 'annual'), 1)
        self.assertEqual(self._record().api_last_checked_kind, 'annual')

    def test_cancelled_line_disappears_and_can_reactivate(self):
        self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        cancelled = self.sync._upsert_snapshot([
            self._row(anulado=True)], self.company, 'api', 'merge')
        self.assertEqual(cancelled['created'], 0)
        self.assertEqual(cancelled['updated'], 1)
        self.assertFalse(self._record().active)
        self.assertFalse(self.env['analytics.sales.move'].sudo().search([
            ('source_line_id', '=', 'FA-6789-SKU-001')]))
        self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertTrue(self._record().active)
        self.assertEqual(len(self._record()), 1)

    def test_partial_cut_does_not_delete_other_periods(self):
        other = self._row(clave='FA-6700-SKU-002', numero='6700',
                          FechaFactura='2026.10.12', Codproducto='SKU-002')
        self.sync._upsert_snapshot([self._row(), other], self.company, 'api', 'merge')
        self.sync._upsert_snapshot([self._row(Total_neto='30')], self.company, 'api', 'merge')
        all_records = self.env['analytics.sales.move'].sudo().search([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'api'),
            ('local_id.name', '=', 'LOCAL TEST ACTUALIZACION 001')])
        self.assertEqual(len(all_records), 2)
        self.assertEqual(self._record().total_net, 30)

    def test_failure_response_does_not_modify_snapshot(self):
        with self.assertRaises(ValidationError):
            _unwrap({'success': False, 'data': [self._row()]})


    def test_dashboard_reloads_latest_saved_api_data_without_fetching_api(self):
        from unittest.mock import patch
        self.env.user.sudo().write({'groups_id': [
            (4, self.env.ref('analytics_sales.group_analytics_sales_admin').id),
        ]})
        self.sync._upsert_snapshot([self._row(Total_neto='25.00')], self.company, 'api', 'merge')
        dashboard = self.env['analytics.sales.dashboard']
        params = {'period': 'year', 'scope': 'all', 'local_id': self._record().local_id.id}
        with patch.object(type(self.sync), '_fetch_api', side_effect=AssertionError('No llamar a la API')):
            before = dashboard.get_dashboard(params)
            self.assertEqual(before['metrics']['sales'], 25.0)
            self.assertTrue(before['dashboard_read_at'])
            self.sync._upsert_snapshot([self._row(Total_neto='70.00', FechaFactura='2026.11.13')],
                                       self.company, 'api', 'merge')
            after = dashboard.get_dashboard(params)
            self.assertEqual(after['metrics']['sales'], 70.0)
            self.assertEqual(after['date_to'], '2026-11-13')
            self.assertAlmostEqual(after['goal_dashboard']['actual'], 70.0)
            self.assertTrue(after['dashboard_read_at'])
            self.assertEqual(len(self._record()), 1)
