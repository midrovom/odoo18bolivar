# -*- coding: utf-8 -*-
"""Regression: no newly created price lists; respect an existing Public Pricelist."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT/'models'/'inventory_web_sync.py').read_text(encoding='utf-8')


def method(name, ns=None):
    klass = next(n for n in ast.parse(SOURCE).body
                 if isinstance(n, ast.ClassDef) and n.name == 'StockInventoryWebSync')
    f = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == name)
    f.decorator_list = []
    globals_dict = ns or {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[f], type_ignores=[])),
                 '<odoo-method>', 'exec'), globals_dict)
    return globals_dict[name]


class FakeRules(list):
    def mapped(self, name):
        return [getattr(item, name) for item in self]


class Items:
    def __init__(self):
        self.created = []
    def sudo(self): return self
    def with_company(self, company): return self
    def search(self, domain, limit=2): return FakeRules()
    def create(self, data):
        self.created.append(data)
        return SimpleNamespace(id=len(self.created))


class ExistingPublicPricelistTest(unittest.TestCase):
    def test_public_pricelist_price2_creates_item_not_price_list(self):
        comp = SimpleNamespace(id=1)
        price_list = SimpleNamespace(id=7, name='Public Pricelist', company_id=comp,
                                     display_name='Public Pricelist')
        items = Items()
        env = {'product.pricelist.item': items}
        fake_service = SimpleNamespace(env=env)
        tmpl = SimpleNamespace(id=18, list_price=27.7846)
        sync_price = method('_sync_price', {
            'float_compare': lambda a, b, precision_digits: (a > b) - (a < b),
        })
        old, new, changed, label = sync_price(fake_service, tmpl, price_list, 22.8429,
                                               comp, cached_rules=None)
        self.assertIsNone(old)
        self.assertEqual(new, 22.8429)
        self.assertTrue(changed)
        self.assertEqual(tmpl.list_price, 27.7846)
        self.assertEqual(items.created[0]['pricelist_id'], 7)
        self.assertEqual(items.created[0]['fixed_price'], 22.8429)

    def test_public_price1_updates_product_list_price(self):
        fake_service = SimpleNamespace(env={})
        tmpl = SimpleNamespace(id=18, list_price=2.0, write=lambda vals: tmpl.__dict__.update(vals))
        sync_price = method('_sync_price', {'float_compare': lambda a, b, precision_digits: (a > b) - (a < b)})
        old, new, changed, label = sync_price(fake_service, tmpl, None, 8.5571,
                                              SimpleNamespace(id=1))
        self.assertEqual(tmpl.list_price, 8.5571)
        self.assertEqual((old, new), (2.0, 8.5571))
        self.assertTrue(changed)


if __name__ == '__main__':
    unittest.main()
