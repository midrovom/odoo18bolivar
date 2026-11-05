# -*- coding: utf-8 -*-
"""Regression tests for legacy stock_api price handling across two endpoints."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')
TEMPLATE = (ROOT / 'models' / 'product_template.py').read_text(encoding='utf-8')
API_SOURCE = (ROOT / 'models' / 'api_administrator.py').read_text(encoding='utf-8')


def get_real_method(name):
    cls = next(n for n in ast.parse(SOURCE).body if isinstance(n, ast.ClassDef)
               and n.name == 'StockInventoryWebSync')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)
    fn.decorator_list = []
    ns = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])),
                 '<actual-odoo-code>', 'exec'), ns)
    return ns[name]


def fake_api(list_price):
    return SimpleNamespace(price_list_id=list_price)


class PriceRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = staticmethod(get_real_method('_price_list_destination'))
        spec = importlib.util.spec_from_file_location('combine', ROOT / 'models' / 'combined_payload.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cls.combine = staticmethod(module.combine_catalogs)

    def test_price1_is_base_even_if_api_form_has_list_selected(self):
        custom = SimpleNamespace(id=31, name='precio_venta')
        self.assertFalse(self.resolver(None, fake_api(custom), 1))

    def test_price2_is_existing_custom_pricelist(self):
        custom = SimpleNamespace(id=31, name='precio_venta')
        self.assertIs(self.resolver(None, fake_api(custom), 2), custom)

    def test_existing_public_price_list_is_valid_for_price2(self):
        public = SimpleNamespace(id=40, name='Public Pricelist')
        self.assertIs(self.resolver(None, fake_api(public), 2), public)

    def test_old_stock_api_rule_uses_custom_for_other_routes(self):
        custom = SimpleNamespace(id=31, name='precio_venta')
        self.assertIs(self.resolver(None, fake_api(custom), 3), custom)

    def test_two_endpoints_same_configured_list_keep_both_prices(self):
        # Odoo pricelist 31 is selected in BOTH API records.
        # /1 must target base (False); /2 must target pricelist 31.
        api_one = fake_api(SimpleNamespace(id=31, name='precio_venta'))
        api_two = fake_api(SimpleNamespace(id=31, name='precio_venta'))
        target_one = self.resolver(None, api_one, 1)
        target_two = self.resolver(None, api_two, 2)
        rows, warnings = self.combine([
            (23, target_one.id if target_one else False,
             [{'codigo': 'ABC', 'Precio': 25.31, 'Bodegas': [{'Bodega': 'ABS', 'StockBodega': 0}]}]),
            (24, target_two.id if target_two else False,
             [{'codigo': 'ABC', 'Precio': 20.48, 'Bodegas': [{'Bodega': 'ABS', 'StockBodega': 0}]}]),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['_inventory_web_prices'], [(23, 25.31), (24, 20.48)])
        self.assertEqual(len(rows[0]['Bodegas']), 1)
        self.assertFalse(warnings)

    def test_prices_are_taken_from_the_two_json_fields(self):
        self.assertIn("price_field = 'Precio' if external_price_id == 1 else 'Precio_2'", SOURCE)
        self.assertIn('price_targets=price_api_targets', SOURCE)
        self.assertIn("values['inventory_web_price_%s' % field_id] = amount", SOURCE)
        self.assertIn('inventory_web_price_1 = fields.Float(', TEMPLATE)
        self.assertIn('inventory_web_price_2 = fields.Float(', TEMPLATE)

    def test_logs_explain_external_price_and_actual_odoo_target(self):
        self.assertIn('PRECIO_RUTA', SOURCE)
        self.assertIn('lista_externa=%s destino=%s', SOURCE)
        self.assertNotIn('inventory_web_external_price', API_SOURCE)
        view = (ROOT / 'views' / 'inventory_web_views.xml').read_text(encoding='utf-8')
        self.assertNotIn('inventory_web_external_price', view)


if __name__ == '__main__':
    unittest.main()
