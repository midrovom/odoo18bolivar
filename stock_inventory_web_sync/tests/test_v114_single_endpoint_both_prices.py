# -*- coding: utf-8 -*-
"""No Odoo database needed: feed-contract and method-level regression tests."""
import ast
import importlib.util
import logging
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')
API_SRC = (ROOT / 'models' / 'api_administrator.py').read_text(encoding='utf-8')

spec = importlib.util.spec_from_file_location('feed', ROOT / 'models' / 'combined_payload.py')
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


def actual_method(name, names=None):
    klass = next(node for node in ast.parse(SRC).body
                 if isinstance(node, ast.ClassDef) and node.name == 'StockInventoryWebSync')
    func = next(node for node in klass.body
                if isinstance(node, ast.FunctionDef) and node.name == name)
    func.decorator_list = []
    namespace = {'defaultdict': defaultdict, '_logger': logging.getLogger(__name__)}
    namespace.update(names or {})
    exec(compile(ast.fix_missing_locations(ast.Module(body=[func], type_ignores=[])),
                 '<real-module-method>', 'exec'), namespace)
    return namespace[name]


class SingleApiPricingTests(unittest.TestCase):
    def payload(self, **changes):
        row = dict(
            codigo='GROVEWHITEKJ1', Nombre='PORCELANATO PAM GROVE WHITE',
            Precio=27.7846, Precio_2=22.8429, StockTotal=2.88,
            Bodegas=[{'Bodega': 'ABS', 'StockBodega': 1.92},
                     {'Bodega': 'NAJ', 'StockBodega': .96}],
        )
        row.update(changes)
        return row

    def test_only_one_feed_contains_both_price_fields(self):
        merged, warnings = feed.combine_catalogs(
            [(23, 31, [self.payload()])], price_targets={1: 23, 2: 23})
        self.assertFalse(warnings)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['_inventory_web_price_fields'],
                         {1: (23, 27.7846), 2: (23, 22.8429)})
        self.assertEqual(merged[0]['_inventory_web_prices'],
                         [(23, 27.7846), (23, 22.8429)])
        self.assertEqual(merged[0]['Bodegas'], self.payload()['Bodegas'])

    def test_wholesale_zero_is_real_value(self):
        merged, _ = feed.combine_catalogs(
            [(23, 31, [self.payload(Precio_2=0)])], price_targets={1: 23, 2: 23})
        self.assertEqual(merged[0]['_inventory_web_price_fields'][2], (23, 0))

    def test_missing_wholesale_does_not_write_zero(self):
        row = self.payload()
        del row['Precio_2']
        merged, _ = feed.combine_catalogs(
            [(23, 31, [row])], price_targets={1: 23, 2: 23})
        self.assertNotIn(2, merged[0]['_inventory_web_price_fields'])

    def test_single_endpoint_route_suffix_does_not_decide_price_field(self):
        self.assertIn('price_api_targets = ({1: api_record.id, 2: api_record.id}', SRC)
        self.assertIn("for field_id, (price_api_id, raw_price) in received_prices.items():", SRC)
        self.assertIn("values['inventory_web_price_%s' % field_id] = amount", SRC)
        self.assertIn('for external_price_id, (source_api_id, raw_price) in price_sources.items():', SRC)
        self.assertIn('target_pricelist = self._price_list_destination(source_api, external_price_id)', SRC)

    def test_cron_fetches_just_one_of_two_leftover_marked_apis(self):
        apis = [SimpleNamespace(id=23, company_id=SimpleNamespace(id=1),
                                price_list_id=SimpleNamespace(id=31)),
                SimpleNamespace(id=24, company_id=SimpleNamespace(id=1),
                                price_list_id=SimpleNamespace(id=32))]
        class ApiModel:
            def sudo(self): return self
            def search(self, domain): return apis
        class Env:
            cr = SimpleNamespace(savepoint=nullcontext)
            def __getitem__(self, name): return ApiModel()
        class Svc:
            env = Env()
            def __init__(self): self.calls=[]
            def _check_sync_access(self): pass
            def _api_endpoint_identity(self, api): return 2, (1 if api.id == 23 else 2)
            def sync_api(self, api_id, execution_type):
                self.calls.append((api_id, execution_type))
                return dict(created=0, updated=1, stocks=2, errors=0)
        method = actual_method('sync_inventory_web_products')
        svc = Svc()
        method(svc)
        self.assertEqual(svc.calls, [(23, 'cron')])
        svc.calls.clear()
        method(svc, company_id=2, execution_type='manual', selected_api_id=24)
        self.assertEqual(svc.calls, [(24, 'manual')])

    def test_cron_and_button_still_independent_of_stock_api_old_cron(self):
        self.assertIn("('inventory_web_products_enabled', '=', True)", SRC)
        self.assertIn('selected_api_id=self.id', API_SRC)
        self.assertIn('ENDPOINTS_EXTRA_OMITIDOS', SRC)
        self.assertIn('model.sync_inventory_web_products()',
                      (ROOT / 'data' / 'ir_cron.xml').read_text())

    def test_existing_public_pricelist_is_accepted_without_creating(self):
        method = actual_method('_validate_existing_pricelist', {'_': lambda message: message,
                                                                  'UserError': ValueError})
        company = SimpleNamespace(id=1, display_name='Transcash')
        selected = SimpleNamespace(id=45, name='Public Pricelist', display_name='Public Pricelist',
                                   company_id=company)
        api = SimpleNamespace(price_list_id=selected)
        self.assertIs(method(None, api, company), selected)
        self.assertFalse(hasattr(api, 'writes'))

    def test_missing_pricelist_fails_without_creation(self):
        method = actual_method('_validate_existing_pricelist', {'_': lambda message: message,
                                                                  'UserError': ValueError})
        company = SimpleNamespace(id=1, display_name='Transcash')
        with self.assertRaisesRegex(ValueError, 'no crea listas nuevas'):
            method(None, SimpleNamespace(price_list_id=False), company)

    def test_previous_autogenerated_wholesale_list_is_rejected_not_deleted(self):
        method = actual_method('_validate_existing_pricelist', {'_': lambda message: message,
                                                                  'UserError': ValueError})
        company = SimpleNamespace(id=1, display_name='Transcash')
        old = SimpleNamespace(id=45, name='Inventario Web Mayorista - Empresa externa 2 - Odoo 1',
                              display_name='Inventario Web Mayorista - Empresa externa 2 - Odoo 1',
                              company_id=company)
        api = SimpleNamespace(price_list_id=old)
        with self.assertRaisesRegex(ValueError, 'lista pública existente'):
            method(None, api, company)
        self.assertIs(api.price_list_id, old)

    def test_same_field_is_not_reinterpreted_as_external_list(self):
        self.assertIn("price_field = 'Precio' if external_price_id == 1 else 'Precio_2'", SRC)
        self.assertIn("string='Precio mayorista API'", (ROOT / 'models' / 'product_template.py').read_text())


if __name__ == '__main__':
    unittest.main()
