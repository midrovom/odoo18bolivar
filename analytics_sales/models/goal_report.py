# -*- coding: utf-8 -*-
"""Cálculo puro de ventas netas y reparto porcentual igualitario por establecimiento.

Los datos provienen de movimientos actuales (FA/DE). Un vendedor se identifica
por su código, o por nombre normalizado cuando no existe código. Una persona
que aparece en varios nlocal se cuenta una sola vez dentro del establecimiento.
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime
import unicodedata

MONTHS_ES = ('Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre')


def money_cents(amount):
    return int((Decimal(str(amount or 0)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def split_cents(total, parts):
    if parts <= 0:
        return []
    sign = -1 if total < 0 else 1
    quotient, remainder = divmod(abs(total), parts)
    return [sign * (quotient + (1 if i < remainder else 0)) for i in range(parts)]


def equal_month_seller_shares(month_cents, sellers):
    """Split each month's target equally, rotating indivisible cents fairly."""
    matrix = [[0] * sellers for _ in month_cents]
    if sellers <= 0:
        return matrix
    allocated = [0] * sellers
    for month, total in enumerate(month_cents):
        sign = -1 if total < 0 else 1
        base, remainder = divmod(abs(total), sellers)
        for seller_index in range(sellers):
            matrix[month][seller_index] = sign * base
            allocated[seller_index] += sign * base
        order = sorted(range(sellers),
                       key=lambda i: (allocated[i], (i - month) % sellers))
        for seller_index in order[:remainder]:
            matrix[month][seller_index] += sign
            allocated[seller_index] += sign
    return matrix


def equal_year_month_shares(annual_cents, sellers):
    """12 months x unique sellers, equal per seller *within each month*.

    The yearly net-sales base is split into 12 monthly quotas. Each monthly
    quota is then shared equally among unique sellers of the establishment;
    when cents cannot divide evenly, the extra cents rotate to the sellers
    with the smallest accumulated amount. Thus each month is fair (<= 1 cent
    difference), yearly totals are fair, and every cent is accounted for.
    """
    matrix = [[0] * sellers for _ in range(12)]
    if sellers <= 0:
        return matrix
    sign = -1 if annual_cents < 0 else 1
    months = split_cents(abs(annual_cents), 12)
    allocated = [0] * sellers
    for month, total in enumerate(months):
        base, remainder = divmod(total, sellers)
        for seller_index in range(sellers):
            matrix[month][seller_index] = base
            allocated[seller_index] += base
        # Do not give all rounding cents to the first seller every month.
        order = sorted(range(sellers),
                       key=lambda i: (allocated[i], (i - month) % sellers))
        for seller_index in order[:remainder]:
            matrix[month][seller_index] += 1
            allocated[seller_index] += 1
    return [[sign * value for value in row] for row in matrix]


def seller_identity(code, name):
    code = str(code or '').strip()
    name = str(name or '').strip()
    return ('code', code.upper()) if code else (('name', name.casefold()) if name else None)


def month_from_read_group(row):
    period = (row.get('__range', {}).get('date:month') or
              row.get('__range', {}).get('date') or {})
    beginning = period.get('from') if isinstance(period, dict) else None
    value = beginning or row.get('date:month') or row.get('date')
    if isinstance(value, (date, datetime)):
        return value.month
    value = str(value or '').strip()
    if len(value) >= 7 and value[:4].isdigit() and value[4] == '-' and value[5:7].isdigit():
        month = int(value[5:7])
        return month if 1 <= month <= 12 else 0
    normalized = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii').lower()
    aliases = (
        ('enero', 'january', 'jan'), ('febrero', 'february', 'feb'),
        ('marzo', 'march', 'mar'), ('abril', 'april', 'apr'),
        ('mayo', 'may'), ('junio', 'june', 'jun'),
        ('julio', 'july', 'jul'), ('agosto', 'august', 'aug'),
        ('septiembre', 'setiembre', 'september', 'sep'),
        ('octubre', 'october', 'oct'), ('noviembre', 'november', 'nov'),
        ('diciembre', 'december', 'dec'),
    )
    for index, names in enumerate(aliases, 1):
        if any(normalized.startswith(n + ' ') or normalized == n for n in names):
            return index
    return 0


