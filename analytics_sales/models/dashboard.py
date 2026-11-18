# -*- coding: utf-8 -*-
from collections import defaultdict
from datetime import date, timedelta
from calendar import monthrange
from odoo import api, fields, models, _
from .goal_report import seller_identity, split_cents, money_cents, equal_month_seller_shares
from odoo.exceptions import AccessError, ValidationError

FASHION_LINES = {'CALZADO', 'CARTERAS', 'MODA MUJER'}


def _previous_calendar_month(today):
    """Mes calendario anterior completo, incluso en un cambio de año."""
    last = today.replace(day=1) - timedelta(days=1)
    return last.replace(day=1), last


def _numbers():
    return {'fa_units': 0.0, 'de_units': 0.0, 'fa_sales': 0.0,
            'de_sales': 0.0, 'fa_cost': 0.0, 'de_cost': 0.0,
            'fa_docs': set(), 'de_docs': set(), 'active_days': set(),
            'lines': 0, 'missing_cost': 0}


def _feed(bucket, row, include_cost):
    fa = row['document_type'] == 'FA'
    amount = row['total_net'] or 0.0
    quantity = row['quantity'] or 0.0
    dockey = '%s|%s|%s' % (row['local_id'][0], row['document_type'], row['document_number'])
    bucket['lines'] += 1
    if fa:
        bucket['fa_units'] += quantity
        bucket['fa_sales'] += amount
        bucket['fa_docs'].add(dockey)
        bucket['active_days'].add(str(row['date']))
    else:
        bucket['de_units'] += quantity
        bucket['de_sales'] += amount
        bucket['de_docs'].add(dockey)
    if include_cost:
        if not row['cost_known']:
            bucket['missing_cost'] += 1
        if fa:
            bucket['fa_cost'] += row['total_cost'] or 0.0
        else:
            bucket['de_cost'] += row['total_cost'] or 0.0


def _pack(bucket, cost_allowed=False):
    fa_invoices = len(bucket['fa_docs'])
    fa_sales, de_sales = bucket['fa_sales'], bucket['de_sales']
    net_sales = fa_sales - de_sales
    d = {
        'fa_units': round(bucket['fa_units'], 3),
        'de_units': round(bucket['de_units'], 3),
        'units': round(bucket['fa_units'] - bucket['de_units'], 3),
        'fa_sales': round(fa_sales, 2), 'de_sales': round(de_sales, 2),
        'sales': round(net_sales, 2),
        'invoices': fa_invoices, 'credit_notes': len(bucket['de_docs']),
        'ticket': round(fa_sales / fa_invoices, 2) if fa_invoices else 0,
        'units_per_invoice': round(bucket['fa_units'] / fa_invoices, 2) if fa_invoices else 0,
        'return_rate': round(de_sales / fa_sales * 100, 2) if fa_sales else 0,
        'units_return_rate': round(bucket['de_units'] / bucket['fa_units'] * 100, 2) if bucket['fa_units'] else 0,
        'active_days': len(bucket['active_days']),
        'invoices_per_active_day': round(fa_invoices / len(bucket['active_days']), 2) if bucket['active_days'] else 0,
        'lines': bucket['lines'],
    }
    if cost_allowed:
        known = bucket['missing_cost'] == 0
        cost = bucket['fa_cost'] - bucket['de_cost']
        profit = net_sales - cost
        d.update({
            'cost_complete': known,
            'cost': round(cost, 2) if known else None,
            'profit': round(profit, 2) if known else None,
            'margin': round(profit / net_sales * 100, 2) if known and net_sales else None,
            'missing_cost_lines': bucket['missing_cost'],
        })
    return d


def _classify_abc(rows):
    """Misma regla ABC histórica aplicada a grupos ya ordenados por venta neta."""
    positive = [row for row in rows if row['sales'] > 0]
    cumulative, positive_total = 0.0, sum(row['sales'] for row in positive)
    for row in rows:
        row['abc'] = 'SIN VENTA'
    for row in positive:
        pct = cumulative / positive_total if positive_total else 1.0
        row['abc'] = 'A' if pct < 0.80 else 'B' if pct < 0.95 else 'C'
        cumulative += row['sales']


def _pack_establishment_comparison(rows, establishments, locals_allowed, include_cost=False):
    """Agrega los nlocal autorizados en una sola fila por establecimiento.

    `rows` ya está limitado a compañía, permisos, fechas y filtros comerciales.
    Cada local pertenece a un único establecimiento, por lo que ninguna
    factura puede aparecer dos veces. Los locales sin establecimiento se
    consolidan en una única fila no individualizada cuando se consulta 'Todos'.
    """
    permitted = set(locals_allowed.ids)
    local_to_establishment = {}
    buckets = {}
    names = {}
    for est in establishments:
        included = permitted.intersection(est.local_ids.ids)
        if not included:
            continue
        buckets[est.id] = _numbers()
        names[est.id] = est.name
        for local_id in included:
            local_to_establishment[local_id] = est.id

    unassigned = permitted.difference(local_to_establishment)
    if unassigned:
        buckets[None] = _numbers()
        names[None] = 'Sin establecimiento'

    for row in rows:
        local = row.get('local_id')
        local_id = local[0] if local else None
        if local_id not in permitted:
            continue
        est_id = local_to_establishment.get(local_id)
        if est_id in buckets:
            _feed(buckets[est_id], row, include_cost)

    result = [dict(name=names[est_id], establishment_id=est_id or False,
                   **_pack(bucket, include_cost))
              for est_id, bucket in buckets.items()]
    result.sort(key=lambda item: (-item['sales'], item['name']))
    return result


