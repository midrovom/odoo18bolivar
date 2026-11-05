# -*- coding: utf-8 -*-
"""Regression tests not requiring an Odoo runtime."""
import ast
from collections import defaultdict
import importlib.util
from pathlib import Path
from contextlib import nullcontext
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('inventory_web_combined', ROOT / 'models' / 'combined_payload.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
combine = module.combine_catalogs


def row(stock=15, amount=25.31, sku='MOLDALIPISUNI', bodegas=None):
    return {'codigo': sku, 'Nombre': 'Alicate', 'Precio': amount, 'StockTotal': stock,
            'Bodegas': bodegas if bodegas is not None else [
                {'Bodega': 'ABS', 'StockBodega': 0},
                {'Bodega': 'ANT', 'StockBodega': 12},
                {'Bodega': 'NAJ', 'StockBodega': 3},
            ]}


class TestTwoEndpoints(unittest.TestCase):
    def test_same_product_one_stock_two_pricelists(self):
        items, warnings = combine([(23, 3, [row(amount=25.31)]),
                                   (24, 4, [row(amount=20.48)])])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['codigo'], 'MOLDALIPISUNI')
        self.assertEqual(items[0]['_inventory_web_prices'], [(23, 25.31), (24, 20.48)])
        self.assertEqual(len(items[0]['Bodegas']), 3)
        self.assertEqual(items[0]['StockTotal'], 15)
        self.assertFalse(warnings)

    def test_union_skus_not_just_intersection(self):
        items, _ = combine([(23, 3, [row(sku='A')]), (24, 4, [row(sku='A'), row(sku='B')])])
        self.assertEqual([item['codigo'] for item in items], ['A', 'B'])
        self.assertEqual(items[1]['_inventory_web_prices'], [(24, 25.31)])

    def test_stock_zero_from_both_sets_explicit_zeros_once(self):
        zero = [{'Bodega': 'ABS', 'StockBodega': 0}]
        items, warnings = combine([(23, 3, [row(0, 1, bodegas=zero)]),
                                   (24, 4, [row(0, 2, bodegas=zero)])])
        self.assertEqual(items[0]['StockTotal'], 0)
        self.assertEqual(items[0]['Bodegas'], zero)
        self.assertFalse(warnings)

    def test_warehouse_stock_not_summed_when_same_sku_in_both(self):
        items, warnings = combine([(23, 3, [row(bodegas=[{'Bodega':'ANT','StockBodega':12}])]),
                                   (24, 4, [row(bodegas=[{'Bodega':'ANT','StockBodega':8}])])])
        self.assertEqual(items[0]['Bodegas'][0]['StockBodega'], 12)
        self.assertTrue(any('stock diferente' in message for message in warnings))

    def test_positive_warehouse_qty_prevents_unsafe_zero(self):
        items, warnings = combine([
            (23, 3, [row(stock=0, bodegas=[{'Bodega':'ANT','StockBodega':0}])]),
            (24, 4, [row(stock=12, bodegas=[{'Bodega':'ANT','StockBodega':12}])])])
        self.assertEqual(items[0]['StockTotal'], 12)
        self.assertEqual(items[0]['Bodegas'], [{'Bodega':'ANT','StockBodega':12}])
        self.assertTrue(warnings)

    def test_stock_total_positive_prevents_unsafe_zero(self):
        items, warnings = combine([(23, 3, [row(stock=0, bodegas=[])]),
                                   (24, 4, [row(stock=15, bodegas=[{'Bodega':'ANT','StockBodega':15}])])])
        self.assertEqual(items[0]['StockTotal'], 15)
        self.assertTrue(any('StockTotal distinto' in m for m in warnings))

    def test_duplicated_pricelist_keeps_first_configured_source(self):
        items, warnings = combine([(23, 3, [row(amount=20)]), (24, 3, [row(amount=30)])])
        self.assertEqual(items[0]['_inventory_web_prices'], [(23, 20)])
        self.assertTrue(any('precios diferentes' in m for m in warnings))

    def test_blank_and_invalid_rows_do_not_remove_valid_products(self):
        items, warnings = combine([(23, 3, [{'codigo': '  '}, row(sku=' ABC '), 'invalid']),
                                   (24, 4, [])])
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['codigo'], 'ABC')
        self.assertEqual(len(warnings), 2)

    def test_cron_groups_by_company_and_runs_one_pass(self):
        source = (ROOT / 'models' / 'inventory_web_sync.py').read_text()
        tree = ast.parse(source)
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                     and n.name == 'StockInventoryWebSync')
        method = next(n for n in klass.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'sync_inventory_web_products')
        method.decorator_list = []
        expr = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        ns = {'defaultdict': defaultdict, ' _unused': None,
              '_logger': __import__('logging').getLogger(__name__)}
        exec(compile(expr, '<group-cron>', 'exec'), ns)
        apis = [SimpleNamespace(id=23, company_id=SimpleNamespace(id=2), price_list_id=SimpleNamespace(id=10)),
                SimpleNamespace(id=24, company_id=SimpleNamespace(id=2), price_list_id=SimpleNamespace(id=11))]
        class Api:
            def sudo(self): return self
            def search(self, domain): return apis
        class Env:
            cr = SimpleNamespace(savepoint=nullcontext)
            def __getitem__(self, name):
                assert name == 'api.administrator'
                return Api()
        class Sync:
            env = Env()
            def __init__(self): self.runs = []
            def _check_sync_access(self): pass
            def _api_endpoint_identity(self, api):
                return api.company_id.id, 1 if api.id == 23 else 2
            def sync_api(self, api_ids, execution_type):
                self.runs.append((api_ids, execution_type))
                return {'created': 1, 'updated': 1, 'stocks': 2, 'errors': 0}
        service = Sync()
        result = ns['sync_inventory_web_products'](service)
        self.assertEqual(service.runs, [(23, 'cron')])
        self.assertEqual(len(result), 1)

    def test_form_and_cron_share_same_flow(self):
        api_code = (ROOT / 'models' / 'api_administrator.py').read_text()
        code = (ROOT / 'models' / 'inventory_web_sync.py').read_text()
        self.assertIn('sync_inventory_web_products(\n            company_id=endpoint_company', api_code)
        self.assertIn('ThreadPoolExecutor(', code)
        self.assertIn('combine_catalogs(', code)
        self.assertIn('price_source_records=', code)
        self.assertIn('price_events', code)

    def test_menu_cleanup_does_not_delete_crons_or_other_menus(self):
        code = (ROOT / 'models' / 'inventory_web_sync.py').read_text()
        self.assertIn('def _hide_radis_inventory_menu(self):', code)
        method = code.split('def _hide_radis_inventory_menu(self):')[1].split('    @api.model')[0]
        self.assertIn("'stock.menu_stock_root'", method)
        self.assertIn("menu.write({'active': False})", method)
        self.assertNotIn('.unlink(', method)
        self.assertIn('name="_hide_radis_inventory_menu"',
                      (ROOT / 'data' / 'ir_cron.xml').read_text())


if __name__ == '__main__':
    unittest.main()
