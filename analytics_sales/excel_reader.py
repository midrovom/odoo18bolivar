# -*- coding: utf-8 -*-
"""Read user-supplied commercial Excel files without bundling any customer data.

XLSX is parsed with the standard library, so Odoo requires no extra dependency.
The optional older XLS format requires xlrd installed in the Odoo environment.
"""
import io
import posixpath
import re
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta


class SalesExcelError(ValueError):
    pass


MAX_UPLOAD_BYTES = 30 * 1024 * 1024
MAX_ROWS = 350000
MAX_COLUMNS = 160
MAX_SHARED_STRINGS_BYTES = 120 * 1024 * 1024
MAX_WORKSHEET_BYTES = 380 * 1024 * 1024

_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
_REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
_PACKAGE_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'


def _tag(name):
    return '{%s}%s' % (_NS, name)


def _header_key(value):
    normalized = unicodedata.normalize('NFKD', str(value or ''))
    ascii_value = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]', '', ascii_value.lower())


# Canonical names correspond to fields supported by analytics.sales.sync._normalize().
# The local used for security is NEVER inferred from the warehouse/bodega field.
_ALIASES = {
    'Tipo': ('tipo', 'tipofactura', 'tipodocumento', 'documenttype', 'type'),
    'numero': ('numero', 'numerofactura', 'nrofactura', 'nfactura', 'nofactura', 'nrodocumento', 'ndocumento', 'numerodocumento', 'documentnumber', 'documento'),
    'FechaFactura': ('fechafactura', 'fechadefactura', 'fecha', 'date', 'fechaemision'),
    'nlocal': ('nlocal', 'local', 'sucursal', 'tienda'),
    'Codproducto': ('codproducto', 'codigoproducto', 'codigodeproducto', 'sku', 'productcode', 'referencia'),
    'Cantidad': ('cantidad', 'cantidadvendida', 'quantity', 'qty', 'unidades'),
    'Total_neto': ('totalneto', 'nettotal', 'netamount', 'valorneto', 'ventaneta', 'importeneto'),
    'Total_Costo': ('totalcosto', 'costtotal', 'totalcost', 'costototal'),
    'costo': ('costo', 'cost', 'unitcost', 'costounitario'),
    'Factura': ('factura', 'invoicedisplay'),
    'Vendedor': ('vendedor', 'seller', 'nombrevendedor'),
    'CodVendedor': ('codvendedor', 'sellercode', 'codigovendedor'),
    'Linea': ('linea', 'line', 'lineaproducto', 'categoria'),
    'Marca': ('marca', 'brand'),
    'Producto': ('producto', 'descripcion', 'productname'),
    'Modelo': ('modelo',),
    'id_linea': ('idlinea', 'lineid', 'iddetalle', 'detailid'),
}
_CANONICAL = {alias: original for original, aliases in _ALIASES.items() for alias in aliases}
_REQUIRED = ('Tipo', 'numero', 'FechaFactura', 'nlocal', 'Codproducto', 'Cantidad', 'Total_neto')


def _get_mapping(cells):
    mapping = {}
    for i, cell in enumerate(cells):
        name = _CANONICAL.get(_header_key(cell))
        if name and name not in mapping:
            mapping[name] = i
    return mapping if all(key in mapping for key in _REQUIRED) else None


def _excel_date(value, date1904=False):
    """Return ISO dates for Excel date serials; leave existing text unchanged."""
    if value is None or value == '':
        return value
    try:
        v = float(value)
    except (ValueError, TypeError, OverflowError):
        return value
    if not 1 <= v <= 2958465:
        return value
    try:
        return ((datetime(1904, 1, 1) if date1904 else datetime(1899, 12, 30)) + timedelta(days=v)).date().isoformat()
    except (OverflowError, ValueError):
        return value