def _daily_history(rows, start, history_days=15):
    """Real FA-DE daily net sales only, within the already authorized filters.

    Never manufacture a future sale or extrapolate. Calendar days without
    movements are included with zero for an honest chronological history.
    The latest recorded date anchors the requested (1..90) historical days.
    """
    days = max(1, min(90, int(history_days)))
    if not rows:
        return {'history': [], 'history_days': days, 'net_total': 0.0,
                'daily_average': 0.0, 'last_actual_day': False}
    last = max(date.fromisoformat(str(row['date'])[:10]) for row in rows)
    by_date = defaultdict(float)
    for row in rows:
        dt = date.fromisoformat(str(row['date'])[:10])
        sign = 1 if row['document_type'] == 'FA' else -1
        by_date[dt] += sign * (row['total_net'] or 0.0)
    available_days = max(1, (last - start).days + 1)
    count = min(days, available_days)
    history = [{'date': (last - timedelta(days=i)).isoformat(),
                'sales': round(by_date[last - timedelta(days=i)], 2)}
               for i in reversed(range(count))]
    total = sum(by_date[last - timedelta(days=i)] for i in range(count))
    return {'history': history, 'history_days': days,
            'net_total': round(total, 2),
            'daily_average': round(total / count, 2),
            'last_actual_day': last.isoformat()}




def _iter_month_segments(start, end):
    current = date(start.year, start.month, 1)
    while current <= end:
        days_in_month = monthrange(current.year, current.month)[1]
        month_start = current
        month_end = date(current.year, current.month, days_in_month)
        overlap_start = max(start, month_start)
        overlap_end = min(end, month_end)
        if overlap_start <= overlap_end:
            overlap_days = (overlap_end - overlap_start).days + 1
            yield {
                'year': current.year,
                'month': current.month,
                'days_in_month': days_in_month,
                'overlap_days': overlap_days,
            }
        current = date(current.year + (1 if current.month == 12 else 0),
                       1 if current.month == 12 else current.month + 1, 1)


def _signed_sales_amount(rows):
    total = 0.0
    for row in rows:
        total += (row.get('total_net') or 0.0) * (1 if row.get('document_type') == 'FA' else -1)
    return round(total, 2)


def _goal_target_from_record(goal, month):
    line = goal.monthly_line_ids.filtered(lambda l: l.month == '%02d' % month)[:1]
    return line.target_amount if line else 0.0


def _goal_cents_for_segment(monthly_target, segment, period):
    """Use the configured MONTHLY goal, not days elapsed, for month/year filters.

    Month: use the whole configured target even when today's date is the 16th.
    Previous month: use the entire configured target.
    Year: use entire monthly targets, including future months within that year.
    Rolling/custom date ranges retain the previous proportional behavior.
    """
    if period in ('month', 'previous_month', 'year'):
        return money_cents(monthly_target or 0.0)
    return money_cents((monthly_target or 0.0) * segment['overlap_days'] / segment['days_in_month'])

def _goal_compliance(actual, target):
    """Porcentaje visible solo si existe una meta monetaria positiva."""
    return round(actual / target * 100, 2) if target > 0 else None


def _goal_period_segments(from_date, to_date, period):
    start, end = date.fromisoformat(from_date), date.fromisoformat(to_date)
    if period == 'year':
        # Coincide con el cálculo de la sección Cumplimiento de metas.
        start, end = date(start.year, 1, 1), date(start.year, 12, 31)
    return list(_iter_month_segments(start, end))


def _merge_goal_sellers(entries):
    """One row per seller across the authorized establishment summaries.

    Add the already allocated quotas, never redistribute the monthly goal.
    The inputs contain only authorized sellers and their filtered net sales.
    """
    merged = {}
    for entry in entries:
        for seller in entry.get('sellers', []):
            identity = seller_identity(seller.get('code'), seller.get('name'))
            if identity is None:
                continue
            row = merged.setdefault(identity, {
                'name': seller['name'], 'code': seller.get('code') or '',
                'target_cents': 0, 'actual_cents': 0,
            })
            row['target_cents'] += money_cents(seller.get('target'))
            row['actual_cents'] += money_cents(seller.get('actual'))
    rows = []
    for row in merged.values():
        target = row.pop('target_cents') / 100.0
        actual = row.pop('actual_cents') / 100.0
        rows.append(dict(row, target=target, actual=actual,
                         difference=round(actual - target, 2),
                         compliance=round(actual / target * 100, 2) if target > 0 else 0.0))
    return sorted(rows, key=lambda row: (-row['actual'], row['name'].casefold(), row['code']))


