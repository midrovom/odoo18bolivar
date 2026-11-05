# -*- coding: utf-8 -*-
"""No automatic pricelist creation in the inventory-web sync module."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'models' / 'inventory_web_sync.py').read_text(encoding='utf-8')


class PricelistNoCreationTests(unittest.TestCase):
    def test_no_legacy_auto_creating_methods(self):
        self.assertNotIn('def _ensure_wholesale_pricelist(', SOURCE)
        self.assertNotIn('def _fix_price_feed_overlap(', SOURCE)
        self.assertNotIn('PRECIO_LISTA_AUTOMAPEADA', SOURCE)
        self.assertNotIn('LISTA_MAYORISTA_CONFIGURADA', SOURCE)

    def test_no_price_list_create_or_auto_assignments(self):
        self.assertNotIn('Pricelist.create(', SOURCE)
        self.assertNotIn('PriceList.create(', SOURCE)
        self.assertNotIn("write({'price_list_id'", SOURCE)

    def test_api_requires_a_preexisting_selected_pricelist(self):
        self.assertIn('self._validate_existing_pricelist(price_api, company)', SOURCE)
        self.assertIn('return api_record.price_list_id or False', SOURCE)
        self.assertIn('if not pricelist:', SOURCE)

    def test_duplicate_feeds_rejected_not_autocreated(self):
        self.assertIn('if len(price_targets) != len(set(price_targets)) and len(api_records) > 1:', SOURCE)


if __name__ == '__main__':
    unittest.main()
