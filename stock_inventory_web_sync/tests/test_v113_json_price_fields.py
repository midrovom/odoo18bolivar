# -*- coding: utf-8 -*-
"""Regression checks: Price and Price_2 are distinct JSON fields, not URL prices."""
import ast
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location('field_price_merge', ROOT / 'models' / 'combined_payload.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
COMBINE = MODULE.combine_catalogs
TARGETS = {1: 23, 2: 24}


def row(sku='PORPBGBOURSANDMAT', public=18.5571, sale=14.2714, stock=123.8298):
    return {
        'codigo': sku, 'Nombre': 'PORCELANATO PBG BOURBON SAND MAT',
        'Precio': public, 'Precio_2': sale, 'StockTotal': stock,
        'Bodegas': [
            {'Bodega': 'ABS', 'StockBodega': 96.3213},
            {'Bodega': 'ANT', 'StockBodega': 1.66},
            {'Bodega': 'CDT', 'StockBodega': 0},
            {'Bodega': 'NAJ', 'StockBodega': 25.8485},
        ],
    }


class FieldPriceTests(unittest.TestCase):
    def test_user_payload_applies_both_json_fields(self):
        items, notices = COMBINE([(23, False, [row()]), (24, 66, [row()])], TARGETS)
        self.assertEqual(len(items), 1)
        product = items[0]
        self.assertEqual(product['_inventory_web_prices'], [(23, 18.5571), (24, 14.2714)])
        self.assertEqual(product['_inventory_web_price_sources'], {1: 23, 2: 24})
        self.assertEqual(product['StockTotal'], 123.8298)
        self.assertEqual(len(product['Bodegas']), 4)
        self.assertFalse(notices)

    def test_prices_do_not_depend_on_endpoint_price_field(self):
        second = row(public=900, sale=8.5)
        first = row(public=18.5571, sale=900)
        merged, warnings = COMBINE([(24, 66, [second]), (23, False, [first])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571), (24, 8.5)])
        self.assertTrue(any('Precio distinto' in msg for msg in warnings))
        self.assertTrue(any('Precio_2 distinto' in msg for msg in warnings))

    def test_works_if_only_one_feed_responded(self):
        merged, notices = COMBINE([(23, False, [row()])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571), (24, 14.2714)])
        self.assertEqual(merged[0]['_inventory_web_price_sources'], {1: 23, 2: 23})
        self.assertFalse(notices)

    def test_only_second_feed_responded(self):
        merged, notices = COMBINE([(24, 66, [row()])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571), (24, 14.2714)])
        self.assertEqual(merged[0]['_inventory_web_price_sources'], {1: 24, 2: 24})
        self.assertFalse(notices)

    def test_zero_is_valid_explicit_sale_price(self):
        merged, _ = COMBINE([(23, False, [row(sale=8.2)]), (24, 66, [row(sale=0)])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571), (24, 0)])

    def test_missing_price_2_is_not_imputed_from_precio(self):
        payload = row()
        del payload['Precio_2']
        merged, _ = COMBINE([(23, False, [payload])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571)])

    def test_only_second_field_available(self):
        payload = row()
        del payload['Precio']
        merged, _ = COMBINE([(24, 66, [payload])], TARGETS)
        self.assertEqual(merged[0]['_inventory_web_prices'], [(24, 14.2714)])

    def test_different_products_union_without_duplicating_stock(self):
        a = row(sku='A')
        b = row(sku='B')
        merged, _ = COMBINE([(23, False, [a]), (24, 66, [a, b])], TARGETS)
        self.assertEqual({p['codigo'] for p in merged}, {'A', 'B'})
        self.assertEqual(len(merged[0]['Bodegas']), 4)
        self.assertEqual(merged[0]['Bodegas'][0]['StockBodega'], 96.3213)

    def test_source_routing_connected_to_odoo_sync_path(self):
        src = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')
        self.assertIn('price_targets=price_api_targets', src)
        self.assertIn("price_api_targets = ({1: api_record.id, 2: api_record.id}", src)
        self.assertIn("price_source_records=price_api_by_id,", src)
        self.assertIn("price_field = 'Precio' if external_price_id == 1 else 'Precio_2'", src)
        self.assertIn("values['inventory_web_price_%s' % field_id] = amount", src)
        self.assertIn("target_pricelist = self._price_list_destination(source_api, external_price_id)", src)
        self.assertIn('PRECIO_CAMPO', src)

    def test_missing_destination_does_not_write_wrong_pricelist(self):
        merged, _ = COMBINE([(23, False, [row()])], {1: 23})
        self.assertEqual(merged[0]['_inventory_web_prices'], [(23, 18.5571)])


if __name__ == '__main__':
    unittest.main()
