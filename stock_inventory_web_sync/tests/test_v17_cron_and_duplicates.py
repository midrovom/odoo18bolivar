# -*- coding: utf-8 -*-
"""Pruebas Odoo-less de los cambios introducidos en 16.0.1.7.0."""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
CODE = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')
TREE = ast.parse(CODE)
SERVICE = next(n for n in TREE.body if isinstance(n, ast.ClassDef)
               and n.name == 'StockInventoryWebSync')


def method_node(name):
    return next(node for node in SERVICE.body
                if isinstance(node, ast.FunctionDef) and node.name == name)


def method_callable(name, context):
    import copy
    node = copy.deepcopy(method_node(name))
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    exec(compile(module, '<new-method>', 'exec'), context)
    return context[name]


class TestCronAndDuplicates(unittest.TestCase):
    def test_cron_uses_only_marked_apis_and_isolates_failed_endpoint(self):
        import logging
        from collections import defaultdict
        sync = method_callable('sync_inventory_web_products', {
            '_logger': logging.getLogger(__name__), 'defaultdict': defaultdict,
        })
        apis = [SimpleNamespace(id=23, name='API productos A',
                                company_id=SimpleNamespace(id=2),
                                end_point='/show_inventory_web/2/2',
                                price_list_id=SimpleNamespace(id=10),
                                inventory_web_products_enabled=True),
                SimpleNamespace(id=24, name='API productos B',
                                company_id=SimpleNamespace(id=3),
                                end_point='/show_inventory_web/3/2',
                                price_list_id=SimpleNamespace(id=11),
                                inventory_web_products_enabled=True)]

        class FakeApiModel:
            domain = None
            def sudo(self):
                return self
            def search(self, domain):
                self.domain = domain
                return apis

        class FakeService:
            def __init__(self):
                self.api_model = FakeApiModel()
                self.env = SimpleNamespace(cr=SimpleNamespace(savepoint=nullcontext))
                self.calls = []
            def _check_sync_access(self):
                return None
            def _api_endpoint_identity(self, api):
                return tuple(int(part) for part in api.end_point.strip('/').split('/')[-2:])
            def sync_api(self, api_id, execution_type):
                self.calls.append((api_id, execution_type))
                if api_id == 23:
                    raise ValueError('fallo de API de pruebas')
                return {'created': 1, 'updated': 12, 'stocks': 3, 'errors': 0}

        class Env(SimpleNamespace):
            def __init__(self, model):
                super().__init__(cr=SimpleNamespace(savepoint=nullcontext))
                self.model = model
            def __getitem__(self, name):
                self_name = 'api.administrator'
                assert name == self_name
                return self.model

        service = FakeService()
        service.env = Env(service.api_model)
        result = sync(service)
        self.assertEqual(service.calls, [(23, 'cron'), (24, 'cron')])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['errors'], 1)
        self.assertEqual(result[1]['updated'], 12)
        self.assertIn(('inventory_web_products_enabled', '=', True), service.api_model.domain)
        self.assertIn(('status', '=', 'A'), service.api_model.domain)

    def test_stock_precache_groups_all_variants_in_one_search(self):
        preload = method_callable('_preload_stock_batch', {})
        calls = []
        quants = [SimpleNamespace(id=201, product_id=SimpleNamespace(id=10)),
                  SimpleNamespace(id=202, product_id=SimpleNamespace(id=11)),
                  SimpleNamespace(id=203, product_id=SimpleNamespace(id=10))]

        class FakeQuants:
            def sudo(self):
                return self
            def with_company(self, company):
                return self
            def search(self, domain):
                calls.append(domain)
                return quants

        class Env(dict):
            pass

        model = SimpleNamespace(env=Env({'stock.quant': FakeQuants()}))
        matches = {'ABC': [SimpleNamespace(id=10), SimpleNamespace(id=11)],
                   'XYZ': [SimpleNamespace(id=12)]}
        mapping = {'ABS': {9}, 'ANT': {13}}
        grouped = preload(model, matches, mapping, SimpleNamespace(id=3))
        self.assertEqual(grouped, {10: [201, 203], 11: [202]})
        self.assertEqual(len(calls), 1)
        self.assertEqual(set(next(value for key, op, value in calls[0] if key == 'product_id')),
                         {10, 11, 12})

    def test_duplicate_product_not_discarded(self):
        body = ast.get_source_segment(CODE, method_node('sync_api'))
        self.assertIn('for variant in variants:', body)
        self.assertIn('matches_by_code[code] = Product.browse([new_id])', body)
        self.assertIn('se procesarán todas las apariciones', body)
        self.assertNotIn('se ignora su segunda aparición', body)
        self.assertIn('processed_stock_ids.add(trace[\'product_id\'])', body)

    def test_duplicate_pricelist_rules_update_without_skipping_product(self):
        import logging
        def compare(a, b, precision_digits=None):
            return 0 if abs(a-b) < 0.000001 else 1
        sync_price = method_callable('_sync_price', {
            '_logger': logging.getLogger(__name__), 'float_compare': compare,
        })
        class Rule:
            def __init__(self, value):
                self.compute_price = 'fixed'
                self.fixed_price = value
        class Rules(list):
            def mapped(self, field):
                return [getattr(r, field) for r in self]
            def write(self, vals):
                for rule in self:
                    rule.compute_price = vals['compute_price']
                    rule.fixed_price = vals['fixed_price']
        class ItemModel:
            def sudo(self):
                return self
            def with_company(self, company):
                return self
        company = SimpleNamespace(id=2)
        pricelist = SimpleNamespace(id=99, name='Lista web', company_id=company,
                                    display_name='Lista web')
        rules = Rules([Rule(12), Rule(14)])
        fake_service = SimpleNamespace(env={'product.pricelist.item': ItemModel()})
        tmpl = SimpleNamespace(id=31)
        before, after, changed, label = sync_price(
            fake_service, tmpl, pricelist, 25.31, company, {31: rules})
        self.assertEqual(before, [12, 14])
        self.assertEqual(after, 25.31)
        self.assertTrue(changed)
        self.assertTrue(all(r.fixed_price == 25.31 for r in rules))

    def test_archived_variants_are_not_skipped_for_sku_duplication(self):
        body = ast.get_source_segment(CODE, method_node('_sync_one_product'))
        self.assertNotIn('El producto está archivado; no se reactiva automáticamente.', body)
        self.assertIn('Producto archivado: se actualizan sus datos sin reactivarlo.', body)


if __name__ == '__main__':
    unittest.main()
