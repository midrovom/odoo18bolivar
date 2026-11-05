"""Pruebas unitarias puras; ejecutar: python -m unittest discover -s tests -v"""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('warehouse_payload', ROOT / 'models' / 'warehouse_payload.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class WarehousePayloadTest(unittest.TestCase):
    warehouses = {'ABS', 'ANT', 'CBA', 'LPP', 'NAJ'}

    def test_log_state_created(self):
        self.assertEqual(mod.trace_state(True, True, False), 'created')

    def test_log_state_updated(self):
        self.assertEqual(mod.trace_state(False, True, False), 'updated')

    def test_log_state_unchanged(self):
        self.assertEqual(mod.trace_state(False, False, False), 'unchanged')

    def test_log_state_warning_overrides_updated(self):
        self.assertEqual(mod.trace_state(False, True, True), 'warning')

    def test_log_state_warning_overrides_created(self):
        self.assertEqual(mod.trace_state(True, True, True), 'warning')

    def test_one_api_resolves_all_warehouse_codes_not_just_configured_id(self):
        ids, notices = mod.resolve_warehouse_ids([
            (11, 'ABS'), (12, 'ANT'), (13, ' CBA  '), (14, 'LPP'),
        ], preferred_id=11)
        self.assertEqual(ids, {'ABS': 11, 'ANT': 12, 'CBA': 13, 'LPP': 14})
        self.assertEqual(notices, [])

    def test_duplicate_warehouse_code_uses_configured_id_only_for_that_code(self):
        ids, notices = mod.resolve_warehouse_ids([
            (11, 'abs'), (12, 'ABS '), (13, 'ANT'),
        ], preferred_id=12)
        self.assertEqual(ids, {'ABS': 12, 'ANT': 13})
        self.assertTrue(any('duplicado' in msg for msg in notices))

    def test_duplicate_without_configured_id_is_skipped(self):
        ids, notices = mod.resolve_warehouse_ids([
            (11, 'ABS'), (12, ' abs'), (13, 'ANT'),
        ])
        self.assertEqual(ids, {'ANT': 13})
        self.assertTrue(any('duplicado' in msg for msg in notices))

    def test_configured_warehouse_must_exist_in_company_candidates(self):
        with self.assertRaises(ValueError):
            mod.resolve_warehouse_ids([(11, 'ABS'), (13, 'ANT')], preferred_id=999)

    def test_product_links_only_warehouses_explicit_in_payload(self):
        codes = mod.declared_warehouse_codes({
            'StockTotal': 0,
            'Bodegas': [
                {'Bodega': ' abs ', 'StockBodega': 0},
                {'Bodega': 'ANT', 'StockBodega': 0},
                {'Bodega': 'UNKNOWN', 'StockBodega': 0},
            ],
        }, {'ABS': 11, 'ANT': 12, 'CBA': 13})
        self.assertEqual(codes, {'ABS', 'ANT'})

    def test_zero_with_single_configured_warehouse_still_clears_all_company(self):
        code_ids, _ = mod.resolve_warehouse_ids(
            [(11, 'ABS'), (12, 'ANT'), (13, 'CBA')], preferred_id=11)
        targets, _ = mod.stock_targets(
            {'StockTotal': 0, 'Bodegas': [{'Bodega': 'ABS', 'StockBodega': 0}]},
            code_ids)
        self.assertEqual(targets, {'ABS': 0, 'ANT': 0, 'CBA': 0})

    def test_unknown_warehouse_does_not_fallback_to_configured_warehouse(self):
        code_ids, _ = mod.resolve_warehouse_ids([(11, 'ABS')], preferred_id=11)
        targets, messages = mod.stock_targets({
            'StockTotal': 5,
            'Bodegas': [{'Bodega': 'NO_EXISTE', 'StockBodega': 5}]
        }, code_ids)
        self.assertNotIn('ABS', targets)
        self.assertTrue(any('no existe' in msg for msg in messages))

    def test_stocktotal_zero_resets_all_company_warehouses(self):
        targets, messages = mod.stock_targets({
            'StockTotal': 0,
            'Bodegas': [{'Bodega': 'ANT', 'StockBodega': 12}, {'Bodega': 'ABS', 'StockBodega': 0}],
        }, self.warehouses)
        self.assertEqual(targets, {code: 0 for code in self.warehouses})
        self.assertTrue(any('contradice' in msg for msg in messages))

    def test_positive_total_updates_only_explicit_warehouses_including_zero(self):
        targets, messages = mod.stock_targets({
            'StockTotal': 15,
            'Bodegas': [{'Bodega': 'ANT', 'StockBodega': 12},
                        {'Bodega': 'NAJ', 'StockBodega': 3},
                        {'Bodega': 'ABS', 'StockBodega': 0}],
        }, self.warehouses)
        self.assertEqual(targets, {'ANT': 12, 'NAJ': 3, 'ABS': 0})
        self.assertFalse(messages)

    def test_total_mismatch_never_distributes_stock(self):
        targets, messages = mod.stock_targets({
            'StockTotal': 15, 'Bodegas': [{'Bodega': 'ANT', 'StockBodega': 2}],
        }, self.warehouses)
        self.assertEqual(targets, {'ANT': 2})
        self.assertTrue(any('difiere' in msg for msg in messages))

    def test_explicit_zero_differs_from_missing(self):
        targets, messages = mod.stock_targets({
            'StockTotal': 2, 'Bodegas': [
                {'Bodega': 'ABS', 'StockBodega': 0},
                {'Bodega': 'NAJ'},
                {'Bodega': 'ANT', 'StockBodega': 2},
            ],
        }, self.warehouses)
        self.assertIn('ABS', targets)
        self.assertEqual(targets['ABS'], 0)
        self.assertNotIn('NAJ', targets)
        self.assertTrue(any('sin StockBodega' in msg for msg in messages))

    def test_empty_string_is_not_zero(self):
        with self.assertRaises(ValueError):
            mod.as_number('', 'StockTotal')
        with self.assertRaises(ValueError):
            mod.as_number(None, 'StockBodega')

    def test_negative_total_does_not_reset_warehouses(self):
        with self.assertRaises(ValueError):
            mod.stock_targets({'StockTotal': -1, 'Bodegas': []}, self.warehouses)

    def test_total_zero_when_bodegas_absent_still_resets(self):
        targets, _ = mod.stock_targets({'StockTotal': 0}, self.warehouses)
        self.assertEqual(len(targets), 5)
        self.assertTrue(all(qty == 0 for qty in targets.values()))

    def test_unknown_warehouse_warns_without_auto_create(self):
        targets, msgs = mod.stock_targets({
            'StockTotal': 1, 'Bodegas': [{'Bodega': 'XYZ', 'StockBodega': 1}]
        }, self.warehouses)
        self.assertEqual(targets, {'XYZ': 1})
        self.assertTrue(any('no existe' in msg for msg in msgs))

    def test_duplicated_code_is_not_counted_twice(self):
        targets, messages = mod.stock_targets({
            'StockTotal': 12, 'Bodegas': [
                {'Bodega': 'ANT', 'StockBodega': 12},
                {'Bodega': 'ANT', 'StockBodega': 3},
            ]
        }, self.warehouses)
        self.assertEqual(targets, {'ANT': 3})
        self.assertTrue(any('duplicada' in msg for msg in messages))


if __name__ == '__main__':
    unittest.main()
