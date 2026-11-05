# -*- coding: utf-8 -*-
"""Pruebas sin Odoo de las nuevas precargas y la ruta de inventario sin cambios."""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
CODE = (ROOT / 'models/inventory_web_sync.py').read_text(encoding='utf-8')
TREE = ast.parse(CODE)
SERVICE = next(node for node in TREE.body
               if isinstance(node, ast.ClassDef) and node.name == 'StockInventoryWebSync')


def get_method(name, extra=None):
    node = next(node for node in SERVICE.body if isinstance(node, ast.FunctionDef) and node.name == name)
    node.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    ctx = dict(extra or {})
    exec(compile(module, '<module-perf-test>', 'exec'), ctx)
    return ctx[name]


class Recordset(list):
    def mapped(self, name):
        return [getattr(item, name) for item in self]

    def filtered(self, function):
        return Recordset([item for item in self if function(item)])


def cmp_rounding(a, b, precision_rounding):
    delta = a - b
    if abs(delta) < precision_rounding / 2:
        return 0
    return 1 if delta > 0 else -1


class PerformanceSyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.quick = get_method('_wh_stock_already_correct', {'float_compare': cmp_rounding})

    def product(self):
        return SimpleNamespace(uom_id=SimpleNamespace(rounding=0.01))

    def wh(self):
        return SimpleNamespace(lot_stock_id=SimpleNamespace(id=5))

    def quant(self, qty, loc=5, reserved=0, owner=False):
        return SimpleNamespace(quantity=qty, reserved_quantity=reserved, lot_id=False,
                               package_id=False, owner_id=owner,
                               location_id=SimpleNamespace(id=loc))

    def test_zero_stock_without_quants_skips_savepoint(self):
        self.assertEqual(self.quick(Recordset(), self.product(), self.wh(), 0), 0.0)

    def test_zero_stock_does_not_skip_when_quantities_cancel(self):
        quants = Recordset([self.quant(5), self.quant(-5, loc=6)])
        self.assertIsNone(self.quick(quants, self.product(), self.wh(), 0))

    def test_positive_target_unchanged_with_child_stock(self):
        quants = Recordset([self.quant(3), self.quant(12, loc=6)])
        self.assertEqual(self.quick(quants, self.product(), self.wh(), 15), 15)
        self.assertIsNone(self.quick(quants, self.product(), self.wh(), 17))

    def test_reservations_and_complex_quants_still_validate(self):
        for q in [self.quant(5, reserved=1), self.quant(5, owner=True)]:
            self.assertIsNone(self.quick(Recordset([q]), self.product(), self.wh(), 5))

    def test_product_and_pricelist_queries_batched(self):
        fn = get_method('_preload_product_batch')
        products = [SimpleNamespace(id=8, default_code='A', product_tmpl_id=SimpleNamespace(id=100)),
                    SimpleNamespace(id=9, default_code='A', product_tmpl_id=SimpleNamespace(id=101)),
                    SimpleNamespace(id=10, default_code='B', product_tmpl_id=SimpleNamespace(id=102))]
        price_rules = [SimpleNamespace(id=32, product_tmpl_id=SimpleNamespace(id=100))]

        class FakeModel:
            def __init__(self, records):
                self.records = records
                self.calls = 0
                self.domain = None
            def sudo(self):
                return self
            def with_company(self, company):
                return self
            def with_context(self, **kwargs):
                return self
            def search(self, domain):
                self.calls += 1
                self.domain = domain
                if self is product_model:
                    codes = next(v for k, op, v in domain if k == 'default_code')
                    return [p for p in self.records if p.default_code in codes]
                return self.records
            def browse(self, ids=None):
                ids = ids or []
                return Recordset([record for record in self.records if record.id in ids])

        product_model = FakeModel(products)
        prices_model = FakeModel(price_rules)
        env = {'product.product': product_model, 'product.pricelist.item': prices_model}
        self_obj = SimpleNamespace(env=env)
        company = SimpleNamespace(id=1)
        pricelist = SimpleNamespace(id=7, name='Web')
        found, rules = fn(self_obj, {'A', 'B', 'C'}, company, pricelist)
        self.assertEqual([p.id for p in found['A']], [8, 9])
        self.assertEqual([p.id for p in found['B']], [10])
        self.assertFalse(found['C'])
        self.assertEqual([r.id for r in rules[100]], [32])
        self.assertFalse(rules[102])
        self.assertEqual(product_model.calls, 1)
        self.assertEqual(prices_model.calls, 1)

    def test_bulk_logs_preserve_all_values(self):
        fn = get_method('_flush_product_logs')
        writes = []
        class FakeModel:
            def sudo(self):
                return self
            def create(self, vals):
                writes.append(vals)
        env = SimpleNamespace(cr=SimpleNamespace(savepoint=nullcontext))
        class ServiceCtx:
            def __init__(self):
                self.env = {'stock.inventory.web.product.log': FakeModel()}
                self.env = FakeEnv(self.env, env.cr)
        class FakeEnv(dict):
            def __init__(self, records, cursor):
                super().__init__(records)
                self.cr = cursor
        ctx = ServiceCtx()
        logs = [{'sku': 'A'}, {'sku': 'B'}, {'sku': 'C'}]
        fn(ctx, logs, SimpleNamespace(id=99))
        self.assertEqual(logs, [])
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0], [{'sku': 'A'}, {'sku': 'B'}, {'sku': 'C'}])

    def test_cron_and_api_form_still_use_same_method(self):
        assert 'def sync_inventory_web_products(' in CODE
        assert 'def _preload_product_batch(' in CODE
        assert 'PROGRESO api_id=' in CODE
        assert 'self._emit_product_audit(run_log, api_record, code, item, trace, state, stocks)' in CODE
        assert 'model.sync_inventory_web_products()' in (ROOT/'data/ir_cron.xml').read_text()
        assert 'name="action_sync_inventory_web"' in (ROOT/'views/inventory_web_views.xml').read_text()


if __name__ == '__main__':
    unittest.main()
