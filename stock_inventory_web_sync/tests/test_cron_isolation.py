# -*- coding: utf-8 -*-
"""Pruebas estáticas y de migración ejecutables sin un servidor Odoo."""
import ast
import logging
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


MODULE_ROOT = Path(__file__).resolve().parent.parent


class CronIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (MODULE_ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')
        cls.tree = ast.parse(cls.code)
        cls.job_xml = ET.parse(MODULE_ROOT / 'data' / 'ir_cron.xml').getroot()

    def test_new_method_replaces_legacy_name_in_new_model(self):
        stock_class = next(node for node in self.tree.body
                           if isinstance(node, ast.ClassDef) and node.name == 'StockInventoryWebSync')
        methods = {node.name for node in stock_class.body if isinstance(node, ast.FunctionDef)}
        self.assertIn('sync_inventory_web_products', methods)
        self.assertNotIn('sync_all_inventory', methods)

    def test_new_cron_calls_new_method(self):
        cron = self.job_xml.find(".//record[@id='ir_cron_inventory_web_sync']")
        self.assertIsNotNone(cron)
        self.assertEqual(cron.find("field[@name='code']").text,
                         'model.sync_inventory_web_products()')
        self.assertEqual(cron.find("field[@name='active']").get('eval'), 'True')

    def test_upgrade_function_outside_noupdate(self):
        blocks = self.job_xml.findall('data')
        self.assertGreaterEqual(len(blocks), 2)
        self.assertEqual(blocks[0].get('noupdate'), '1')
        self.assertNotEqual(blocks[1].get('noupdate'), '1')
        migrated = blocks[1].find("function[@model='stock.inventory.web.sync']")
        self.assertIsNotNone(migrated)
        self.assertEqual(migrated.get('name'), '_migrate_inventory_web_cron_code')

    def test_selection_is_separate_from_legacy_stock_flag(self):
        service = next(node for node in self.tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'StockInventoryWebSync')
        method = next(node for node in service.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'sync_inventory_web_products')
        text = ast.get_source_segment(self.code, method)
        self.assertIn("('inventory_web_products_enabled', '=', True)", text)
        self.assertNotIn("('is_stock_update', '=', True)", text)

    def test_migration_only_touches_new_model_actions(self):
        # Extrae el método para probarlo sin importar Odoo (no disponible aquí).
        service = next(node for node in self.tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'StockInventoryWebSync')
        node = next(node for node in service.body
                    if isinstance(node, ast.FunctionDef) and node.name == '_migrate_inventory_web_cron_code')
        cloned = ast.FunctionDef(name=node.name, args=node.args, body=node.body,
                                 decorator_list=[], returns=node.returns, type_comment=None)
        module = ast.fix_missing_locations(ast.Module(body=[cloned], type_ignores=[]))
        namespace = {'_logger': logging.getLogger(__name__)}
        exec(compile(module, '<migration-test>', 'exec'), namespace)
        migrate = namespace[node.name]

        class Job:
            def __init__(self, code):
                self.code = code
                self.id = 25
                self.name = 'Cron nuevo'
                self.active = False
                self.model_id = type('Model', (), {'model':'stock.inventory.web.sync'})()
            def sudo(self):
                return self
            def write(self, vals):
                self.code = vals.get('code', self.code)
                self.active = vals.get('active', self.active)

        class Jobs:
            def __init__(self):
                self.searched_domain = []
                self.jobs = [Job('model.sync_all_inventory(2)'), Job('model.otra_accion()')]
            def sudo(self):
                return self
            def search(self, domain):
                self.searched_domain = domain
                return self.jobs

        class Env:
            def __init__(self):
                self.jobs = Jobs()
                self.canonical = Job('model.sync_all_inventory(2)')
            def ref(self, xmlid, raise_if_not_found=False):
                assert xmlid == 'stock_inventory_web_sync.ir_cron_inventory_web_sync'
                return self.canonical
            def __getitem__(self, name):
                assert name == 'ir.cron'
                return self.jobs

        class Service:
            def __init__(self):
                self.env = Env()

        fake_service = Service()
        self.assertTrue(migrate(fake_service))
        self.assertIn(('model_id.model', '=', 'stock.inventory.web.sync'),
                      fake_service.env.jobs.searched_domain)
        self.assertEqual(fake_service.env.jobs.jobs[0].code,
                         'model.sync_inventory_web_products(2)')
        self.assertEqual(fake_service.env.jobs.jobs[1].code, 'model.otra_accion()')
        self.assertTrue(fake_service.env.canonical.active)
        self.assertEqual(fake_service.env.canonical.code, 'model.sync_inventory_web_products()')


if __name__ == '__main__':
    unittest.main()
