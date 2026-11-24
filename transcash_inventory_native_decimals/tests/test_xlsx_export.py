"""Standalone regression test: python tests/test_xlsx_export.py.

Uses the unmodified Transcash exporter, not Odoo runtime. Supply a path to
original module via TRANSCASH_MODULE_DIR env, or place it alongside source.
"""
import io
import importlib.util
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(os.getenv('TRANSCASH_MODULE_DIR', str(ROOT.parent / 'transcash_inventory')))
sys.path.insert(0, str(ROOT / 'services'))
from localized_xlsx import add_odoo_display_sheet, MAIN


def source_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, str(SRC / relative))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def check_workbook(binary, cfg, sheet_name, number_ref, display_text, numeric='1234567.89'):
    output = add_odoo_display_sheet(binary, cfg)
    with zipfile.ZipFile(io.BytesIO(output)) as z:
        assert z.testzip() is None
        assert 'xl/worksheets/sheet2.xml' in z.namelist()
        book = ET.fromstring(z.read('xl/workbook.xml'))
        names = [x.attrib['name'] for x in book.findall('.//{%s}sheet' % MAIN)]
        assert names == ['Formato Odoo', 'Datos numéricos'], names
        display = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        original = ET.fromstring(z.read('xl/worksheets/sheet2.xml'))
        current = display.find('.//{%s}c[@r="%s"]' % (MAIN, number_ref))
        raw = original.find('.//{%s}c[@r="%s"]' % (MAIN, number_ref))
        assert current.attrib.get('t') == 'inlineStr', current.attrib
        assert ''.join(current.itertext()) == display_text, ''.join(current.itertext())
        assert raw.attrib.get('t') != 'inlineStr'
        assert raw.find('{%s}v' % MAIN).text == numeric
        # non-numeric strings are still strings and preserved, including escapes
        assert display.find('.//{%s}c[@r="A8"]' % MAIN) is not None
        print('OK', sheet_name, cfg['decimal_point'], number_ref, display_text)


def main():
    table = source_module('table_export', 'services/table_export.py')
    ai = source_module('ai_export', 'services/ai_export.py')
    src1 = table.build_table_xlsx('Inventario', 'Empresa',
        ['SKU', 'Valor $', 'Margen %', 'Cantidad'],
        [['COD001', 1234567.89, 12.5, -1200.6], ['COD002', 9.1, 3.5, 0]])
    es = {'decimal_point': ',', 'thousands_sep': '.', 'grouping': [3,0]}
    en = {'decimal_point': '.', 'thousands_sep': ',', 'grouping': [3,0]}
    check_workbook(src1, es, 'table', 'B8', '$1.234.567,89')
    check_workbook(src1, en, 'table', 'B8', '$1,234,567.89')
    with zipfile.ZipFile(io.BytesIO(add_odoo_display_sheet(src1, es))) as z:
        row = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        for ref, expected in [('C8', '12,50%'), ('D8', '-1.200,60')]:
            cel = row.find('.//{%s}c[@r="%s"]' % (MAIN, ref))
            assert ''.join(cel.itertext()) == expected
    result = {'filas': [{'grupo': 'A', 'metricas': {'ventas': 1234567.89}}],
              'metricas': ['ventas'], 'totales': {'ventas': 1234567.89}}
    src2 = ai.build_result_xlsx(result, 'Cuánto vendí?')
    check_workbook(src2, es, 'ai', 'B8', '$1.234.567,89')
    # Odoo grouping including Indian, and no thousands group
    indian = {'decimal_point': ',', 'thousands_sep': ' ', 'grouping': [3,2,0]}
    check_workbook(src1, indian, 'indian', 'B8', '$12 34 567,89')
    print('OK: Excel keeps numeric originals plus locale-accurate display strings.')

if __name__ == '__main__':
    main()
