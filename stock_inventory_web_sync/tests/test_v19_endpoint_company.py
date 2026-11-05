# -*- coding: utf-8 -*-
"""Endpoint route and one-pass per company tests without an Odoo server."""
import ast
import importlib.util
import logging
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
modspec = importlib.util.spec_from_file_location('inventory_routes', ROOT / 'models' / 'endpoint_routing.py')
routes = importlib.util.module_from_spec(modspec)
modspec.loader.exec_module(routes)
parse = routes.endpoint_company_and_price


class EndpointIdentityTest(unittest.TestCase):
    def test_explicit_external_company_and_two_prices(self):
        self.assertEqual(parse('https://api.example/inventory_odoo/consulta_odoo/',
                               'show_inventory_web/2/1'), (2, 1))
        self.assertEqual(parse('https://api.example/inventory_odoo/consulta_odoo/',
                               'show_inventory_web/2/2'), (2, 2))

    def test_no_baked_in_company(self):
        self.assertEqual(parse('https://host/', 'show_inventory_web/19/22'), (19, 22))

    def test_relative_endpoint_querystring_trailing_slash(self):
        self.assertEqual(parse('inventory_odoo/consulta_odoo/',
                               'show_inventory_web/5/4/?page=1'), (5, 4))

    def test_old_route_must_not_be_selected(self):
        with self.assertRaises(ValueError):
            parse('https://api.example/', "show_inventory/1/XAD/''/''/1")

    def test_missing_invalid_or_zero_ids(self):
        for url in ('show_inventory_web/0/2', 'show_inventory_web/2/0',
                    'show_inventory_web/2/no', 'show_inventory_web/2/1/extra'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse('', url)

    def test_external_route_company_and_odoo_configured_company_are_distinct(self):
        source = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf8')
        self.assertIn('endpoint_company, external_price = self._api_endpoint_identity(api_record)', source)
        self.assertIn('grouped[endpoint_company].append(api_record.id)', source)
        self.assertIn('target_company_ids = {api.company_id.id for api in api_records if api.company_id}', source)
        self.assertIn("company = self.env['res.company'].sudo().browse(target_company_id).exists()", source)
        self.assertNotIn("browse(endpoint_company_id).exists()", source)
        self.assertNotIn("domain.append(('company_id', '=', int(company_id)))", source)
        self.assertIn("'company_id': company.id", source)

    def test_actual_cron_groups_two_endpoints_for_external_company(self):
        source = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf8')
        klass = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)
                     and n.name == 'StockInventoryWebSync')
        node = next(n for n in klass.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'sync_inventory_web_products')
        code = ast.fix_missing_locations(ast.Module(body=[ast.FunctionDef(
            name=node.name, args=node.args, body=node.body, decorator_list=[],
            returns=None, type_comment=None)], type_ignores=[]))
        ns = {'defaultdict': defaultdict, '_logger': logging.getLogger('route.test')}
        exec(compile(code, '<route-cron-test>', 'exec'), ns)
        apis = [SimpleNamespace(id=23, company_id=SimpleNamespace(id=8),
                                price_list_id=SimpleNamespace(id=31),
                                url='https://host/inventory_odoo/consulta_odoo/',
                                end_point='show_inventory_web/2/1'),
                SimpleNamespace(id=24, company_id=SimpleNamespace(id=8),
                                price_list_id=SimpleNamespace(id=32),
                                url='https://host/inventory_odoo/consulta_odoo/',
                                end_point='show_inventory_web/2/2')]
        class Api:
            def sudo(self): return self
            def search(self, domain): return apis
        class Env(dict):
            def __init__(self): super().__init__({'api.administrator': Api()})
            cr = SimpleNamespace(savepoint=nullcontext)
        class Sync:
            env = Env()
            calls = []
            def _check_sync_access(self): return None
            def _api_endpoint_identity(self, api): return parse(api.url, api.end_point)
            def sync_api(self, ids, execution_type):
                self.calls.append(ids)
                return {'created': 0, 'updated': 1, 'stocks': 1, 'errors': 0}
        svc = Sync()
        ns['sync_inventory_web_products'](svc)
        self.assertEqual(svc.calls, [23])
        svc.calls.clear()
        ns['sync_inventory_web_products'](svc, company_id=2, execution_type='manual')
        self.assertEqual(svc.calls, [23])
        svc.calls.clear()
        ns['sync_inventory_web_products'](svc, company_id=8)
        self.assertEqual(svc.calls, [])

    def test_price_route_distinct_and_company_guard_code(self):
        source = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf8')
        self.assertIn('external_lists = [identity[1] for identity in identities.values()]', source)
        self.assertIn('if len(price_targets) != len(set(price_targets)) and len(api_records) > 1:', source)
        self.assertIn('if price_list and price_list.company_id and price_list.company_id != company:', source)
        self.assertIn('self._preload_multi_price_rules(', source)

    def test_logs_use_odoo_configured_company(self):
        source = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf8')
        self.assertIn("'company_id': run_log.company_id.id", source)
        self.assertIn('run_log.company_id.id, run_id, state', source)

if __name__ == '__main__':
    unittest.main()