def _rows_to_dicts(rows, date1904=False, sheet_label=''):
    """rows yields pairs (1-based Excel row number, list of cell values)."""
    header = None
    first_data = 0
    result = []
    for row_number, cells in rows:
        if not any(str(v).strip() for v in cells if v is not None):
            continue
        if header is None:
            mapping = _get_mapping(cells)
            if mapping:
                header = mapping
                first_data = row_number
            elif row_number >= 35:
                break
            continue
        rec = {field: cells[idx] if idx < len(cells) else '' for field, idx in header.items()}
        for field in ('numero', 'Codproducto', 'CodVendedor', 'Factura', 'id_linea'):
            value = rec.get(field)
            if isinstance(value, float) and value.is_integer():
                rec[field] = str(int(value))
        rec['FechaFactura'] = _excel_date(rec['FechaFactura'], date1904)
        rec['__excel_row'] = row_number
        result.append(rec)
        if len(result) > MAX_ROWS:
            raise SalesExcelError('El Excel supera el máximo de %s líneas.' % MAX_ROWS)
    if header is None:
        return None
    if not result:
        raise SalesExcelError('La hoja %s tiene encabezados, pero no contiene movimientos.' % sheet_label)
    return result


def _column_index(ref):
    letters = re.match(r'^[A-Za-z]+', ref or '')
    if not letters:
        return None
    number = 0
    for ch in letters.group().upper():
        number = number * 26 + ord(ch) - ord('A') + 1
    return number - 1


def _strings(z):
    path = 'xl/sharedStrings.xml'
    if path not in z.namelist():
        return []
    if z.getinfo(path).file_size > MAX_SHARED_STRINGS_BYTES:
        raise SalesExcelError('El catálogo de texto del Excel es demasiado grande.')
    result = []
    with z.open(path) as stream:
        for _, elem in ET.iterparse(stream, events=('end',)):
            if elem.tag == _tag('si'):
                result.append(''.join(n.text or '' for n in elem.iter(_tag('t'))))
                elem.clear()
    return result


def _worksheet_rows(z, path, strings):
    if z.getinfo(path).file_size > MAX_WORKSHEET_BYTES:
        raise SalesExcelError('La hoja del Excel es demasiado grande.')
    with z.open(path) as stream:
        for _, elem in ET.iterparse(stream, events=('end',)):
            if elem.tag != _tag('row'):
                continue
            row_number = int(elem.get('r') or 0)
            cell_values = {}
            for c in elem.findall(_tag('c')):
                col = _column_index(c.get('r'))
                if col is None or col >= MAX_COLUMNS:
                    continue
                cell_type = c.get('t')
                val = c.find(_tag('v'))
                if cell_type == 's' and val is not None:
                    try:
                        value = strings[int(val.text)]
                    except (IndexError, ValueError, TypeError):
                        raise SalesExcelError('El archivo Excel contiene una referencia de texto inválida.')
                elif cell_type == 'inlineStr':
                    value = ''.join(n.text or '' for n in c.iter(_tag('t')))
                elif cell_type == 'e':
                    value = val.text if val is not None and val.text else ''
                else:
                    value = val.text if val is not None and val.text is not None else ''
                cell_values[col] = value
            width = max(cell_values, default=-1) + 1
            values = [''] * width
            for idx, val in cell_values.items():
                values[idx] = val
            yield row_number, values
            elem.clear()


def _get_sheets(z):
    try:
        xml = ET.fromstring(z.read('xl/workbook.xml'))
        relationships = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    except KeyError:
        raise SalesExcelError('El archivo no contiene la estructura completa de un libro XLSX.')
    date1904 = xml.find(_tag('workbookPr'))
    date1904 = date1904 is not None and date1904.get('date1904', '0').lower() in ('1', 'true')
    paths = {}
    for rel in relationships.findall('{%s}Relationship' % _PACKAGE_REL_NS):
        target = rel.get('Target', '')
        if rel.get('TargetMode') == 'External':
            continue
        target = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        if target.startswith('xl/worksheets/') and target in z.namelist():
            paths[rel.get('Id')] = target
    ret = []
    for sheet in xml.findall('.//' + _tag('sheet')):
        path = paths.get(sheet.get('{%s}id' % _REL_NS))
        if path:
            ret.append((sheet.get('name', ''), path))
    return ret, date1904


