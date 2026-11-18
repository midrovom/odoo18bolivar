# -*- coding: utf-8 -*-
"""Integration tests: run inside Odoo 18 with --test-enable."""
import base64
import io
import zipfile

from odoo.tests.common import TransactionCase


def _sample_xlsx(net='25'):
    """Build an independent, minimal XLSX, never using bundled customer data."""
    cols = ('Tipo', 'numero', 'FechaFactura', 'nlocal', 'Codproducto',
            'Cantidad', 'Total_neto', 'Total_Costo', 'Producto')
    values = ('FA', 'TEST-EXCEL-9001', '2026-11-09', 'LOCAL TEST EXCEL',
              'SKU-EXCEL-001', '2', net, '13', 'Producto de prueba')
    def cell(i, row, value):
        tag = chr(ord('A') + i) + str(row)
        return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (tag, value)
    sheet = ('<?xml version="1.0" encoding="utf-8"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData><row r="1">%s</row><row r="2">%s</row></sheetData></worksheet>' %
             (''.join(cell(i, 1, name) for i, name in enumerate(cols)),
              ''.join(cell(i, 2, value) for i, value in enumerate(values))))
    workbook = ('<?xml version="1.0" encoding="utf-8"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Movimientos" sheetId="1" r:id="rId1"/></sheets></workbook>')
    rels = ('<?xml version="1.0" encoding="utf-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Target="worksheets/sheet1.xml" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"/>'
            '</Relationships>')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode='w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('xl/workbook.xml', workbook)
        z.writestr('xl/_rels/workbook.xml.rels', rels)
        z.writestr('xl/worksheets/sheet1.xml', sheet)
    return base64.b64encode(stream.getvalue()).decode('ascii')


class TestAnalyticsSalesExcelImport(TransactionCase):
    def test_file_selection_merge_then_replace(self):
        # Default Odoo technical users are no longer Analytics Sales admins.
        self.env.user.sudo().write({'groups_id': [
            (4, self.env.ref('analytics_sales.group_analytics_sales_admin').id),
        ]})
        Wizard = self.env['analytics.sales.excel.import']
        Move = self.env['analytics.sales.move'].sudo()
        domain = [('company_id', '=', self.env.company.id),
                  ('document_number', '=', 'TEST-EXCEL-9001'),
                  ('source_kind', '=', 'historico')]
        wizard = Wizard.create({'upload_file': _sample_xlsx(),
                                'filename': 'ventas_prueba.xlsx', 'import_mode': 'merge'})
        wizard.action_import()
        self.assertEqual(Move.search_count(domain), 1)
        wizard2 = Wizard.create({'upload_file': _sample_xlsx(),
                                 'filename': 'otro_nombre.xlsx', 'import_mode': 'merge'})
        wizard2.action_import()
        self.assertEqual(Move.search_count(domain), 1)
        wizard3 = Wizard.create({'upload_file': _sample_xlsx('55'),
                                 'filename': 'ventas_actualizadas.xlsx', 'import_mode': 'merge'})
        wizard3.action_import()
        self.assertEqual(Move.search_count(domain), 1)
        self.assertAlmostEqual(Move.search(domain).total_net, 55)
        self.assertTrue(self.env['analytics.sales.sync.log'].search([
            ('company_id', '=', self.env.company.id),
            ('origin', '=', 'historico'), ('state', '=', 'ok'),
        ], limit=1))
