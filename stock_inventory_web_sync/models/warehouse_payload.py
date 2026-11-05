# -*- coding: utf-8 -*-
"""Reglas puras del contrato JSON y resolución de almacenes. Sin dependencia de Odoo."""
import math


def as_number(value, field_name):
    if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
        raise ValueError('%s vacío; no se convierte implícitamente a cero.' % field_name)
    try:
        number = float(value)
    except (ValueError, TypeError):
        raise ValueError('%s debe ser numérico.' % field_name)
    if not math.isfinite(number):
        raise ValueError('%s debe ser finito.' % field_name)
    return number


def warehouse_code(value):
    """Equivale a comparar stock.warehouse.code y Bodegas[].Bodega sin espacios/minúsculas."""
    return str(value or '').strip().upper()


def resolve_warehouse_ids(candidates, preferred_id=None):
    """{CODIGO: id de stock.warehouse}, advertencias.

    candidates contiene SOLO los almacenes de la empresa de api.administrator.
    preferred_id es api.administrator.warehouse_id.id: sirve como referencia
    y para desambiguar *su propio código*, nunca filtra los demás códigos.
    """
    by_code = {}
    duplicates = {}
    ids = set()
    notices = []
    for warehouse_id, raw_code in candidates:
        ids.add(warehouse_id)
        code = warehouse_code(raw_code)
        if not code:
            notices.append('Almacén ID %s sin código: se omite.' % warehouse_id)
            continue
        if code in by_code:
            duplicates.setdefault(code, [by_code[code]]).append(warehouse_id)
        else:
            by_code[code] = warehouse_id

    if preferred_id and preferred_id not in ids:
        raise ValueError('La bodega asignada en api_administrator no pertenece a la empresa de la API.')
    for code, matches in duplicates.items():
        if preferred_id and preferred_id in matches:
            by_code[code] = preferred_id
            notices.append('Código de bodega %s duplicado: se utiliza la bodega ID %s asignada en API Administrator.'
                           % (code, preferred_id))
        else:
            by_code.pop(code, None)
            notices.append('Código de bodega %s duplicado: no se puede identificar de forma segura.' % code)
    return by_code, notices


def declared_warehouse_codes(item, available_codes):
    """Bodegas realmente mencionadas por el producto (no incluye ceros implícitos)."""
    records = item.get('Bodegas', [])
    if not isinstance(records, list):
        return set()
    return {code for record in records if isinstance(record, dict)
            for code in [warehouse_code(record.get('Bodega'))]
            if code and code in available_codes}


def stock_targets(item, available_codes):
    """Devuelve {COD_BODEGA: cantidad} y advertencias; ningún stock implícito.

    - StockTotal=0: cero para las bodegas de la empresa; preserva regla anterior.
    - StockTotal>0: solo modifica las bodegas indicadas (incluyendo cero).
    - Un código desconocido nunca se redirige a api.administrator.warehouse_id.
    """
    notes = []
    total = as_number(item['StockTotal'], 'StockTotal') if 'StockTotal' in item else None
    if total is not None and total < 0:
        raise ValueError('StockTotal no puede ser negativo.')
    records = item.get('Bodegas', [])
    if not isinstance(records, list):
        raise ValueError('Bodegas debe ser una lista de objetos.')
    targets = {}
    for rec in records:
        if not isinstance(rec, dict):
            notes.append('Se omitió una bodega cuyo registro no es JSON objeto.')
            continue
        code = warehouse_code(rec.get('Bodega'))
        if not code:
            notes.append('Bodega sin código; se omitió.')
            continue
        if code in targets:
            notes.append('Bodega duplicada %s; prevalece el último StockBodega válido recibido.' % code)
        if 'StockBodega' not in rec:
            notes.append('Bodega %s sin StockBodega; se omitió.' % code)
            continue
        try:
            quantity = as_number(rec['StockBodega'], 'StockBodega de %s' % code)
        except ValueError as exc:
            notes.append(str(exc))
            continue
        if quantity < 0:
            notes.append('Bodega %s con stock negativo; se omitió.' % code)
            continue
        targets[code] = quantity

    unknown = [code for code in targets if code not in available_codes]
    for code in unknown:
        notes.append('La bodega %s no existe entre las bodegas de esta empresa.' % code)

    if total is not None and total == 0:
        if any(value for value in targets.values()):
            notes.append('StockTotal=0 contradice StockBodega>0; se aplicó cero por StockTotal.')
        targets = {code: 0.0 for code in available_codes}
    elif total is not None and targets and not math.isclose(sum(targets.values()), total, abs_tol=1e-5):
        notes.append('StockTotal=%s difiere de la suma de Bodegas=%s; se respetó cada StockBodega.'
                     % (total, sum(targets.values())))
    if total is None and not targets:
        notes.append('Sin StockTotal ni bodegas válidas; no se modificaron existencias.')
    if total is not None and total > 0 and not targets:
        notes.append('StockTotal positivo sin Bodegas válidas: no se distribuye stock automáticamente.')
    return targets, notes


def trace_state(created, changed, has_warnings):
    """Resultado visible en el historial de producto después de cerrar el savepoint."""
    if has_warnings:
        return 'warning'
    if created:
        return 'created'
    return 'updated' if changed else 'unchanged'