def _read_xlsx(data, sheet_name=None):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            if 'xl/workbook.xml' not in names:
                raise SalesExcelError('El archivo no es un libro Excel XLSX válido.')
            sheets, date1904 = _get_sheets(z)
            if not sheets:
                raise SalesExcelError('El Excel no contiene hojas utilizables.')
            if sheet_name:
                matches = [(name, path) for name, path in sheets if name.strip().casefold() == sheet_name.strip().casefold()]
                if not matches:
                    raise SalesExcelError('No se encontró la hoja "%s". Hojas: %s' % (sheet_name, ', '.join(name for name, _ in sheets)))
                sheets = matches
            strings = _strings(z)
            for name, path in sheets:
                found = _rows_to_dicts(_worksheet_rows(z, path, strings), date1904=date1904, sheet_label=name)
                if found is not None:
                    return found, name
            raise SalesExcelError('Ninguna hoja tiene las columnas requeridas: %s. Hojas revisadas: %s.' % (', '.join(_REQUIRED), ', '.join(name for name, _ in sheets)))
    except (zipfile.BadZipFile, EOFError) as error:
        raise SalesExcelError('No se puede abrir el XLSX: archivo dañado o formato incorrecto.') from error
    except ET.ParseError as error:
        raise SalesExcelError('El XML interno del archivo XLSX no es válido.') from error


def _read_xls(data, sheet_name=None):
    try:
        import xlrd
    except ImportError:
        raise SalesExcelError('Para cargar archivos .xls antiguos instale xlrd en el entorno Python de Odoo, o guarde el archivo como .xlsx.')
    try:
        book = xlrd.open_workbook(file_contents=data, on_demand=True)
    except Exception as error:
        raise SalesExcelError('No fue posible leer el archivo XLS: %s.' % type(error).__name__) from error
    try:
        names = book.sheet_names()
        if sheet_name:
            names = [name for name in names if name.strip().casefold() == sheet_name.strip().casefold()]
            if not names:
                raise SalesExcelError('No se encontró la hoja "%s" en el XLS.' % sheet_name)
        for name in names:
            sheet = book.sheet_by_name(name)
            def rows():
                for r in range(sheet.nrows):
                    items = []
                    for c in range(min(sheet.ncols, MAX_COLUMNS)):
                        cell = sheet.cell(r, c)
                        if cell.ctype == xlrd.XL_CELL_DATE:
                            try:
                                value = xlrd.xldate_as_datetime(cell.value, book.datemode).date().isoformat()
                            except (ValueError, OverflowError):
                                value = str(cell.value)
                        else:
                            value = cell.value
                        items.append(value)
                    yield r + 1, items
            result = _rows_to_dicts(rows(), date1904=bool(book.datemode), sheet_label=name)
            if result is not None:
                return result, name
        raise SalesExcelError('Ninguna hoja tiene las columnas requeridas: %s.' % ', '.join(_REQUIRED))
    finally:
        book.release_resources()


def load_sales_file(data, filename, sheet_name=None):
    """Return (rows, sheet_name). No filesystem access or network requests."""
    if not isinstance(data, bytes) or not data:
        raise SalesExcelError('Seleccione un archivo Excel para importar.')
    if len(data) > MAX_UPLOAD_BYTES:
        raise SalesExcelError('El archivo supera el tamaño máximo de 30 MB.')
    ext = (filename or '').lower().strip().rsplit('.', 1)
    extension = '.' + ext[-1] if len(ext) == 2 else ''
    if extension == '.xlsx':
        return _read_xlsx(data, sheet_name)
    if extension == '.xls':
        return _read_xls(data, sheet_name)
    raise SalesExcelError('Solo se admiten archivos Excel .xlsx o .xls. No se permiten otros formatos.')
