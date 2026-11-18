# -*- coding: utf-8 -*-
import hashlib
import json
import logging
import re
from datetime import datetime, date, time, timedelta

import pytz
from urllib.parse import urljoin

import requests
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


def _keyify(obj):
    return {str(k).strip().lower().replace(' ', '').replace('_', ''): v for k, v in obj.items()}


def _pick(obj, *keys):
    for key in keys:
        value = obj.get(key.lower().replace('_', '').replace(' ', ''))
        if value is not None:
            return value
    return None


def _amount(value, default=None):
    if value is None or value == '':
        return default
    try:
        if isinstance(value, str):
            value = value.strip().replace('$', '').replace(' ', '')
            if ',' in value and '.' in value:
                value = value.replace(',', '') if value.rfind('.') > value.rfind(',') else value.replace('.', '').replace(',', '.')
            elif ',' in value:
                value = value.replace(',', '.')
        return float(value)
    except (ValueError, TypeError):
        return default


def _date(value):
    if isinstance(value, (date, datetime)):
        return value.strftime('%Y-%m-%d')
    raw = str(value or '').strip().split(' ')[0].split('T')[0]
    for pattern in ('%Y-%m-%d', '%Y.%m.%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(raw, pattern).date().isoformat()
        except ValueError:
            pass
    return None


def _unwrap(payload):
    if isinstance(payload, (str, bytes)):
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            raise ValidationError(_('La respuesta del API no es JSON válido.'))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if payload.get('success') is False:
            raise ValidationError(_('La API indicó success=false; no se modificaron los datos existentes.'))
        for attr in ('data', 'result', 'rows', 'items', 'registros', 'response'):
            if attr in payload:
                try:
                    return _unwrap(payload[attr])
                except ValidationError:
                    continue
    raise ValidationError(_('El endpoint no devolvió un arreglo de movimientos JSON.'))


# Odoo stores ir.cron.nextcall as UTC, while the business operates in Ecuador.
_ECUADOR_TZ = pytz.timezone('America/Guayaquil')


def _next_analytics_run_utc(kind, now_utc=None):
    """Return next local 00:00 (annual) or even-hour slot (monthly), as naive UTC."""
    now = now_utc or datetime.utcnow().replace(tzinfo=pytz.UTC)
    if now.tzinfo is None:
        now = pytz.UTC.localize(now)
    local = now.astimezone(_ECUADOR_TZ)
    day_start = datetime.combine(local.date(), time.min)
    if kind == 'annual':
        target = day_start + timedelta(days=1)
    elif kind == 'monthly':
        target = day_start + timedelta(hours=(local.hour // 2 + 1) * 2)
    else:
        raise ValueError('Tipo de cron no admitido')
    return _ECUADOR_TZ.localize(target).astimezone(pytz.UTC).replace(tzinfo=None)


class AnalyticsSalesSyncLog(models.Model):
    _name = 'analytics.sales.sync.log'
    _description = 'Historial de sincronización Analytics Sales'
    _order = 'id desc'
    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='cascade')
    started_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    ended_at = fields.Datetime(readonly=True)
    origin = fields.Selection([('api', 'API Administrator'), ('historico', 'Archivo Excel')], required=True)
    state = fields.Selection([('running', 'Procesando'), ('ok', 'Correcto'), ('error', 'Error')], required=True, default='running')
    total_rows = fields.Integer(readonly=True)
    created_rows = fields.Integer(readonly=True)
    updated_rows = fields.Integer(readonly=True)
    refreshed_rows = fields.Integer(string='Claves consultadas', readonly=True)
    removed_rows = fields.Integer(readonly=True)
    message = fields.Text(readonly=True)
    api_endpoint = fields.Char(string='Endpoint API', readonly=True, index=True)
    api_config_id = fields.Integer(string='ID de configuración API', readonly=True, index=True)
    api_kind = fields.Selection([('annual', 'Ventas anuales'), ('monthly', 'Ventas mensuales'), ('warehouse', 'Actualizar bodegas')], string='Cron ejecutado', readonly=True, index=True)


class AnalyticsSalesSync(models.AbstractModel):
    _name = 'analytics.sales.sync'
    _description = 'Sincronización controlada desde API Administrator'

    @api.model
    def _available_api_records(self, company):
        """Show existing API Administrator records without exposing credentials.

        The API Administrator addon is optional for opening the dashboard or
        importing Excel, but must be present to configure API schedules.
        """
        if 'api.administrator' not in self.env.registry.models:
            return []  # No API Administrator installed; no options to select.
        model = self.env['api.administrator'].sudo()
        domain = []
        if 'active' in model._fields:
            domain.append(('active', '=', True))
        if 'company_id' in model._fields:
            domain.append(('company_id', 'in', [False, company.id]))
        return model.search(domain, order='id')

    @api.model
    def _api_identifier(self, record):
        if not record:
            return ''
        # The name accepted by call_api() can differ from display_name.
        for field_name in ('api_name', 'name', 'endpoint_name'):
            if field_name in record._fields:
                value = str(record[field_name] or '').strip()
                if value:
                    return value
        return str(record.display_name or '').strip()

    @api.model
    def _api_label(self, record):
        if not record:
            return ''
        display = str(record.display_name or self._api_identifier(record)).strip()
        return '%s [ID %s]' % (display, record.id)

    @api.model
    def _api_record_by_id(self, company, record_id):
        if 'api.administrator' not in self.env.registry.models:
            raise UserError(_('No está instalado API Administrator (modelo api.administrator).'))
        api_admin = self.env['api.administrator'].sudo()
        try:
            record_id = int(record_id)
        except (ValueError, TypeError):
            raise UserError(_('ID de configuración de API no válido.'))
        record = api_admin.browse(record_id).exists()
        if not record:
            raise UserError(_('La API seleccionada (ID %s) fue eliminada de API Administrator. Seleccione otra.') % record_id)
        if 'active' in api_admin._fields and not record.active:
            raise UserError(_('La API seleccionada (ID %s) está inactiva en API Administrator.') % record_id)
        if 'company_id' in api_admin._fields and record.company_id and record.company_id.id != company.id:
            raise UserError(_('La API ID %s pertenece a otra compañía. Revise la selección.') % record_id)
        if not self._api_identifier(record):
            raise UserError(_('La API ID %s no tiene identificador para call_api().') % record_id)
        return record

    @api.model
    def _find_legacy_api(self, company, kind):
        """One-time migration from the old string-based configuration.

        Resolve only unambiguous names. A renamed API is not guessed: the user
        must select the correct existing record once in settings.
        """
        if 'api.administrator' not in self.env.registry.models:
            return False
        params = self.env['ir.config_parameter'].sudo()
        suffix = 'annual_name' if kind == 'annual' else 'monthly_name'
        default = 'ventas_anuales' if kind == 'annual' else 'ventas_mensuales'
        old_name = (params.get_param('analytics_sales.api_%s.%s' % (suffix, company.id), default) or '').strip()
        if not old_name:
            return False
        model = self.env['api.administrator'].sudo()
        named = [field for field in ('api_name', 'name', 'endpoint_name') if field in model._fields]
        if not named:
            return False
        domain = ['|'] * (len(named) - 1) + [(name, '=', old_name) for name in named]
        domain = ([('active', '=', True)] if 'active' in model._fields else []) + domain
        if 'company_id' in model._fields:
            domain = [('company_id', 'in', [False, company.id])] + domain
        matches = model.search(domain, limit=2)
        return matches[0] if len(matches) == 1 else False

    @api.model
    def _saved_binding(self, company, field_name, param_prefix):
        """Read the persistent parameter, with the company settings as backup.

        '0' is an explicit disconnection, not a missing parameter. Never guess
        a replacement endpoint when an ID was saved but is temporarily inactive.
        """
        key = 'analytics_sales.%s.%s' % (param_prefix, company.id)
        raw = self.env['ir.config_parameter'].sudo().get_param(key, None)
        if raw not in (None, False, ''):
            return str(raw)
        record = self.env['analytics.sales.settings'].sudo().search([
            ('company_id', '=', company.id)], limit=1)
        return str(record[field_name]) if record and record[field_name] else None

    @api.model
    def _configured_api(self, company, kind, raise_missing=True):
        if kind not in ('annual', 'monthly'):
            raise ValidationError(_('Tipo de sincronización API inválido.'))
        saved = self._saved_binding(company, '%s_api_id' % kind, 'api_%s_id' % kind)
        if saved == '0':
            if raise_missing:
                raise UserError(_('No está vinculada la API de ventas. Seleccione y guarde la API correspondiente.'))
            return False
        if saved:
            # Do not silently fall back to a similarly named or different API.
            try:
                return self._api_record_by_id(company, saved)
            except UserError:
                if not raise_missing:
                    # Settings must remain accessible to repair a deleted/disabled API.
                    return False
                raise
        # Backward-compatible first load of version 16.0.1.1.7 settings.
        record = self._find_legacy_api(company, kind)
        if record:
            return record
        if raise_missing:
            raise UserError(_('No está vinculada la API de ventas %s. Vaya a Analytics Sales > Administración > Configuración API, seleccione el registro de API Administrator y guarde.') %
                            (_('anuales') if kind == 'annual' else _('mensuales')))
        return False

    @api.model
    def _endpoint_config(self, company, kind):
        """Compatibility helper used only for informational or legacy paths."""
        record = self._configured_api(company, kind)
        return self._api_identifier(record)

    @api.model
    def _fetch_api(self, company, endpoint, selected_record=None):
        # The endpoint's credentials and URL live exclusively in API Administrator.
        if 'api.administrator' not in self.env.registry.models:
            raise UserError(_('No se encuentra instalado API Administrator (modelo api.administrator). Instálelo y configure el endpoint.'))
        api_admin = self.env['api.administrator'].sudo()
        # Revalidate record and company at execution time, including after rename.
        if selected_record:
            selected_record = self._api_record_by_id(company, selected_record.id)
            endpoint = self._api_identifier(selected_record)
        # Some installations implement call_api, while others expose a configuration record only.
        call = getattr(api_admin, 'call_api', None)
        if callable(call):
            # call_api() currently accepts an API *name*, not a record ID.
            # Refuse ambiguous names rather than calling a different record.
            if selected_record:
                same_name = [rec for rec in self._available_api_records(company)
                             if self._api_identifier(rec) == endpoint]
                if len(same_name) != 1 or same_name[0].id != selected_record.id:
                    raise UserError(_('Hay varias APIs con el identificador "%s" en esta compañía. Renómbrelas de forma única en API Administrator antes de sincronizar.') % endpoint)
            try:
                payload = call(api_name=endpoint, method='get', company_id=company.id)
            except TypeError as error:
                # API Administrator installations can expose call_api(api_name, method)
                # without company_id. Retry only for an actual signature mismatch;
                # never retry a TypeError caused inside the API implementation.
                detail = str(error).lower()
                if 'company_id' in detail and ('unexpected' in detail or 'keyword' in detail):
                    # Without a company parameter, a duplicate name anywhere in the
                    # provider could select a different company's credentials.
                    all_records = api_admin.search([('active', '=', True)]) if 'active' in api_admin._fields else api_admin.search([])
                    same_name_global = [r for r in all_records if self._api_identifier(r) == endpoint]
                    if len(same_name_global) != 1 or (selected_record and same_name_global[0].id != selected_record.id):
                        raise UserError(_('call_api() no admite compañía y existen APIs con el mismo nombre "%s". Renombre los registros con nombres únicos o adapte API Administrator para aceptar company_id.') % endpoint)
                    payload = call(api_name=endpoint, method='get')
                elif 'api_name' in detail and ('unexpected' in detail or 'keyword' in detail):
                    payload = call(endpoint, method='get', company_id=company.id)
                else:
                    raise
            return _unwrap(payload)
        fields_available = api_admin._fields
        if selected_record:
            record = selected_record
        else:
            # Legacy API callers only; cron and manual buttons pass the fixed record.
            matches = api_admin.search([('id', 'in', self._available_api_records(company).ids)])
            matches = matches.filtered(lambda candidate: self._api_identifier(candidate) == endpoint)
            if len(matches) != 1:
                raise UserError(_('API Administrator: el nombre "%s" no identifica una única API. Seleccione su registro por ID.') % endpoint)
            record = matches[0]
        required_fields = ('url', 'end_point', 'user_id', 'password')
        missing = [name for name in required_fields if name not in fields_available]
        if missing:
            raise UserError(_('Esta versión de API Administrator usa otros campos: %s. Adaptar únicamente _fetch_api().') % ', '.join(missing))
        # 'user_id' here is the credential header from the existing API Administrator, not an Odoo user.
        for k in ('user_id', 'password'):
            if fields_available[k].type not in ('char', 'text'):
                raise UserError(_('El campo %s de API Administrator no es texto. Verifique el módulo de referencia para alinear el adaptador.') % k)
        base = (record.url or '').strip()
        resource = (record.end_point or '').strip()
        if not base.lower().startswith(('http://', 'https://')):
            raise UserError(_('La URL configurada en API Administrator es inválida.'))
        address = urljoin(base.rstrip('/') + '/', resource.lstrip('/'))
        headers = {'Accept': 'application/json', 'user_id': record.user_id or '', 'password': record.password or ''}
        try:
            response = requests.get(address, headers=headers, timeout=(10, 120), allow_redirects=False)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as error:
            _logger.warning('Analytics Sales API failed (%s): %s', endpoint, type(error).__name__)
            raise UserError(_('Falló la consulta de ventas a API Administrator. Revise conexión/credenciales/endpoint: %s') % type(error).__name__)
        return _unwrap(payload)

    @api.model
    def _normalize(self, original, index, source_kind):
        if not isinstance(original, dict):
            raise ValidationError(_('Fila %s: no es objeto JSON.') % index)
        m = _keyify(original)
        kind = str(_pick(m, 'tipo', 'tipofactura', 'document_type', 'type') or '').strip().upper()
        if kind not in ('FA', 'DE'):
            raise ValidationError(_('Fila %s: tipo no es FA o DE.') % index)
        nlocal = str(_pick(m, 'nlocal') or '').strip()
        if not nlocal:
            raise ValidationError(_('Fila %s: nlocal es obligatorio; no se permite usar bodega o localidad como sustituto.') % index)
        document = str(_pick(m, 'numero', 'numerofactura', 'document_number', 'documento') or '').strip()
        if not document:
            raise ValidationError(_('Fila %s: falta número de factura/devolución.') % index)
        # La API IDR envía numero='5377', y el histórico Excel utiliza
        # 'FA-5377'/'DE-128'. Normalizar solo la API; no alterar Excel importado.
        if source_kind == 'api' and not document.upper().startswith(kind + '-'):
            document = '%s-%s' % (kind, document)
        fecha = _date(_pick(m, 'fechafactura', 'fecha', 'date'))
        if not fecha:
            raise ValidationError(_('Fila %s: fecha inválida.') % index)
        qty = _amount(_pick(m, 'cantidad', 'quantity', 'qty'))
        total = _amount(_pick(m, 'total_neto', 'totalneto', 'net_total', 'netamount'))
        sku = str(_pick(m, 'codproducto', 'sku', 'product_code') or '').strip()
        if not sku or sku.upper() in ('#NAME?', '#N/A', '#REF!', '#VALUE!', '#DIV/0!', '#NUM!', '#NULL!'):
            # Do not lose sales merely because Excel contains a formula error in SKU.
            # A product-name-based synthetic key is stable across different uploads.
            description = str(_pick(m, 'producto', 'descripcion', 'product_name') or '').strip()
            if description:
                sku = 'SIN-CODIGO-' + hashlib.sha1(description.upper().encode('utf-8')).hexdigest()[:16].upper()
        if qty is None or total is None or not sku:
            raise ValidationError(_('Fila %s: necesita Codproducto (o Producto para generarlo), Cantidad y Total_neto.') % index)
        if not all(abs(x) < 10**12 for x in (qty, total)):
            raise ValidationError(_('Fila %s: importe o cantidad fuera de rango.') % index)
        cost_value = _amount(_pick(m, 'total_costo', 'totalcosto', 'total_cost', 'cost_total'))
        # Costo por unidad is an alternative; do not confuse with absolute total.
        if cost_value is None:
            unit_cost = _amount(_pick(m, 'costo', 'cost', 'unit_cost'))
            if unit_cost is not None:
                cost_value = abs(unit_cost * qty)
        # Contrato IDR: clave identifica UN registro comercial de la API,
        # independientemente del nombre del endpoint, local, fecha o importe.
        # Otras fuentes siguen admitiendo id_linea de forma compatible.
        if source_kind == 'api':
            stable_line = _pick(m, 'clave')
            if not str(stable_line or '').strip():
                stable_line = _pick(m, 'idlinea', 'id_linea', 'lineid', 'line_id', 'id_detalle', 'detail_id')
        else:
            stable_line = _pick(m, 'idlinea', 'id_linea', 'lineid', 'line_id', 'id_detalle', 'detail_id')
        seller = str(_pick(m, 'vendedor', 'seller', 'nombrevendedor') or '').strip() or 'NO IDENTIFICADO'
        line_name = str(_pick(m, 'linea', 'line', 'linea_producto', 'categoria') or '').strip().upper() or 'SIN LÍNEA'
        brand = str(_pick(m, 'marca', 'brand') or '').strip() or 'SIN MARCA'
        raw_model = _pick(m, 'modelo')
        modelo = str(raw_model).strip() if raw_model is not None and raw_model is not False else ''
        # Un elemento debe desaparecer del dashboard solamente si el ERP informa
        # explícitamente su anulación. No inferir anulaciones por ausencia en un
        # corte mensual parcial, porque eso borraría ventas válidas del histórico.
        is_active = True
        if source_kind == 'api':
            explicit_cancelled = _pick(m, 'anulado', 'cancelado', 'cancelled')
            explicit_active = _pick(m, 'activo', 'active')
            external_status = str(_pick(m, 'estado', 'status') or '').strip().lower()
            if explicit_cancelled is not None:
                is_active = not (str(explicit_cancelled).strip().lower() in ('true', '1', 'si', 'sí', 'yes'))
            elif explicit_active is not None:
                is_active = str(explicit_active).strip().lower() in ('true', '1', 'si', 'sí', 'yes')
            elif external_status in ('anulado', 'anulada', 'cancelado', 'cancelada', 'cancelled', 'void', 'voided'):
                is_active = False
        vals = {
            'document_type': kind, 'document_number': document, 'date': fecha,
            'nlocal': nlocal,
            'source_line_id': str(stable_line).strip() if stable_line is not None else '',
            'invoice_display': str(_pick(m, 'factura', 'invoice_display') or '').strip(),
            'seller': seller,
            'seller_code': str(_pick(m, 'codvendedor', 'seller_code') or '').strip(),
            'line_name': line_name,
            'brand': brand,
            'sku': sku,
            'modelo': modelo or False,
            'product_name': str(_pick(m, 'producto', 'descripcion', 'product_name') or sku).strip(),
            'quantity': abs(qty), 'total_net': abs(total),
            'total_cost': abs(cost_value) if cost_value is not None else 0.0,
            'cost_known': cost_value is not None,
            'source_kind': source_kind, 'active': is_active,
        }
        return vals

    @api.model
    def _upsert_snapshot(self, rows, company, origin, mode='replace'):
        """Atomic import. API endpoints always use merge to avoid deleting other periods."""
        if mode not in ('replace', 'merge') or origin not in ('api', 'historico'):
            raise ValidationError(_('Modo de importación no permitido.'))
        if not isinstance(rows, list) or not rows:
            raise ValidationError(_('El origen devolvió cero registros: se conserva el histórico sin modificar.'))
        if len(rows) > 350000:
            raise ValidationError(_('El corte excede 350.000 líneas. Se requiere API paginada.'))
        local_obj = self.env['analytics.sales.local'].sudo()
        move_obj = self.env['analytics.sales.move'].sudo()
        company_id = company.id
        existing_locals = {rec.name: rec.id for rec in local_obj.search([('company_id', '=', company_id)])}
        records = []
        # El contrato API IDR declara clave ÚNICA por detalle. Una repetición
        # exacta dentro del mismo JSON se descarta para no inflar las ventas;
        # si los valores difieren, no existe una forma segura de escoger uno.
        seen = {}
        repeated_source_keys = 0
        for index, raw in enumerate(rows, 1):
            r = self._normalize(raw, raw.get('__excel_row', index) if isinstance(raw, dict) else index, origin)
            nlocal = r.pop('nlocal')
            if nlocal not in existing_locals:
                existing_locals[nlocal] = local_obj.create({'name': nlocal, 'company_id': company_id}).id
            r['local_id'] = existing_locals[nlocal]
            original_id = r['source_line_id']
            if original_id and origin == 'api':
                # Identidad estable: NO depende de fecha, local, importe ni del
                # endpoint anual/mensual. El UNIQUE SQL agrega la compañía.
                raw_key = 'api|clave|%s' % original_id
                if raw_key in seen:
                    repeated_source_keys += 1
                    if seen[raw_key] != r:
                        raise ValidationError(_(
                            'La clave API "%s" aparece más de una vez con datos diferentes '
                            '(fila %s). El origen debe entregar una sola línea por clave.'
                        ) % (original_id, index))
                    continue
                seen[raw_key] = r.copy()
            elif original_id:
                raw_key = json.dumps([origin, r['local_id'], original_id, r['document_type'],
                                      r['document_number'], r['date'][:4]], ensure_ascii=False)
                count = seen.get(raw_key, 0) + 1
                seen[raw_key] = count
                if count > 1:
                    raw_key = '%s|ocurrencia:%s' % (raw_key, count)
            else:
                # Include exact row values so even ambiguous repeated lines can be represented.
                base = json.dumps([origin, r['local_id'], r['document_type'], r['document_number'], r['date'],
                                   r['seller_code'], r['seller'], r['sku'], r['quantity'], r['total_net'],
                                   r['total_cost'] if r['cost_known'] else None], ensure_ascii=False)
                seq = seen.get(base, 0) + 1
                seen[base] = seq
                raw_key = '%s|duplicate:%s' % (base, seq)
            r['source_key'] = hashlib.sha256(raw_key.encode('utf8')).hexdigest()
            r['company_id'] = company_id
            records.append(r)
        keys = [r['source_key'] for r in records]
        if len(keys) != len(set(keys)):
            raise ValidationError(_('El origen contiene IDs de línea duplicados. Verifique el endpoint.'))
        old = move_obj.with_context(active_test=False).search([('company_id', '=', company_id), ('source_kind', '=', origin)])
        existing = {rec.source_key: rec for rec in old}
        initial_keys = set(existing)
        by_fingerprint = {}
        by_document = {}
        by_source_id = {}
        by_product_name = {}
        incoming_doc_counts = {}

        def canonical_document(r):
            # Versiones anteriores guardaron el numero API sin prefijo (5377).
            # Hacer equivalentes 5377 y FA-5377 para actualizar los datos
            # existentes sin duplicarlos al migrar al formato JSON nativo.
            number = str(r['document_number'] or '').strip()
            kind = r['document_type']
            if origin == 'api' and not number.upper().startswith(kind + '-'):
                return '%s-%s' % (kind, number)
            return number

        def document_identity(r):
            local = r['local_id'].id if hasattr(r['local_id'], 'id') else r['local_id']
            return local, r['document_type'], canonical_document(r), str(r['date'])[:4], r['sku']

        def product_identity(r):
            local = r['local_id'].id if hasattr(r['local_id'], 'id') else r['local_id']
            return local, r['document_type'], canonical_document(r), str(r['date'])[:4], (r['product_name'] or '').strip().casefold()

        def source_identity(r):
            line = r['source_line_id'] or ''
            if not line:
                return None
            if origin == 'api':
                # La clave es el identificador único de la línea API, incluso
                # si cambia su local, fecha, vendedor o importe.
                return line
            local = r['local_id'].id if hasattr(r['local_id'], 'id') else r['local_id']
            return local, r['document_type'], canonical_document(r), str(r['date'])[:4], line

        def fingerprint(r):
            local = r['local_id'].id if hasattr(r['local_id'], 'id') else r['local_id']
            def item(name):
                v = r[name]
                if name == 'date':
                    return str(v)
                if name == 'document_number':
                    return canonical_document(r)
                if name in ('quantity', 'total_net', 'total_cost'):
                    return round(float(v or 0), 5)
                return v or ''
            return (local,) + tuple(item(k) for k in (
                'document_type', 'document_number', 'date', 'seller', 'seller_code',
                'line_name', 'brand', 'sku', 'product_name', 'invoice_display',
                'quantity', 'total_net', 'total_cost', 'cost_known', 'active'))

        if mode == 'merge':
            if origin == 'api':
                # Migración segura desde 16.0.1.1.12: esa versión asignaba un
                # sufijo de ocurrencia a claves repetidas e importaba dos filas
                # idénticas. Consolidarlas sin alterar datos distintos.
                grouped = {}
                for rec in old:
                    if rec.source_line_id:
                        grouped.setdefault(rec.source_line_id, []).append(rec)
                removed_legacy = set()
                for source_id, items in grouped.items():
                    if len(items) < 2:
                        continue
                    first = items[0]
                    for extra in items[1:]:
                        if fingerprint(first) != fingerprint(extra):
                            raise ValidationError(_(
                                'Ya existen líneas distintas con la misma clave API "%s". '
                                'Revise estos datos antes de consolidarlos.'
                            ) % source_id)
                        extra.unlink()
                        removed_legacy.add(extra.id)
                if removed_legacy:
                    old = old.filtered(lambda rec: rec.id not in removed_legacy)
                    existing = {rec.source_key: rec for rec in old}
                    initial_keys = set(existing)
            for record in old:
                by_fingerprint.setdefault(fingerprint(record), []).append(record)
                by_document.setdefault(document_identity(record), []).append(record)
                by_product_name.setdefault(product_identity(record), []).append(record)
                if source_identity(record):
                    by_source_id.setdefault(source_identity(record), []).append(record)
            for record in records:
                key = document_identity(record)
                incoming_doc_counts[key] = incoming_doc_counts.get(key, 0) + 1

        created, updated = 0, 0
        new_values = []
        pending_keys = set()
        matched_ids = set()
        for values in records:
            prior = existing.get(values['source_key'])
            if mode == 'merge' and (not prior or prior.id in matched_ids):
                prior = None
                # First match exact line content (works for legacy embedded demo IDs).
                for match in by_fingerprint.get(fingerprint(values), []):
                    if match.id not in matched_ids:
                        prior = match
                        break
                # Explicit ERP line identifiers are stable across changed quantities/prices.
                if not prior and source_identity(values):
                    matches = [r for r in by_source_id.get(source_identity(values), []) if r.id not in matched_ids]
                    if len(matches) == 1:
                        prior = matches[0]
                # A description match allows older demo rows with broken Excel
                # formula SKUs (#NAME?) to be repaired without creating duplicates.
                if not prior and values['product_name']:
                    matches = [r for r in by_product_name.get(product_identity(values), []) if r.id not in matched_ids]
                    if len(matches) == 1:
                        prior = matches[0]
                # When there is exactly one such product line per document, update it.
                # Ambiguous repeated SKU lines are never overwritten by a guessed match.
                if not prior and incoming_doc_counts[document_identity(values)] == 1:
                    matches = [r for r in by_document.get(document_identity(values), []) if r.id not in matched_ids]
                    if len(matches) == 1:
                        prior = matches[0]
            if prior:
                matched_ids.add(prior.id)
                existing.pop(prior.source_key, None)
                changes = {}
                for key, value in values.items():
                    if key == 'source_key':
                        # Las claves antiguas incluían local/documento/sufijos.
                        # Migrar al hash estable de clave, sin recrear registros.
                        if origin == 'api' and prior.source_key != value:
                            changes[key] = value
                        continue
                    if mode == 'merge' and key == 'source_line_id' and not value and prior.source_line_id:
                        continue  # Preserve existing stable IDs when sheet omits them.
                    # Un corte sin modelo no debe borrar el dato que ya entregó otra API.
                    # No se modifica la identidad de la línea ni su clave por añadir el modelo.
                    if key == 'modelo' and not value:
                        continue
                    before = prior[key]
                    if key in ('company_id', 'local_id') and before:
                        before = before.id
                    elif key == 'date':
                        before = str(before)
                    elif key in ('quantity', 'total_net', 'total_cost'):
                        before = float(before or 0.0)
                        if abs(before - float(value)) <= 0.00001:
                            continue
                    if before != value:
                        changes[key] = value
                if changes:
                    prior.write(changes)
                    updated += 1
            else:
                # A source key collision with a previously matched record may happen
                # in an ambiguous sheet. Raise, rather than duplicating an invoice line.
                if values['source_key'] in initial_keys or values['source_key'] in pending_keys:
                    raise ValidationError(_('Hay líneas con identidad ambigua. Incluya id_linea para distinguirlas.'))
                pending_keys.add(values['source_key'])
                new_values.append(values)
        for offset in range(0, len(new_values), 400):
            chunk = new_values[offset:offset + 400]
            move_obj.create(chunk)
            created += len(chunk)
        removed = len(existing) if mode == 'replace' else 0
        if mode == 'replace' and existing:
            move_obj.browse([rec.id for rec in existing.values()]).unlink()
        # Persist the catalog in the same transaction as accepted sales. Work
        # with unique names, not individual movements or a full-table scan.
        self.env['analytics.sales.category']._register_names(
            company, {record['line_name'] for record in records})
        if repeated_source_keys:
            _logger.warning('Analytics Sales: %s filas repetidas con la misma clave API se ignoraron (no duplicar importes/unidades).', repeated_source_keys)
        return {'rows': len(rows), 'created': created, 'updated': updated, 'removed': removed,
                'repeated_keys': repeated_source_keys,
                'source_keys': keys if origin == 'api' else []}

    @api.model
    def _mark_api_keys_checked(self, company, source_keys, api_kind):
        """Timestamp ALL keys returned by the source, even if the values have not changed.

        The raw SQL batch avoids one ORM write per line for large annual snapshots.
        Only origin=api is affected. Updates are in the same savepoint as the
        business-data upsert, so a failed import cannot claim freshness.
        """
        if api_kind not in ('annual', 'monthly'):
            raise ValidationError(_('Tipo de cron no válido para registrar consulta.'))
        if not source_keys:
            return 0
        moves = self.env['analytics.sales.move'].sudo()
        moves.flush_model(['company_id', 'source_kind', 'source_key'])
        now = fields.Datetime.now()
        refreshed = 0
        for offset in range(0, len(source_keys), 5000):
            chunk = source_keys[offset:offset + 5000]
            self.env.cr.execute('''
                UPDATE analytics_sales_move
                   SET api_last_checked_at = %s,
                       api_last_checked_kind = %s
                 WHERE company_id = %s
                   AND source_kind = 'api'
                   AND source_key = ANY(%s)
            ''', (now, api_kind, company.id, chunk))
            refreshed += self.env.cr.rowcount
        moves.invalidate_model(['api_last_checked_at', 'api_last_checked_kind'])
        return refreshed

    @api.model
    def _run(self, company, origin, api_kind=None):
        if origin != 'api' or api_kind not in ('annual', 'monthly'):
            raise ValidationError(_('La carga de Excel requiere seleccionar un archivo desde Importar Excel.'))
        # Annual and monthly jobs can coincide at 00:00. Serialize ingestion for
        # the same company to avoid duplicate inserts from simultaneous workers.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (171706, company.id))
        log = self.env['analytics.sales.sync.log'].sudo().create({
            'company_id': company.id, 'origin': 'api', 'state': 'running',
            'api_endpoint': '', 'api_config_id': 0, 'api_kind': api_kind,
        })
        endpoint = _('sin configurar')
        record_id = 0
        try:
            with self.env.cr.savepoint():
                record = self._configured_api(company, api_kind)
                endpoint = self._api_identifier(record)
                record_id = record.id
                log.write({'api_endpoint': endpoint, 'api_config_id': record_id})
                raw = self._fetch_api(company, endpoint, selected_record=record)
                # DO NOT replace all API rows: annual/monthly API responses overlap
                # and might contain different, partial periods.
                counts = self._upsert_snapshot(raw, company, 'api', mode='merge')
                checked = self._mark_api_keys_checked(company, counts.pop('source_keys'), api_kind)
                counts['refreshed'] = checked
        except Exception as error:
            log.write({'ended_at': fields.Datetime.now(), 'state': 'error',
                       'api_config_id': record_id,
                       'api_endpoint': endpoint if record_id else '',
                       'message': ('API ID %s (%s): %s' % (record_id, endpoint, str(error)))[:1800]})
            _logger.exception('Analytics Sales sync failed (company %s, API ID %s, %s)', company.id, record_id, endpoint)
            return {'error': ('API ID %s (%s): %s' % (record_id, endpoint, str(error)))[:850],
                    'rows': 0, 'created': 0, 'updated': 0, 'removed': 0}
        log.write({'ended_at': fields.Datetime.now(), 'state': 'ok',
                   'total_rows': counts['rows'], 'created_rows': counts['created'],
                   'updated_rows': counts['updated'], 'removed_rows': counts['removed'],
                   'refreshed_rows': counts['refreshed'],
                   'message': ('API ID %s (%s): %s claves revisadas; datos actualizados según respuesta actual (sin eliminar otros períodos).%s' %
                               (record_id, endpoint, counts['refreshed'],
                                (' Se ignoraron %s filas duplicadas de clave.' % counts['repeated_keys'])
                                if counts.get('repeated_keys') else ''))})
        return counts

    @api.model
    def action_sync_annual_now(self):
        self.env['analytics.sales.security'].check_admin()
        return self._run(self.env.company, 'api', 'annual')

    @api.model
    def action_sync_monthly_now(self):
        self.env['analytics.sales.security'].check_admin()
        return self._run(self.env.company, 'api', 'monthly')

    @api.model
    def action_sync_now(self):
        """Actualización manual de las tres APIs, sin cambiar sus cron."""
        self.env['analytics.sales.security'].check_admin()
        company = self.env.company
        results = [self._run(company, 'api', k) for k in ('annual', 'monthly')]
        warehouse = self._run_warehouse(company)
        # Each import has its own savepoint/log. A failed endpoint must not hide
        # successful updates from the other endpoints or mix warehouse counts
        # with sales movement counts.
        summary = {key: sum(r.get(key, 0) for r in results)
                   for key in ('rows', 'created', 'updated', 'removed')}
        summary['warehouse'] = warehouse
        errors = ['%s: %s' % (label, result['error'])
                  for label, result in zip((_('Ventas anuales'), _('Ventas mensuales'), _('Bodegas')),
                                           results + [warehouse]) if result.get('error')]
        if errors:
            summary['error'] = ' | '.join(errors)
        return summary

    @api.model
    def action_import_excel(self, rows, mode, filename, sheet):
        """Called by the transient upload wizard, not from scheduled API processing."""
        self.env['analytics.sales.security'].check_admin()
        company = self.env.company
        if mode not in ('replace', 'merge'):
            raise ValidationError(_('Modo de importación inválido.'))
        log = self.env['analytics.sales.sync.log'].sudo().create({
            'company_id': company.id, 'origin': 'historico', 'state': 'running',
        })
        try:
            with self.env.cr.savepoint():
                counts = self._upsert_snapshot(rows, company, 'historico', mode=mode)
        except Exception as error:
            _logger.exception('Analytics Sales Excel import failed (company=%s, filename=%s)', company.id, filename)
            log.write({'ended_at': fields.Datetime.now(), 'state': 'error',
                       'message': ('Archivo: %s | Hoja: %s | %s' % (filename, sheet, str(error)))[:1800]})
            return {'error': str(error)[:850]}
        log.write({'ended_at': fields.Datetime.now(), 'state': 'ok',
                   'total_rows': counts['rows'], 'created_rows': counts['created'],
                   'updated_rows': counts['updated'], 'removed_rows': counts['removed'],
                   'message': ('Archivo: %s | Hoja: %s | Modo: %s' % (filename, sheet, mode))[:1800]})
        return counts

    @api.model
    def _sales_cron_records(self):
        """Los dos únicos cron que puede vincular esta configuración."""
        jobs = self.env['ir.cron'].sudo()
        for xmlid in ('analytics_sales.ir_cron_analytics_sales_anuales',
                      'analytics_sales.ir_cron_analytics_sales_mensuales'):
            cron = self.env.ref(xmlid, raise_if_not_found=False)
            # El usuario Administrador de Analytics Sales no necesita pertenecer
            # al grupo técnico Ajustes para consultar las opciones del selector.
            if cron:
                cron = cron.sudo()
                if cron._name == 'ir.cron' and cron.model_id.model == self._name:
                    jobs |= cron
        return jobs

    @api.model
    def _configured_cron_id(self, company, kind):
        """Each API has its own automatic job; legacy selectors cannot swap jobs."""
        xmlids = {
            'annual': 'analytics_sales.ir_cron_analytics_sales_anuales',
            'monthly': 'analytics_sales.ir_cron_analytics_sales_mensuales',
            'warehouse': 'analytics_sales.ir_cron_analytics_sales_warehouses',
        }
        if kind not in xmlids:
            raise ValidationError(_('Tipo de sincronización inválido.'))
        cron = self.env.ref(xmlids[kind], raise_if_not_found=False)
        return cron.id if cron and cron._name == 'ir.cron' else False

    @api.model
    def _cron_sync_kind(self, job_kind):
        """The annual and monthly jobs only run their corresponding saved API."""
        if job_kind not in ('annual', 'monthly'):
            raise ValidationError(_('Tipo de cron desconocido.'))
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Solo el usuario técnico del cron puede ejecutar las sincronizaciones.'))
        for company in self.env['res.company'].sudo().search([]):
            saved = self._saved_binding(company, '%s_api_id' % job_kind, 'api_%s_id' % job_kind)
            if saved in (None, False, '', '0'):
                continue
            try:
                with self.env.cr.savepoint():
                    result = self.sudo().with_company(company)._run(company, 'api', job_kind)
                    if result.get('error'):
                        _logger.error('Analytics Sales cron %s empresa %s falló (ver historial)',
                                      job_kind, company.id)
            except Exception:
                _logger.exception('Analytics Sales cron %s empresa %s: fallo inesperado',
                                  job_kind, company.id)
        return True

    @api.model
    def cron_sync_anuales(self):
        """Trabajo anual 00:00 Ecuador; ejecuta la API vinculada a este cron."""
        return self._cron_sync_kind('annual')

    @api.model
    def cron_sync_mensuales(self):
        """Trabajo cada 2 horas; ejecuta la API vinculada a este cron."""
        return self._cron_sync_kind('monthly')

    @api.model
    def cron_sync(self):
        """Legacy job retained as no-op to prevent duplicate syncs on updates."""
        _logger.info('Analytics Sales legacy cron ignored; use annual/monthly jobs')
        return True

    @api.model
    def configure_crons(self):
        """Called by XML on install AND upgrade; disables old job and aligns Ecuador times.

        Jobs run automatically; dispatch checks each company's saved API ID.
        The old cron selectors cannot disable or swap the jobs.
        """
        for kind, xmlid, cron_name in (
            ('annual', 'analytics_sales.ir_cron_analytics_sales_anuales', 'Analytics Sales | Ventas anuales |'),
            ('monthly', 'analytics_sales.ir_cron_analytics_sales_mensuales', 'Analytics Sales | Ventas mensuales |'),
        ):
            cron = self.env.ref(xmlid, raise_if_not_found=False)
            if cron:
                # ir.cron XML is noupdate=1: rename persisted jobs on module upgrades.
                vals = {
                    'name': cron_name, 'active': True,
                    'interval_number': 1 if kind == 'annual' else 2,
                    'interval_type': 'days' if kind == 'annual' else 'hours',
                }
                # Keep an already aligned next call, including a due job, on upgrades.
                nextcall = fields.Datetime.to_datetime(cron.nextcall)
                local = pytz.UTC.localize(nextcall).astimezone(_ECUADOR_TZ) if nextcall else None
                aligned = local and local.minute == 0 and local.second == 0 and (
                    local.hour == 0 if kind == 'annual' else local.hour % 2 == 0)
                if not aligned:
                    vals['nextcall'] = fields.Datetime.to_string(_next_analytics_run_utc(kind))
                cron.sudo().write(vals)
        old_cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_sync', raise_if_not_found=False)
        if old_cron:
            old_cron.sudo().write({'active': False})

        params = self.env['ir.config_parameter'].sudo()
        companies = self.env['res.company'].sudo().search([])
        for company in companies:
            # Repair missing parameter copies from permanent settings before
            # looking at legacy names/defaults. Do not overwrite saved IDs or 0.
            for field_name, prefix in (
                ('annual_api_id', 'api_annual_id'), ('monthly_api_id', 'api_monthly_id'),
                ('warehouse_api_id', 'api_warehouse_id'),
            ):
                key = 'analytics_sales.%s.%s' % (prefix, company.id)
                if params.get_param(key, None) in (None, False, ''):
                    recovered = self._saved_binding(company, field_name, prefix)
                    if recovered is not None:
                        params.set_param(key, recovered)
            for kind in ('annual', 'monthly'):
                key_api = 'analytics_sales.api_%s_id.%s' % (kind, company.id)
                if not params.get_param(key_api):
                    record = self._find_legacy_api(company, kind)
                    if record:
                        params.set_param(key_api, str(record.id))
                cron_id = self._configured_cron_id(company, kind)
                if cron_id:
                    params.set_param('analytics_sales.cron_%s_id.%s' % (kind, company.id), str(cron_id))
                    params.set_param('analytics_sales.cron_%s_enabled.%s' % (kind, company.id), 'True')
        return True
