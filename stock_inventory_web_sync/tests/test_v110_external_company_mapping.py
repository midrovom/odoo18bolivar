# -*- coding: utf-8 -*-
"""Regression: the endpoint's external company 2 is NOT res.company(2)."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')


class UserError(Exception):
    pass


class ApiRecords(list):
    @property
    def ids(self):
        return [rec.id for rec in self]


class Companies:
    def __init__(self):
        self.resolved_ids = []
    def sudo(self):
        return self
    def browse(self, company_id):
        self.resolved_ids.append(company_id)
        return SimpleNamespace(exists=lambda: SimpleNamespace(
            id=company_id, display_name='Empresa Odoo de prueba'))


class Environment(dict):
    pass


def execute_company_mapping(external_company, configured_ids):
    """Execute the exact AST statements of sync_api company resolution."""
    tree = ast.parse(SOURCE)
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                 and n.name == 'StockInventoryWebSync')
    method = next(n for n in klass.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'sync_api')
    start = next(i for i, node in enumerate(method.body)
                 if isinstance(node, ast.Assign) and any(
                     isinstance(target, ast.Name) and target.id == 'endpoint_company_id'
                     for target in node.targets))
    stop = next(i for i, node in enumerate(method.body[start:])
                if isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == 'external_lists'
                    for target in node.targets)) + start
    statements = method.body[start:stop]
    ns = {'UserError': UserError, '_': lambda text: text,
          '_logger': SimpleNamespace(info=lambda *a, **kw: None)}
    companies = Companies()
    env = Environment({'res.company': companies})
    apis = ApiRecords([SimpleNamespace(id=i + 23,
                                       company_id=SimpleNamespace(id=company_id) if company_id else None)
                       for i, company_id in enumerate(configured_ids)])
    ns.update({'endpoint_company_ids': {external_company}, 'api_records': apis,
               'self': SimpleNamespace(env=env)})
    exec(compile(ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])),
                 '<real-company-mapping>', 'exec'), ns)
    return ns.get('company'), companies.resolved_ids


class ExternalCompanyMappingTest(unittest.TestCase):
    def test_source_company_two_maps_to_odoo_company_other_than_two(self):
        company, resolved_ids = execute_company_mapping(2, [7, 7])
        self.assertEqual(resolved_ids, [7])
        self.assertEqual(company.id, 7)

    def test_target_company_can_have_id_one(self):
        company, resolved_ids = execute_company_mapping(2, [1, 1])
        self.assertEqual(resolved_ids, [1])
        self.assertEqual(company.id, 1)

    def test_different_configured_odoo_companies_are_rejected_before_updates(self):
        with self.assertRaisesRegex(UserError, 'misma Empresa'):
            execute_company_mapping(2, [7, 8])

    def test_missing_odoo_company_is_rejected_before_updates(self):
        with self.assertRaisesRegex(UserError, 'misma Empresa'):
            execute_company_mapping(2, [7, None])

    def test_external_ids_not_hardcoded(self):
        company, resolved_ids = execute_company_mapping(4, [7, 7])
        self.assertEqual(resolved_ids, [7])
        self.assertEqual(company.id, 7)

    def test_cron_and_manual_still_share_one_pass(self):
        source = (ROOT / 'models' / 'api_administrator.py').read_text(encoding='utf-8')
        self.assertIn('service.sync_inventory_web_products(', source)
        self.assertIn('company_id=endpoint_company', source)
        self.assertIn("model.sync_inventory_web_products()", (ROOT / 'data' / 'ir_cron.xml').read_text())

    def test_error_that_triggered_bug_removed(self):
        self.assertNotIn('La empresa ID %s recibida desde show_inventory_web no existe en Odoo', SOURCE)
        self.assertNotIn('browse(endpoint_company_id).exists()', SOURCE)
        self.assertIn('empresa_externa=%s empresa_odoo=%s', SOURCE)


if __name__ == '__main__':
    unittest.main()
