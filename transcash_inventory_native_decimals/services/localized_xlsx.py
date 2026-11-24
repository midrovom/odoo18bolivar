# -*- coding: utf-8 -*-
"""Additional locale-stable preview sheet for Transcash-produced XLSX files.

OOXML numeric payloads use invariant '.' decimal notation by specification;
Excel applies its *own* system separators, not Odoo's `res.lang`. A locale
string in the number-format code cannot reliably override Excel's settings.

We therefore retain the original worksheet verbatim as 'Datos numéricos' and
make 'Formato Odoo' the first worksheet. Only in the first worksheet numerical
cells become locale-formatted inline strings; the second remains 100% numeric,
so Excel arithmetic, sorting and importers still work with full precision.
No processing or additional queries are run against imported data.

Streaming row-by-row prevents building a second giant XML DOM for big exports.
"""

import io
import re
import shutil
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile

MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
DOCREL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKGREL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CTYPES = 'http://schemas.openxmlformats.org/package/2006/content-types'
SHEET = 'xl/worksheets/sheet1.xml'
NEW_SHEET = 'xl/worksheets/sheet2.xml'
XLSX_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


def _q(ns, tag):
    return '{%s}%s' % (ns, tag)


def _series_group(value, separator, grouping):
    if not value or not separator or not grouping:
        return value
    blocks = []
    remaining = value
    index = 0
    previous = 0
    while remaining:
        if index < len(grouping):
            width = grouping[index]
            index += 1
            if width == -1:
                blocks.append(remaining)
                break
            if width == 0:
                if not previous:
                    blocks.append(remaining)
                    break
                width = previous
                index -= 1  # repeat width through the rest of the string
            else:
                previous = width
        else:
            blocks.append(remaining)
            break
        if width <= 0:
            blocks.append(remaining)
            break
        blocks.append(remaining[-width:])
        remaining = remaining[:-width]
    return separator.join(reversed(blocks))


def _number_to_locale(value, cfg, decimal_places=None, prefix='', suffix=''):
    try:
        num = Decimal(str(value))
        if not num.is_finite():
            return None
    except (TypeError, InvalidOperation):
        return None
    if decimal_places is not None:
        with localcontext() as ctx:
            ctx.prec = max(35, len(num.as_tuple().digits) + decimal_places + 4)
            num = num.quantize(Decimal(1).scaleb(-decimal_places), rounding=ROUND_HALF_UP)
            text = format(num.copy_abs(), '.%df' % decimal_places)
    else:
        # Preserve the original precision for 'General' cells.
        text = format(num.copy_abs(), 'f')
    integer, dot, fraction = text.partition('.')
    integer = _series_group(integer, cfg['thousands_sep'], cfg['grouping'])
    displayed = integer + (cfg['decimal_point'] + fraction if dot else '')
    sign = '-' if num.is_signed() and num != 0 else ''
    return sign + prefix + displayed + suffix


def _get_cell_formats(zipped):
    root = ET.fromstring(zipped.read('xl/styles.xml'))
    mapping = {}
    fmts = root.find(_q(MAIN, 'numFmts'))
    if fmts is not None:
        for item in fmts:
            mapping[int(item.attrib['numFmtId'])] = item.attrib.get('formatCode', '')
    xfs = root.find(_q(MAIN, 'cellXfs'))
    answer = {}
    if xfs is None:
        return answer
    for idx, xf in enumerate(xfs):
        code = mapping.get(int(xf.attrib.get('numFmtId', '0')), '')
        # Match formats emitted by the Transcash v18.0.1.51 builders.
        if not code:
            continue
        first_section = code.split(';')[0]
        match = re.search(r'\.([0#?]+)', first_section)
        places = min(len(match.group(1)), 10) if match else 0
        kind = 'currency' if '$' in first_section else ('percent' if '%' in first_section else 'number')
        answer[idx] = (places, kind)
    return answer


def _render_row(row, formats, cfg):
    for cell in row.findall(_q(MAIN, 'c')):
        if cell.attrib.get('t') in ('inlineStr', 's', 'str', 'b', 'e'):
            continue
        if cell.find(_q(MAIN, 'f')) is not None:
            continue
        raw = cell.find(_q(MAIN, 'v'))
        if raw is None or raw.text is None:
            continue
        style = int(cell.attrib.get('s', '0'))
        places, kind = formats.get(style, (None, 'number'))
        display = _number_to_locale(
            raw.text, cfg, places,
            '$' if kind == 'currency' else '',
            '%' if kind == 'percent' else '',
        )
        if display is None:
            continue
        cell.remove(raw)
        cell.attrib['t'] = 'inlineStr'
        content = ET.SubElement(cell, _q(MAIN, 'is'))
        text = ET.SubElement(content, _q(MAIN, 't'), {'{http://www.w3.org/XML/1998/namespace}space': 'preserve'})
        text.text = display


