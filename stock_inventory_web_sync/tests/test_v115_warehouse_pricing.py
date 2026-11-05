# -*- coding: utf-8 -*-
import importlib.util
import pathlib
import unittest
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    'warehouse_price_routing', ROOT / 'models' / 'warehouse_price_routing.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestWarehousePricing(unittest.TestCase):
    def test_selected_and_product_present_uses_public(self):
        self.assertEqual(module.price_field_for_warehouse(3, [2, 3], [3, 5]), 'Precio')

    def test_selected_but_product_missing_uses_wholesale(self):
        self.assertEqual(module.price_field_for_warehouse(3, [3], [5]), 'Precio_2')

    def test_nonselected_present_uses_wholesale(self):
        self.assertEqual(module.price_field_for_warehouse(5, [3], [3, 5]), 'Precio_2')

    def test_no_selected_uses_wholesale(self):
        self.assertEqual(module.price_field_for_warehouse(5, [], [5]), 'Precio_2')

    def test_empty_product_warehouses_uses_wholesale(self):
        self.assertEqual(module.price_field_for_warehouse(3, [3], []), 'Precio_2')

    def test_no_warehouse_id_uses_wholesale(self):
        self.assertEqual(module.price_field_for_warehouse(False, [3], [3]), 'Precio_2')

    def test_many_selected_and_many_product_warehouses(self):
        selected = [1, 2, 3]
        product = [2, 4, 6]
        self.assertEqual(module.price_field_for_warehouse(2, selected, product), 'Precio')
        self.assertEqual(module.price_field_for_warehouse(4, selected, product), 'Precio_2')

    def test_zero_quantity_is_not_used_for_price_mapping(self):
        # Product stock zero is still present in the Bodegas list.
        self.assertEqual(module.price_field_for_warehouse(1, {1}, {1}), 'Precio')

    def test_xml_selector_is_m2m_and_original_m2o_retained(self):
        tree = ElementTree.parse(ROOT / 'views' / 'inventory_web_views.xml')
        fields = [f.attrib for f in tree.findall('.//field')]
        self.assertTrue(any('warehouse_id' in (field.attrib.get('expr') or '') for field in tree.findall('.//xpath')))
        self.assertTrue(any(f.get('name') == 'inventory_web_price_warehouse_ids'
                            and f.get('widget') == 'many2many_tags' for f in fields))
        source = (ROOT / 'models' / 'api_administrator.py').read_text()
        self.assertIn('inventory_web_price_warehouse_ids = fields.Many2many(', source)
        self.assertNotIn('warehouse_id = fields.Many2many(', source)

    def test_pricing_only_on_selected_pricelist(self):
        code = (ROOT / 'models' / 'sale_order_line.py').read_text()
        self.assertIn("('price_list_id', '=', self.order_id.pricelist_id.id)", code)
        self.assertIn('self.product_id.inventory_web_warehouse_ids.ids', code)
        self.assertIn('def _get_display_price(self):', code)

    def test_cron_stays_independent(self):
        code = (ROOT / 'data' / 'ir_cron.xml').read_text()
        self.assertIn('model.sync_inventory_web_products()', code)
        self.assertNotIn('model.sync_all_inventory(', code)


if __name__ == '__main__':
    unittest.main()
