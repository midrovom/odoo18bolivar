# -*- coding: utf-8 -*-
"""Pruebas de emisión por SKU/almacén sin cargar el servidor Odoo."""
import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import logging
import unittest

ROOT = Path(__file__).resolve().parents[1]


def extract_method(name, extra=None):
    source = (ROOT / 'models/inventory_web_sync.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    model = next(cls for cls in tree.body if isinstance(cls, ast.ClassDef)
                 and cls.name == 'StockInventoryWebSync')
    method = next(node for node in model.body
                  if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    code = compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                   '<test_method>', 'exec')
    namespace = dict(extra or {})
    exec(code, namespace)
    return namespace[name]


spec = importlib.util.spec_from_file_location('warehouse_payload', ROOT / 'models/warehouse_payload.py')
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)


class ServerAuditLogTest(unittest.TestCase):
    def test_method_and_cron_tag_present(self):
        source = (ROOT / 'models/inventory_web_sync.py').read_text(encoding='utf-8')
        for marker in ('[INV_WEB_SYNC] CRON_INICIO', '[INV_WEB_SYNC] SIN_APIS',
                       '[INV_WEB_SYNC] PRODUCTO', '[INV_WEB_SYNC] PRECIO',
                       '[INV_WEB_SYNC] BODEGA', '[INV_WEB_SYNC] CRON_FIN'):
            self.assertIn(marker, source)
        self.assertIn('self._emit_product_audit(run_log, api_record, code, item, trace, state, stocks)', source)
        self.assertIn('with self.env.cr.savepoint():', source)

    def test_audit_lines_include_each_warehouse_even_zero_and_unchanged(self):
        logger = logging.getLogger('inventario.web.audit.test')
        fn = extract_method('_emit_product_audit', {'_logger': logger, 'logging': logging})
        ctx = SimpleNamespace(_string=lambda x: str(x).strip(),
                              _log_value=lambda x: '(vacío)' if x is None else str(x))
        api = SimpleNamespace(id=9, company_id=SimpleNamespace(id=2))
        item = {'Nombre': 'ALICATE NIVELA PISO', 'Precio': 25.31, 'StockTotal': 15}
        trace = {'product_id': 203, 'price_event': {'label': 'Lista web', 'before': 20,
                 'after': 25.31, 'state': 'ACTUALIZADO'},
                 'warehouse_events': [
                     {'code': 'ABS', 'target': 0, 'before': 5, 'after': 0,
                      'warehouse_id': 10, 'warehouse_name': 'Abastos', 'state': 'AJUSTADA'},
                     {'code': 'ANT', 'target': 12, 'before': 12, 'after': 12,
                      'warehouse_id': 11, 'warehouse_name': 'Ant', 'state': 'SIN_CAMBIOS'},
                     {'code': 'NAJ', 'target': 3, 'before': None, 'after': None,
                      'warehouse_id': 12, 'warehouse_name': 'Naj', 'state': 'OMITIDA',
                      'reason': 'Hay reservas'},
                 ]}
        with self.assertLogs(logger, level='INFO') as captured:
            fn(ctx, SimpleNamespace(id=44, company_id=SimpleNamespace(id=2)), api, 'MOLDALIPISUNI', item, trace, 'warning', 1)
        output = '\n'.join(captured.output)
        self.assertIn('PRODUCTO sku=MOLDALIPISUNI', output)
        self.assertIn('PRECIO sku=MOLDALIPISUNI', output)
        self.assertIn('BODEGA sku=MOLDALIPISUNI bodega=ABS', output)
        self.assertIn('anterior=5 cantidad_api=0 final=0 resultado=AJUSTADA', output)
        self.assertIn('BODEGA sku=MOLDALIPISUNI bodega=ANT', output)
        self.assertIn('resultado=SIN_CAMBIOS', output)
        self.assertIn('BODEGA sku=MOLDALIPISUNI bodega=NAJ', output)
        self.assertIn('resultado=OMITIDA motivo=Hay reservas', output)
        self.assertIn('ejecucion_id=44', output)

    def test_stock_warehouse_result_events(self):
        logger = logging.getLogger('inventario.web.audit.test.stock')
        fn = extract_method('_sync_warehouses', {
            '_logger': logger,
            'stock_targets': payload.stock_targets,
            'UserError': type('UserError', (Exception,), {}),
            'ValidationError': type('ValidationError', (Exception,), {}),
        })
        warehouses = {code: SimpleNamespace(id=i+1, display_name=code,
                       lot_stock_id=True) for i, code in enumerate(['ABS', 'ANT', 'NAJ'])}
        class Context:
            def __init__(self):
                self.env = SimpleNamespace(cr=SimpleNamespace(savepoint=nullcontext))
            def _set_wh_stock(self, product, wh, target, company):
                before = {'ABS': 5, 'ANT': 12, 'NAJ': 3}[wh.display_name]
                return before != target, before, target
            def _log_value(self, value):
                return str(value)
        trace = {'lines': [], 'warehouse_events': []}
        item = {'StockTotal': 15, 'Bodegas': [
            {'Bodega': 'ABS', 'StockBodega': 0},
            {'Bodega': 'ANT', 'StockBodega': 12},
            {'Bodega': 'NAJ', 'StockBodega': 3},
        ]}
        count, warnings = fn(Context(), item, SimpleNamespace(default_code='SKU'),
                             SimpleNamespace(name='Empresa'), warehouses, trace)
        self.assertEqual(count, 1)
        self.assertEqual(warnings, [])
        self.assertEqual([ev['state'] for ev in trace['warehouse_events']],
                         ['AJUSTADA', 'SIN_CAMBIOS', 'SIN_CAMBIOS'])
        self.assertEqual(trace['warehouse_events'][0]['after'], 0.0)

    def test_stock_total_zero_audits_every_company_warehouse(self):
        warehouse_map = {'ABS': object(), 'ANT': object(), 'NAJ': object()}
        targets, notices = payload.stock_targets({'StockTotal': 0, 'Bodegas': [
            {'Bodega': 'ANT', 'StockBodega': 0},
        ]}, warehouse_map)
        self.assertEqual(targets, {'ABS': 0.0, 'ANT': 0.0, 'NAJ': 0.0})
        self.assertEqual(notices, [])

if __name__ == '__main__':
    unittest.main()
