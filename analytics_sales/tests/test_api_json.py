# -*- coding: utf-8 -*-
"""Tests del contrato JSON nativo de ventas IDR (sin datos reales)."""
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

from ..models.sync import _unwrap


class TestAnalyticsSalesNativeApiJson(TransactionCase):

    def setUp(self):
        super().setUp()
        self.sync = self.env['analytics.sales.sync'].sudo()
        self.company = self.env.company

    def _row(self, **changes):
        row = {
            'clave': 'FA-5377-SKU-01', 'Tipo': 'FA', 'numero': '5377',
            'Factura': '1482', 'FechaFactura': '2026.10.01',
            'nlocal': 'TEST JSON IDR LOCAL 001', 'Codvendedor': '178   ',
            'Vendedor': 'Persona de Prueba', 'Codproducto': 'SKU-01     ',
            'Producto': 'Producto ficticio', 'Linea': 'CALZADO       ',
            'Marca': 'Marca Prueba      ', 'Cantidad': '2.00',
            'Total_neto': '13.0400000', 'Total_costo': '11.77000000',
        }
        row.update(changes)
        return row

    def _moves(self):
        return self.env['analytics.sales.move'].sudo().search([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'api'),
            ('local_id.name', '=', 'TEST JSON IDR LOCAL 001'),
        ])

    def test_wrapped_response_and_signed_returns(self):
        row = self._row()
        payload = {'success': True, 'data': [row], 'session_id': 'session-test'}
        self.assertEqual(_unwrap(payload), [row])
        vals = self.sync._normalize(row, 1, 'api')
        self.assertEqual(vals['source_line_id'], 'FA-5377-SKU-01')
        self.assertEqual(vals['document_number'], 'FA-5377')
        self.assertEqual(vals['date'], '2026-10-01')
        self.assertEqual(vals['seller_code'], '178')
        self.assertEqual(vals['sku'], 'SKU-01')
        self.assertEqual(vals['line_name'], 'CALZADO')
        self.assertEqual(vals['brand'], 'Marca Prueba')
        self.assertEqual(vals['total_net'], 13.04)
        self.assertEqual(vals['total_cost'], 11.77)
        refund = self.sync._normalize(self._row(
            clave='DE-128-SKU-01', Tipo='DE', numero='128',
            Cantidad='-1.00', Total_neto='-9.5000', Total_costo='-6.1000',
        ), 2, 'api')
        self.assertEqual(refund['document_number'], 'DE-128')
        self.assertEqual(refund['quantity'], 1)
        self.assertEqual(refund['total_net'], 9.5)
        self.assertEqual(refund['total_cost'], 6.1)

    def test_api_merge_uses_clave_without_duplicates(self):
        row = self._row()
        first = self.sync._upsert_snapshot([row], self.company, 'api', 'merge')
        self.assertEqual(first['created'], 1)
        same = self.sync._upsert_snapshot([row], self.company, 'api', 'merge')
        self.assertEqual(same['created'], 0)
        updated = self.sync._upsert_snapshot(
            [self._row(Total_neto='14.5500000')], self.company, 'api', 'merge')
        self.assertEqual(updated['created'], 0)
        self.assertEqual(updated['updated'], 1)
        self.assertEqual(len(self._moves()), 1)
        self.assertAlmostEqual(self._moves().total_net, 14.55)

    def test_repeated_clave_is_counted_once(self):
        repeated = self._row(clave='FA-5849-SKU-01', numero='5849')
        data = [repeated.copy(), repeated.copy()]
        result = self.sync._upsert_snapshot(data, self.company, 'api', 'merge')
        self.assertEqual(result['created'], 1)
        self.assertEqual(result['repeated_keys'], 1)
        again = self.sync._upsert_snapshot(data, self.company, 'api', 'merge')
        self.assertEqual(again['created'], 0)
        self.assertEqual(len(self._moves()), 1)

    def test_conflicting_duplicate_clave_is_rejected(self):
        first = self._row(clave='FA-5849-SKU-01')
        second = self._row(clave='FA-5849-SKU-01', Total_neto='99.0000000')
        with self.assertRaises(ValidationError):
            self.sync._upsert_snapshot([first, second], self.company, 'api', 'merge')

    def test_clave_is_independent_from_local_and_document(self):
        original = self._row()
        self.sync._upsert_snapshot([original], self.company, 'api', 'merge')
        result = self.sync._upsert_snapshot([self._row(
            numero='6399', FechaFactura='2026.11.12', Total_neto='15.00',
        )], self.company, 'api', 'merge')
        self.assertEqual(result['created'], 0)
        self.assertEqual(result['updated'], 1)
        self.assertEqual(len(self._moves()), 1)
        self.assertEqual(self._moves().document_number, 'FA-6399')

    def test_previous_version_duplicate_entries_are_consolidated(self):
        source_id = 'FA-5849-SKU-01'
        row = self._row(clave=source_id)
        self.sync._upsert_snapshot([row], self.company, 'api', 'merge')
        original = self._moves()
        duplicate_vals = original.copy_data()[0]
        duplicate_vals.pop('id', None)
        duplicate_vals['source_key'] = 'legacy-occurrence-2'
        self.env['analytics.sales.move'].sudo().create(duplicate_vals)
        self.assertEqual(len(self._moves()), 2)
        result = self.sync._upsert_snapshot([row], self.company, 'api', 'merge')
        self.assertEqual(result['created'], 0)
        self.assertEqual(len(self._moves()), 1)

    def test_legacy_api_numeric_document_is_updated(self):
        """API de versiones antiguas sin clave y con numero sin prefijo."""
        legacy = self._row()
        legacy.pop('clave')
        self.sync._upsert_snapshot([legacy], self.company, 'api', 'merge')
        # Simula el dato tal como quedo guardado en la version previa.
        self._moves().write({'document_number': '5377'})
        result = self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(result['created'], 0)
        self.assertEqual(len(self._moves()), 1)
        self.assertEqual(self._moves().document_number, 'FA-5377')
        self.assertEqual(self._moves().source_line_id, 'FA-5377-SKU-01')

    def test_api_does_not_erase_historical_excel_data(self):
        history = self._row()
        self.sync._upsert_snapshot([history], self.company, 'historico', 'merge')
        self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(self.env['analytics.sales.move'].sudo().search_count([
            ('company_id', '=', self.company.id), ('source_kind', '=', 'historico'),
            ('local_id.name', '=', 'TEST JSON IDR LOCAL 001')]), 1)

    def test_invalid_api_row_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.sync._normalize(self._row(nlocal='    '), 1, 'api')

    def test_model_updates_same_api_key_and_survives_missing_field(self):
        self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        initial = self._moves()
        self.assertFalse(initial.modelo)
        self.sync._upsert_snapshot([self._row(modelo='  MODELO-410  ')], self.company, 'api', 'merge')
        updated = self._moves()
        self.assertEqual(updated.ids, initial.ids)
        self.assertEqual(updated.modelo, 'MODELO-410')
        self.assertEqual(updated.total_net, initial.total_net)
        self.sync._upsert_snapshot([self._row()], self.company, 'api', 'merge')
        self.assertEqual(self._moves().modelo, 'MODELO-410')
        self.sync._upsert_snapshot([self._row(modelo='MODELO-500')], self.company, 'api', 'merge')
        self.assertEqual(self._moves().ids, initial.ids)
        self.assertEqual(self._moves().modelo, 'MODELO-500')