class AnalyticsSalesDashboard(models.AbstractModel):
    _name = 'analytics.sales.dashboard'
    _description = 'Servicio seguro de inteligencia comercial Analytics Sales'

    @api.model
    def get_dashboard(self, filters=None):
        """Single RPC boundary. Only aggregates cross the wire; no raw costs for sales roles."""
        filters = filters if isinstance(filters, dict) else {}
        role, local_scope = self.env['analytics.sales.security'].get_role_and_scope()
        try:
            history_days = int(filters.get('history_days', 15))
        except (TypeError, ValueError):
            raise ValidationError(_('La cantidad de días históricos debe ser numérica.'))
        if not 1 <= history_days <= 90:
            raise ValidationError(_('Seleccione entre 1 y 90 días de historial.'))
        company = self.env.company
        admin = role == 'administrador'
        local_model = self.env['analytics.sales.local'].sudo()
        allowed_domain = [('company_id', '=', company.id)]
        if local_scope is not None:
            allowed_domain.append(('id', 'in', local_scope))
        locals_allowed = local_model.search(allowed_domain, order='name')
        allowed_ids = set(locals_allowed.ids)
        establishment_model = self.env['analytics.sales.establishment'].sudo()
        established = establishment_model.search([
            ('company_id', '=', company.id), ('local_ids', 'in', list(allowed_ids)),
        ], order='name') if allowed_ids else establishment_model.browse()
        if admin:
            # El inventario se relaciona directamente con establecimientos, incluso sin nlocal.
            warehouse_establishments = self.env['analytics.sales.warehouse'].sudo().search([
                ('company_id', '=', company.id), ('establishment_id', '!=', False),
            ]).mapped('establishment_id').filtered(lambda est: est.active and est.company_id == company)
            established = (established | warehouse_establishments).sorted(key=lambda est: (est.name or '').casefold())
        establishment_raw = filters.get('establishment_id') or False
        selected_establishment = False
        establishment_ids = set(established.ids)
        if establishment_raw and str(establishment_raw).strip().lower() != 'all':
            try:
                selected_establishment = int(establishment_raw)
            except (TypeError, ValueError):
                raise ValidationError(_('Establecimiento inválido.'))
            if selected_establishment not in establishment_ids:
                raise AccessError(_('No tiene permiso para consultar ese establecimiento.'))
            establishment = established.filtered(lambda rec: rec.id == selected_establishment)[:1]
            allowed_ids &= set(establishment.local_ids.ids)
        local_raw = filters.get('local_id') or False
        selected_local = False
        if local_raw and str(local_raw).strip().lower() != 'all':
            try:
                selected_local = int(local_raw)
            except (TypeError, ValueError):
                raise ValidationError(_('Local inválido.'))
            if selected_local not in allowed_ids:
                raise AccessError(_('No tiene permiso para consultar ese nlocal.'))
        scope = (filters.get('scope') or 'moda').lower()
        if scope not in ('moda', 'all'):
            raise ValidationError(_('Ámbito inválido.'))
        source_domain = [('company_id', '=', company.id), ('source_kind', '=', 'api')]
        move_model = self.env['analytics.sales.move'].sudo()
        source = 'api' if move_model.with_context(active_test=False).search_count(source_domain) else 'historico'
        base_domain = [('company_id', '=', company.id), ('source_kind', '=', source),
                       ('document_type', 'in', ['FA', 'DE'])]
        if local_scope is not None or selected_establishment:
            base_domain.append(('local_id', 'in', list(allowed_ids)))
        filtered_locals = locals_allowed.filtered(lambda local: local.id in allowed_ids)
        if role == 'tienda':
            # Un perfil Tienda consulta exactamente un nlocal a la vez.
            # 'all' nunca significa agregar resultados de varios locales.
            if not allowed_ids:
                raise AccessError(_('No tiene locales nlocal autorizados.'))
            if not selected_local:
                selected_local = filtered_locals[0].id
        # Cuando se seleccionan establecimiento + local, el comparativo muestra
        # ÚNICAMENTE ese local. Si se selecciona solo un establecimiento, sigue
        # sumando todos sus nlocal autorizados sin desglosarlos.
        show_selected_local = bool(selected_establishment and selected_local)
        comparison_domain = list(base_domain)
        if selected_local:
            base_domain.append(('local_id', '=', selected_local))
            if role == 'tienda':
                comparison_domain.append(('local_id', '=', selected_local))
        if scope == 'moda':
            fashion_filter = ('line_name', 'in', list(FASHION_LINES))
            base_domain.append(fashion_filter)
            comparison_domain.append(fashion_filter)
        first_rec = move_model.search(base_domain, order='date asc,id asc', limit=1)
        last_rec = move_model.search(base_domain, order='date desc,id desc', limit=1)
        first = first_rec.date if first_rec else False
        last = last_rec.date if last_rec else False
        # Los periodos 30/90/Año son MOVILES, anclados al último día disponible.
        # Los valores manuales tienen prioridad y permanecen fijos.
        period = str(filters.get('period') or 'custom').lower()
        if period == 'month':
            # Mes calendario del usuario, aunque todavía no existan ventas.
            today = fields.Date.context_today(self)
            from_date, to_date = today.replace(day=1).isoformat(), today.isoformat()
        elif period == 'previous_month':
            # Mes calendario anterior completo en la zona horaria del usuario.
            first_previous, last_previous = _previous_calendar_month(fields.Date.context_today(self))
            from_date, to_date = first_previous.isoformat(), last_previous.isoformat()
        elif period in ('30', '90', 'year') and last:
            end_date = last
            if period == 'year':
                start_date = end_date.replace(month=1, day=1)
            else:
                start_date = end_date - timedelta(days=int(period) - 1)
            from_date, to_date = start_date.isoformat(), end_date.isoformat()
        else:
            from_date = str(filters.get('date_from') or (str(first) if first else date.today().replace(month=1, day=1)))[:10]
            to_date = str(filters.get('date_to') or (str(last) if last else date.today()))[:10]
        try:
            start = date.fromisoformat(from_date)
            end = date.fromisoformat(to_date)
        except ValueError:
            raise ValidationError(_('Fechas inválidas; utilice YYYY-MM-DD.'))
        if start > end or (end - start).days > 3650:
            raise ValidationError(_('El rango de fechas no es válido o supera diez años.'))
        date_filters = [('date', '>=', from_date), ('date', '<=', to_date)]
        base_domain += date_filters
        # El gráfico de establecimientos dispone de su PROPIO período móvil:
        # se ancla al último movimiento del establecimiento completo, no al
        # último movimiento del nlocal elegido. El resto del dashboard conserva
        # exactamente el rango previamente calculado para ese nlocal.
        comparison_from, comparison_to = from_date, to_date
        if role != 'tienda' and selected_local and not show_selected_local and period in ('30', '90', 'year'):
            comparison_last = move_model.search(
                comparison_domain, order='date desc,id desc', limit=1)
            if comparison_last:
                comparison_end = comparison_last.date
                comparison_start = (comparison_end.replace(month=1, day=1)
                                    if period == 'year' else
                                    comparison_end - timedelta(days=int(period) - 1))
                comparison_from = comparison_start.isoformat()
                comparison_to = comparison_end.isoformat()
        comparison_domain += [ ('date', '>=', comparison_from),
                               ('date', '<=', comparison_to) ]
        data_fields = ['document_type', 'document_number', 'date', 'local_id',
                       'seller', 'seller_code', 'line_name', 'brand', 'sku', 'product_name', 'modelo',
                       'quantity', 'total_net']
        if admin:
            data_fields += ['total_cost', 'cost_known']
        rows_base = move_model.search_read(base_domain, data_fields, order='date,id')
        # Solo cuando el usuario filtra un nlocal necesitamos otra consulta.
        # Para Tienda NO ampliamos nada: su gráfico sigue siendo por vendedor.
        rows_comparison = (move_model.search_read(comparison_domain, data_fields, order='date,id')
                           if selected_local and not show_selected_local else None)
        # Filter choices are scoped to caller's allowed locales and date range.
        opts = {
            'locals': [{'id': loc.id, 'name': loc.name} for loc in locals_allowed],
            'establishments': [{'id': rec.id, 'name': rec.name,
                                'local_ids': list(set(rec.local_ids.ids) & set(locals_allowed.ids))}
                               for rec in established],
            'lines': sorted({r['line_name'] or 'SIN LÍNEA' for r in rows_base}),
            'brands': sorted({r['brand'] or 'SIN MARCA' for r in rows_base}),
            'sellers': sorted({r['seller'] or 'NO IDENTIFICADO' for r in rows_base}),
        }
        for field_name, db_field in (('line', 'line_name'), ('brand', 'brand'), ('seller', 'seller')):
            selection = filters.get(field_name)
            if selection and selection != 'all':
                unknown = {'line': 'SIN LÍNEA', 'brand': 'SIN MARCA',
                           'seller': 'NO IDENTIFICADO'}[field_name]
                rows_base = [row for row in rows_base if (row[db_field] or unknown) == selection]
                if rows_comparison is not None:
                    rows_comparison = [row for row in rows_comparison
                                       if (row[db_field] or unknown) == selection]
        # El caso combinado presenta una sola fila con los datos del nlocal
        # seleccionado, dentro del período de los indicadores generales.
        # Se utiliza rows_base, que ya pasó todos los filtros y controles de acceso.
        if show_selected_local:
            selected_record = filtered_locals.filtered(lambda loc: loc.id == selected_local)[:1]
            local_totals = _numbers()
            for sale_row in rows_base:
                _feed(local_totals, sale_row, admin)
            establishment_comparison = ([dict(name=selected_record.name,
                                              establishment_id=selected_establishment,
                                              **_pack(local_totals, admin))]
                                        if selected_record else [])
        else:
            # Al escoger solo el establecimiento se conserva el comparativo
            # agrupado, incluso para locales sin ventas del período.
            comparison_locals = (filtered_locals.filtered(lambda loc: loc.id == selected_local)
                                 if role == 'tienda' else filtered_locals)
            comparison_establishments = established.filtered(
                lambda est: bool(set(est.local_ids.ids) & set(comparison_locals.ids)))
            establishment_comparison = _pack_establishment_comparison(
                rows_comparison if rows_comparison is not None else rows_base,
                comparison_establishments, comparison_locals, admin)
        # Cumplimiento en el comparativo: siempre usa la meta mensual del
        # establecimiento correspondiente. Con un local elegido, la venta del
        # local es su aporte a la meta GLOBAL, no una meta inventada por local.
        self._add_comparison_goal_compliance(
            establishment_comparison, company, from_date, to_date, period)
        goal_summary = self._comparison_goal_card(establishment_comparison, show_selected_local)
        total = _numbers()
        dimensions = {'stores': {}, 'lines': {}, 'brands': {}, 'sellers': {}, 'products': {}, 'models': {}}
        product_labels = {}
        trend = defaultdict(_numbers)
        for row in rows_base:
            _feed(total, row, admin)
            dimensions_keys = {
                'stores': str(row['local_id'][1]),
                'lines': row['line_name'] or 'SIN LÍNEA',
                'brands': row['brand'] or 'SIN MARCA',
                'sellers': row['seller'] or 'NO IDENTIFICADO',
                'products': (row['sku'] or 'SIN SKU'),
                'models': str(row.get('modelo') or '').strip() or 'Sin modelo',
            }
            product_labels.setdefault(dimensions_keys['products'], row['product_name'] or 'SIN DESCRIPCIÓN')
            for dim, label in dimensions_keys.items():
                if label not in dimensions[dim]:
                    dimensions[dim][label] = _numbers()
                _feed(dimensions[dim][label], row, admin)
            dt = str(row['date'])[:7]
            _feed(trend[dt], row, admin)
        packed = {key: [{'name': name, **_pack(bucket, admin)} for name, bucket in items.items()]
                  for key, items in dimensions.items()}
        for product in packed['products']:
            sku = product['name']
            product['sku'] = sku
            product['name'] = sku + ' · ' + product_labels.get(sku, sku)
        for values in packed.values():
            values.sort(key=lambda item: (-item['sales'], item['name']))
        # ABC measures sales contribution. Velocity measures commercial demand, not stock turns.
        day_count = max(1, (end - start).days + 1)
        for p in packed['products']:
            p['velocity'] = round(p['units'] / day_count, 3)
        # ABC por modelo, sin cambiar la velocidad ni el ranking original por SKU.
        for dimension in ('products', 'models'):
            _classify_abc(packed[dimension])
        totals = _pack(total, admin)
        months = [{'month': month, **_pack(bucket, admin)} for month, bucket in sorted(trend.items())]
        max_sales = max((max(t['fa_sales'], t['de_sales']) for t in months), default=0.0) or 1
        for t in months:
            t['fa_height'] = max(1, round(t['fa_sales'] / max_sales * 100)) if t['fa_sales'] else 0
            t['de_height'] = max(1, round(t['de_sales'] / max_sales * 100)) if t['de_sales'] else 0
        insights = self._insights(packed, totals, admin)
        daily = _daily_history(rows_base, start, history_days)
        # Una sola marca de tiempo por compañía; nunca exponer credenciales
        # ni movimientos crudos, tampoco a perfiles Tienda/Supervisor.
        latest_sync = self.env['analytics.sales.sync.log'].sudo().search([
            ('company_id', '=', company.id), ('origin', '=', 'api'),
            ('state', '=', 'ok'), '|', ('api_kind', '=', False), ('api_kind', 'in', ['annual', 'monthly']),
        ], order='ended_at desc, id desc', limit=1)
        api_synced_at = fields.Datetime.to_string(latest_sync.ended_at) if latest_sync else False
        # La venta real de Metas debe partir EXACTAMENTE de las mismas líneas
        # autorizadas y filtradas usadas para la tarjeta principal Venta neta.
        # Las cuotas mensuales guardadas se consultan aparte y no se alteran.
        goal_dashboard = self._goal_dashboard(
            company, source, established, selected_establishment, allowed_ids,
            from_date, to_date, role, period,
            filtered_rows=rows_base, selected_local=selected_local,
            selected_seller=filters.get('seller'))
        return {
            'role': role, 'company': company.name, 'source': source,
            'api_synced_at': api_synced_at,
            # Marca de la consulta real, independiente de la última sincronización API.
            'dashboard_read_at': fields.Datetime.to_string(fields.Datetime.now()),
            'selected_local_id': selected_local or False,
            'selected_establishment_id': selected_establishment or False,
            'scope': scope, 'options': opts, 'date_min': str(first) if first else None,
            'date_max': str(last) if last else None, 'date_from': from_date,
            'date_to': to_date, 'metrics': totals, 'rankings': packed,
            'establishment_comparison': establishment_comparison,
            'goal_compliance_card': goal_summary,
            'trend': months, 'daily_history': daily, 'insights': insights,
            'goal_dashboard': goal_dashboard,
            'warehouse_dashboard': (self.env['analytics.sales.warehouse']._dashboard_warehouses(
                company, selected_establishment) if admin else False),
            'rows_filtered': len(rows_base),
            'limitations': _('Velocidad comercial = unidades netas por día calendario. Para rotación de inventario y cobertura se necesitan existencias y stock promedio.'),
        }

    @api.model
    def _add_comparison_goal_compliance(self, rows, company, from_date, to_date, period):
        """Anota solo agregados de metas para los establecimientos ya autorizados.

        Nunca amplía los locales ni las ventas de la comparación existente.
        Reutiliza el cálculo mensual de la ficha Metas: mes completo para
        Mes actual/anterior, doce cuotas para Año y prorrata en rangos parciales.
        """
        ids = list({row.get('establishment_id') for row in rows
                    if row.get('establishment_id')})
        segments = _goal_period_segments(from_date, to_date, period)
        years = list({segment['year'] for segment in segments})
        goal_by_est_year = {}
        if ids and years:
            goals = self.env['analytics.sales.goal'].sudo().search([
                ('company_id', '=', company.id),
                ('establishment_id', 'in', ids),
                ('year', 'in', years),
                ('active', '=', True),
            ], order='year,id desc')
            for goal in goals:
                goal_by_est_year.setdefault((goal.establishment_id.id, goal.year), goal)
        for row in rows:
            est_id = row.get('establishment_id')
            cents = 0
            for seg in segments:
                goal = goal_by_est_year.get((est_id, seg['year'])) if est_id else None
                if goal:
                    cents += _goal_cents_for_segment(
                        _goal_target_from_record(goal, seg['month']), seg, period)
            target = round(cents / 100.0, 2)
            row['goal_target'] = target
            row['goal_compliance'] = _goal_compliance(row['sales'], target)

    @api.model
    def _comparison_goal_card(self, rows, show_selected_local):
        if not rows:
            return {'available': False, 'label': 'Cumplimiento de meta',
                    'detail': 'Sin establecimientos autorizados'}
        candidates = [row for row in rows if row.get('goal_target', 0) > 0]
        if not candidates:
            return {'available': False, 'label': 'Cumplimiento de meta',
                    'detail': 'Sin meta asignada para este período'}
        target = round(sum(row['goal_target'] for row in candidates), 2)
        actual = round(sum(row['sales'] for row in candidates), 2)
        if show_selected_local:
            label = 'Aporte a meta del establecimiento'
            detail = 'Venta neta del local / meta completa del establecimiento'
        else:
            label = 'Cumplimiento de meta'
            detail = ('Venta neta / meta del período' if len(rows) == 1
                      else 'Solo establecimientos con metas asignadas')
        return {'available': True, 'label': label, 'value': _goal_compliance(actual, target),
                'target': target, 'actual': actual, 'detail': detail}

    @api.model
    def _goal_dashboard(self, company, source, establishments, selected_establishment, allowed_ids,
                        from_date, to_date, role, period='custom', filtered_rows=None,
                        selected_local=False, selected_seller=None):
        """Metas por vendedor, con un único listado en la vista general.

        Conserva el reparto mensual configurado, pero el importe de Venta real
        proviene del mismo conjunto filtrado usado por la tarjeta Venta neta.
        Nunca incorpora locales no autorizados.
        """
        if selected_establishment:
            result = self._goal_dashboard_one(
                company, source, establishments, selected_establishment, allowed_ids,
                from_date, to_date, role, period,
                filtered_rows=filtered_rows, selected_seller=selected_seller)
            if result.get('available'):
                result['all_establishments'] = False
                result['establishments'] = [dict(result, establishment_id=selected_establishment,
                                                 establishments=[])]
            return result

        entries = []
        assigned_ids = set()
        # Si se consulta un local concreto bajo "Todos los establecimientos",
        # las ventas ya están filtradas a ese nlocal. No debemos agregar las
        # metas de establecimientos ajenos al local seleccionado.
        permitted_ids = (set(allowed_ids) & {selected_local}
                         if selected_local else set(allowed_ids))
        for est in establishments.sorted(key=lambda item: (item.name or '').casefold()):
            associated = set(est.local_ids.ids) & permitted_ids
            if not associated:
                continue
            assigned_ids.update(associated)
            row = self._goal_dashboard_one(
                company, source, establishments, est.id, allowed_ids,
                from_date, to_date, role, period,
                filtered_rows=filtered_rows, selected_seller=selected_seller)
            if row.get('available'):
                entries.append(dict(row, establishment_id=est.id))

        # Vista general: los locales autorizados que no pertenecen a ningún
        # establecimiento también deben contarse, igual que en Ventas netas
        # por establecimientos. Nunca crear una meta ficticia para ellos.
        unassigned_ids = sorted(permitted_ids - assigned_ids)
        if unassigned_ids:
            row = self._goal_dashboard_one(
                company, source, establishments, False, allowed_ids,
                from_date, to_date, role, period,
                unassigned_local_ids=unassigned_ids,
                filtered_rows=filtered_rows, selected_seller=selected_seller)
            if row.get('available'):
                entries.append(dict(row, establishment_id='unassigned'))
        if not entries:
            return {'available': False,
                    'message': _('No hay locales autorizados para consultar.')}
        target = round(sum(row['target'] for row in entries), 2)
        actual = round(sum(row['actual'] for row in entries), 2)
        sellers = _merge_goal_sellers(entries)
        return {
            'available': True,
            'all_establishments': True,
            'establishment_name': _('Todos los establecimientos'),
            'period_label': '%s → %s' % (from_date, to_date),
            'target': target,
            'actual': actual,
            'difference': round(actual - target, 2),
            'compliance': round(actual / target * 100, 2) if target else 0.0,
            'establishment_count': len(entries),
            'seller_count': len(sellers),
            'sellers': sellers,
            'establishments': entries,
            'note': _('Vendedores de los locales autorizados, incluidos los locales sin establecimiento. La barra representa el avance de cada vendedor respecto a su meta asignada.'),
        }

    @api.model
    def _goal_dashboard_one(self, company, source, establishments, selected_establishment, allowed_ids,
                            from_date, to_date, role, period='custom', unassigned_local_ids=None,
                            filtered_rows=None, selected_seller=None):
        # Solo el resumen general puede solicitar la agrupación virtual
        # "Sin establecimiento"; la lista se limita siempre a locales
        # permitidos y no tiene objetivo mensual propio.
        unassigned = unassigned_local_ids is not None
        if unassigned:
            local_ids = sorted(set(unassigned_local_ids) & set(allowed_ids))
            establishment_name = _('Sin establecimiento')
        else:
            if not selected_establishment:
                return {
                    'available': False,
                    'message': _('Seleccione un establecimiento para comparar la meta definida frente a la venta real.'),
                }
            establishment = establishments.filtered(lambda rec: rec.id == selected_establishment)[:1]
            if not establishment:
                return {'available': False, 'message': _('Establecimiento no disponible para este usuario.')}
            local_ids = [lid for lid in establishment.local_ids.ids if lid in set(allowed_ids)]
            establishment_name = establishment.name
        if not local_ids:
            return {'available': False, 'message': _('No hay locales autorizados para este grupo.')}
        start = date.fromisoformat(from_date)
        end = date.fromisoformat(to_date)
        move_model = self.env['analytics.sales.move'].sudo()
        period_domain = [
            ('company_id', '=', company.id), ('source_kind', '=', source),
            ('document_type', 'in', ['FA', 'DE']), ('local_id', 'in', local_ids),
            ('date', '>=', from_date), ('date', '<=', to_date),
        ]
        data_fields = ['document_type', 'date', 'seller', 'seller_code', 'total_net']
        if filtered_rows is None:
            # Compatibilidad con los métodos internos y tests existentes.
            rows_period = move_model.search_read(period_domain, data_fields, order='date,id')
        else:
            # Misma fuente y MISMAS líneas que se usan para Venta neta:
            # fecha, permisos, establecimiento/local, Moda, línea, marca y
            # vendedor ya fueron aplicados en get_dashboard. No volver a
            # consultar las ventas ignorando esos filtros.
            local_set = set(local_ids)
            rows_period = [row for row in filtered_rows
                           if row.get('local_id') and row['local_id'][0] in local_set]

        # A full-year goal includes January through December, even when
        # the selected year's last real invoice is from an earlier month.
        # Real sales above still respect the dashboard's actual date interval.
        goal_segments = list(_iter_month_segments(
            date(start.year, 1, 1), date(start.year, 12, 31))) if period == 'year' \
            else list(_iter_month_segments(start, end))
        years = sorted({segment['year'] for segment in goal_segments})
        if years:
            roster_domain = [
                ('company_id', '=', company.id), ('source_kind', '=', source),
                ('document_type', 'in', ['FA', 'DE']), ('local_id', 'in', local_ids),
                ('date', '>=', '%s-01-01' % min(years)), ('date', '<=', '%s-12-31' % max(years)),
            ]
        else:
            roster_domain = list(period_domain)
        roster_rows = move_model.search_read(roster_domain, ['seller', 'seller_code'], order='seller,id')
        roster = {}
        for row in roster_rows:
            identity = seller_identity(row.get('seller_code'), row.get('seller'))
            if identity is None:
                continue
            info = roster.setdefault(identity, {
                'name': (row.get('seller') or row.get('seller_code') or 'NO IDENTIFICADO').strip(),
                'code': (row.get('seller_code') or '').strip(),
            })
            if not info['name'] and row.get('seller'):
                info['name'] = row.get('seller').strip()
        seller_keys = sorted(roster, key=lambda key: (roster[key]['name'].casefold(), roster[key]['code'], key))
        actual_by_seller = defaultdict(float)
        for row in rows_period:
            identity = seller_identity(row.get('seller_code'), row.get('seller'))
            if identity is None:
                continue
            actual_by_seller[identity] += (row.get('total_net') or 0.0) * (1 if row.get('document_type') == 'FA' else -1)

        goal_by_year = {}
        if not unassigned:
            goal_model = self.env['analytics.sales.goal'].sudo()
            goal_records = goal_model.search([
                ('company_id', '=', company.id),
                ('establishment_id', '=', establishment.id),
                ('year', 'in', years),
                ('active', '=', True),
            ], order='year,id desc')
            for goal in goal_records:
                goal_by_year.setdefault(goal.year, goal)

        # El dashboard comparte el MISMO reparto de centavos que la ficha
        # Metas > Distribución por vendedor. No volver a repartir un mes
        # con otro algoritmo: hacerlo podría mostrar una cuota distinta
        # a la meta mensual asignada al mismo vendedor en Administración.
        monthly_seller_allocations = {}
        if seller_keys:
            for year in years:
                goal = goal_by_year.get(year)
                monthly_cents = [money_cents(_goal_target_from_record(goal, month))
                                 if goal else 0 for month in range(1, 13)]
                monthly_seller_allocations[year] = equal_month_seller_shares(
                    monthly_cents, len(seller_keys))

        target_total_cents = 0
        target_by_seller_cents = defaultdict(int)
        for segment in goal_segments:
            goal = goal_by_year.get(segment['year'])
            month_target = _goal_target_from_record(goal, segment['month']) if goal else 0.0
            period_target_cents = _goal_cents_for_segment(month_target, segment, period)
            target_total_cents += period_target_cents
            if not seller_keys:
                continue
            if period in ('month', 'previous_month', 'year') or (
                    segment['overlap_days'] == segment['days_in_month']):
                # Cuota íntegra configurada para el mes: exactamente la
                # misma cantidad visible en Distribución por vendedor.
                shares = monthly_seller_allocations[segment['year']][segment['month'] - 1]
            else:
                # Solo los rangos parciales personalizados/30/90 días
                # conservan la prorrata de la versión anterior.
                shares = split_cents(period_target_cents, len(seller_keys))
            for identity, cents in zip(seller_keys, shares):
                target_by_seller_cents[identity] += cents

        actual_total = _signed_sales_amount(rows_period)
        sellers = []
        for identity in seller_keys:
            info = roster[identity]
            target_amount = round(target_by_seller_cents.get(identity, 0) / 100.0, 2)
            actual_amount = round(actual_by_seller.get(identity, 0.0), 2)
            sellers.append({
                'name': info['name'],
                'code': info['code'],
                'target': target_amount,
                'actual': actual_amount,
                'difference': round(actual_amount - target_amount, 2),
                'compliance': round(actual_amount / target_amount * 100, 2) if target_amount else 0.0,
            })
        # El filtro de vendedor se aplica también al detalle visible. La
        # meta individual NO se redistribuye: sigue basada en el censo anual
        # completo, igual que Administración > Metas.
        if selected_seller and selected_seller != 'all':
            sellers = [row for row in sellers if row['name'] == selected_seller]
        sellers.sort(key=lambda row: (-row['actual'], row['name']))
        target_total = round(target_total_cents / 100.0, 2)
        return {
            'available': True,
            'establishment_name': establishment_name,
            'period_label': '%s → %s' % (from_date, to_date),
            'target': target_total,
            'actual': actual_total,
            'difference': round(actual_total - target_total, 2),
            'compliance': round(actual_total / target_total * 100, 2) if target_total else 0.0,
            'seller_count': len(seller_keys),
            'sellers': sellers,
            'seller_max': max([1.0] + [max(s['target'], s['actual']) for s in sellers]),
            'note': (_('Locales autorizados sin establecimiento: ventas reales sin meta mensual asociada.')
                     if unassigned else
                     _('La meta toma las cuotas mensuales configuradas; la venta real aplica los mismos filtros comerciales que el indicador Venta neta.')),
        }

    @api.model
    def _insights(self, groups, totals, admin):
        cards = []
        def top(dim, key, positive=True):
            seq = [r for r in groups[dim] if (r.get(key) is not None) and (not positive or r[key] > 0)]
            return max(seq, key=lambda x: x[key]) if seq else None
        by_units, by_sales = top('stores', 'units'), top('stores', 'sales')
        best_seller = top('sellers', 'invoices')
        best_brand = top('brands', 'units')
        if by_units:
            cards.append({'label': 'Local líder en unidades', 'title': by_units['name'],
                          'detail': '%s unidades netas · %s facturas FA' % (by_units['units'], by_units['invoices'])})
        if by_sales:
            cards.append({'label': 'Local líder en facturación', 'title': by_sales['name'],
                          'detail': 'Ventas netas USD %.2f · %s unidades' % (by_sales['sales'], by_sales['units'])})
        if best_seller:
            cards.append({'label': 'Productividad comercial', 'title': best_seller['name'],
                          'detail': '%s facturas FA · %.2f unidades por factura' % (best_seller['invoices'], best_seller['units_per_invoice'])})
        if best_brand:
            cards.append({'label': 'Marca líder por unidades', 'title': best_brand['name'],
                          'detail': '%s unidades netas · USD %.2f' % (best_brand['units'], best_brand['sales'])})
        risky = top('stores', 'de_sales')
        if risky:
            cards.append({'label': 'Revisar devoluciones', 'title': risky['name'],
                          'detail': 'USD %.2f devueltos y %s unidades DE; revisar causas y período original' % (risky['de_sales'], risky['de_units'])})
        if admin:
            known = [r for r in groups['stores'] if r.get('cost_complete') and r.get('profit') is not None]
            if known:
                best = max(known, key=lambda r: r['profit'])
                cards.append({'label': 'Mayor utilidad bruta', 'title': best['name'],
                              'detail': 'USD %.2f · Margen %.1f%%' % (best['profit'], best['margin'] or 0)})
            if not totals['cost_complete']:
                cards.append({'label': 'Calidad de costos', 'title': 'Costos incompletos',
                              'detail': '%s líneas sin costo. Se omite utilidad y margen global.' % totals['missing_cost_lines']})
        return cards