def build_monthly_goals(local_names, source_rows, annual_base, monthly_targets=None):
    """Retorna desglose de un establecimiento: año -> mes -> local/vendedor.

    Si se definen metas mensuales, cada mes utiliza su propia meta en lugar
    de dividir la venta anual entre doce. Sin metas manuales mantiene intacto
    el comportamiento histórico. Los vendedores del establecimiento reciben
    cuotas equitativas y cada uno se cuenta una sola vez.
    """
    ids = sorted(local_names, key=lambda k: (str(local_names[k]).casefold(), k))
    if monthly_targets is not None:
        if len(monthly_targets) != 12:
            raise ValueError('Las metas mensuales deben contener exactamente 12 importes.')
        month_shares = [max(0, money_cents(value)) for value in monthly_targets]
        year_cents = sum(month_shares)
    else:
        year_cents = max(0, money_cents(annual_base))
        month_shares = split_cents(year_cents, 12)
    totals = defaultdict(lambda: {'fa': 0., 'de': 0., 'fa_units': 0., 'de_units': 0.})
    seller_totals = defaultdict(lambda: {'fa': 0., 'de': 0., 'fa_units': 0., 'de_units': 0.})
    roster = {}
    for row in source_rows:
        month = int(row.get('month') or 0)
        local_id = row.get('local_id')
        dtype = str(row.get('document_type') or '').upper()
        if month not in range(1, 13) or local_id not in local_names or dtype not in ('FA', 'DE'):
            continue
        code = str(row.get('seller_code') or '').strip()
        name = str(row.get('seller') or '').strip()
        identity = seller_identity(code, name)
        if identity is not None:
            entry = roster.setdefault(identity, {'name': name or code, 'code': code, 'locals': set()})
            if not entry['name'] and name:
                entry['name'] = name
            entry['locals'].add(local_id)
        typ = 'fa' if dtype == 'FA' else 'de'
        value = abs(float(row.get('total_net') or 0.))
        qty = abs(float(row.get('quantity') or 0.))
        totals[(month, local_id)][typ] += value
        totals[(month, local_id)][typ + '_units'] += qty
        seller_totals[(month, local_id, identity)][typ] += value
        seller_totals[(month, local_id, identity)][typ + '_units'] += qty

    keys = sorted(roster, key=lambda k: (roster[k]['name'].casefold(), roster[k]['code'], k))
    allocation_matrix = (equal_month_seller_shares(month_shares, len(keys))
                         if monthly_targets is not None else
                         equal_year_month_shares(year_cents, len(keys)))
    annual_sellers = {k: {'name': roster[k]['name'], 'code': roster[k]['code'],
                          'locals': sorted(roster[k]['locals']), 'goal_cents': 0,
                          'fa': 0., 'de': 0., 'net': 0.,
                          'percentage': 100. / len(keys)} for k in keys}
    result = []
    total_unassigned = 0
    for month in range(1, 13):
        monthly_goal = month_shares[month - 1]
        shares = allocation_matrix[month - 1]
        allocations = defaultdict(int)
        est_sellers = []
        for key, share in zip(keys, shares):
            info = roster[key]
            local_keys = sorted(info['locals'], key=lambda k: (local_names[k].casefold(), k))
            for local_id, part in zip(local_keys, split_cents(share, len(local_keys))):
                allocations[(local_id, key)] += part
            fa = sum(seller_totals[(month, local_id, key)]['fa'] for local_id in local_keys)
            de = sum(seller_totals[(month, local_id, key)]['de'] for local_id in local_keys)
            est_sellers.append({'name': info['name'], 'code': info['code'],
                                'locals': [local_names[k] for k in local_keys],
                                'fa': fa, 'de': de, 'net': fa - de,
                                'fa_units': sum(seller_totals[(month, k, key)]['fa_units'] for k in local_keys),
                                'de_units': sum(seller_totals[(month, k, key)]['de_units'] for k in local_keys),
                                'percentage': 100. / len(keys), 'goal_cents': share})
            annual_sellers[key]['goal_cents'] += share
            annual_sellers[key]['fa'] += fa
            annual_sellers[key]['de'] += de
            annual_sellers[key]['net'] += fa - de
        local_details = []
        total_fa = total_de = 0.
        for local_id in ids:
            base = totals[(month, local_id)]
            row_sellers = []
            local_goal = 0
            for key in keys:
                if local_id not in roster[key]['locals']:
                    continue
                goal = allocations[(local_id, key)]
                local_goal += goal
                sale = seller_totals[(month, local_id, key)]
                row_sellers.append({'name': roster[key]['name'], 'code': roster[key]['code'],
                                    'fa': sale['fa'], 'de': sale['de'],
                                    'net': sale['fa'] - sale['de'],
                                    'fa_units': sale['fa_units'], 'de_units': sale['de_units'],
                                    'goal_cents': goal,
                                    'percentage': 100. / len(keys), 'unassigned': False})
            no_seller = seller_totals.get((month, local_id, None))
            if no_seller is not None:
                row_sellers.append({'name': 'Sin vendedor registrado', 'code': '',
                                    'fa': no_seller['fa'], 'de': no_seller['de'],
                                    'net': no_seller['fa'] - no_seller['de'],
                                    'fa_units': no_seller['fa_units'], 'de_units': no_seller['de_units'],
                                    'goal_cents': 0, 'percentage': 0., 'unassigned': True})
            total_fa += base['fa']
            total_de += base['de']
            local_details.append({'local_id': local_id, 'name': local_names[local_id],
                                  'fa': base['fa'], 'de': base['de'], 'net': base['fa'] - base['de'],
                                  'fa_units': base['fa_units'], 'de_units': base['de_units'],
                                  'goal_cents': local_goal, 'unassigned_cents': 0,
                                  'sellers': row_sellers})
        unknown_fa = sum(seller_totals[(month, k, None)]['fa'] for k in ids)
        unknown_de = sum(seller_totals[(month, k, None)]['de'] for k in ids)
        if unknown_fa or unknown_de:
            est_sellers.append({'name': 'Sin vendedor registrado', 'code': '',
                                'locals': [], 'fa': unknown_fa, 'de': unknown_de,
                                'net': unknown_fa - unknown_de,
                                'percentage': 0., 'goal_cents': 0, 'unassigned': True})
        month_unassigned = monthly_goal if not keys else 0
        total_unassigned += month_unassigned
        result.append({'month': month, 'name': MONTHS_ES[month - 1],
                       'fa': total_fa, 'de': total_de, 'net': total_fa - total_de,
                       'goal_cents': monthly_goal, 'unassigned_cents': month_unassigned,
                       'locals': local_details, 'sellers': est_sellers})
    return {'months': result, 'annual_goal_cents': year_cents,
            'annual_sellers': [annual_sellers[k] for k in keys],
            'seller_count': len(keys),
            'unassigned_cents': total_unassigned,
            'assigned_cents': year_cents - total_unassigned}