def _write_display_sheet(source, destination, formats, cfg):
    """XML row streaming: at most one <row> and a few metadata nodes live."""
    ET.register_namespace('', MAIN)
    destination.write(('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                       '<worksheet xmlns="%s">' % MAIN).encode('utf-8'))
    stack = []
    root = None
    in_data = False
    for event, elem in ET.iterparse(source, events=('start', 'end')):
        if event == 'start':
            if root is None:
                root = elem
            stack.append(elem)
            if elem.tag == _q(MAIN, 'sheetData') and len(stack) == 2:
                destination.write(b'<sheetData>')
                in_data = True
            continue
        # end event, while stack still contains current element
        if in_data and len(stack) == 3 and elem.tag == _q(MAIN, 'row'):
            _render_row(elem, formats, cfg)
            destination.write(ET.tostring(elem, encoding='utf-8'))
            stack[-2].remove(elem)
        elif elem.tag == _q(MAIN, 'sheetData') and len(stack) == 2:
            destination.write(b'</sheetData>')
            in_data = False
            root.remove(elem)
        elif len(stack) == 2:  # other top-level worksheet children
            destination.write(ET.tostring(elem, encoding='utf-8'))
            root.remove(elem)
        stack.pop()
    destination.write(b'</worksheet>')


def _changed_workbook(xml):
    ET.register_namespace('', MAIN)
    ET.register_namespace('r', DOCREL)
    root = ET.fromstring(xml)
    sheets = root.find(_q(MAIN, 'sheets'))
    original = list(sheets)
    if len(original) != 1:
        raise ValueError('Se esperaba una única hoja de TRANSCASH.')
    original[0].set('name', 'Formato Odoo')
    ET.SubElement(sheets, _q(MAIN, 'sheet'), {
        'name': 'Datos numéricos', 'sheetId': '2', _q(DOCREL, 'id'): 'rId3'
    })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def _changed_relationships(xml):
    ET.register_namespace('', PKGREL)
    root = ET.fromstring(xml)
    ET.SubElement(root, _q(PKGREL, 'Relationship'), {
        'Id': 'rId3',
        'Type': DOCREL + '/worksheet',
        'Target': 'worksheets/sheet2.xml',
    })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def _changed_types(xml):
    ET.register_namespace('', CTYPES)
    root = ET.fromstring(xml)
    ET.SubElement(root, _q(CTYPES, 'Override'), {
        'PartName': '/' + NEW_SHEET,
        'ContentType': 'application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml',
    })
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def add_odoo_display_sheet(data, cfg):
    """Return XLSX with display + unchanged numeric sheets, or original data.

    Intended only for Transcash-generated XLSX endpoints; caller does no patch
    on errors, uploads, or arbitrary third-party Excel files.
    """
    output = io.BytesIO()
    with ZipFile(io.BytesIO(data), 'r') as src:
        required = {SHEET, 'xl/styles.xml', 'xl/workbook.xml',
                    'xl/_rels/workbook.xml.rels', '[Content_Types].xml'}
        if not required.issubset(src.namelist()) or NEW_SHEET in src.namelist():
            return data
        formats = _get_cell_formats(src)
        with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=5, allowZip64=True) as dst:
            for item in src.infolist():
                name = item.filename
                if name == SHEET:
                    with src.open(name) as fsrc, dst.open(name, 'w', force_zip64=True) as fdst:
                        _write_display_sheet(fsrc, fdst, formats, cfg)
                elif name in ('xl/workbook.xml', 'xl/_rels/workbook.xml.rels', '[Content_Types].xml'):
                    original = src.read(name)
                    changed = (_changed_workbook(original) if name == 'xl/workbook.xml' else
                               _changed_relationships(original) if name == 'xl/_rels/workbook.xml.rels' else
                               _changed_types(original))
                    dst.writestr(name, changed)
                else:
                    with src.open(item) as fsrc, dst.open(name, 'w', force_zip64=True) as fdst:
                        shutil.copyfileobj(fsrc, fdst, length=1024 * 1024)
            with src.open(SHEET) as fsrc, dst.open(NEW_SHEET, 'w', force_zip64=True) as fdst:
                shutil.copyfileobj(fsrc, fdst, length=1024 * 1024)
    return output.getvalue()
