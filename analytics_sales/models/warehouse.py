# -*- coding: utf-8 -*-
"""Maestro independiente de valoración de bodegas (no altera ventas)."""
import logging
import math
from decimal import Decimal, ROUND_HALF_UP

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError

from .sync import _keyify, _pick, _amount

_logger = logging.getLogger(__name__)


def _warehouse_rows(rows):
    """Contrato real: Bodega (código), nBodega, Stock y Valor total."""
    if not isinstance(rows, list) or not rows:
        raise ValidationError(_('La API de bodegas no devolvió registros. Se conserva el maestro.'))
    result = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValidationError(_('Bodegas, fila %s: se esperaba un objeto JSON.') % index)
        data = _keyify(row)
        code = _pick(data, 'bodega', 'codigo', 'codigo_bodega', 'cod_bodega', 'code')
        name = _pick(data, 'nbodega', 'nombre', 'nombre_bodega', 'descripcion', 'name')
        raw_stock = _pick(data, 'stock')
        amount = _pick(data, 'valor', 'valor_bodega', 'valor_total', 'value')
        code = str(code).strip() if isinstance(code, (str, int)) and not isinstance(code, bool) else ''
        name = name.strip() if isinstance(name, str) else ''
        stock = None if isinstance(raw_stock, bool) else _amount(raw_stock)
        value = None if isinstance(amount, bool) else _amount(amount)
        if (not code or not name or stock is None or value is None
                or not math.isfinite(stock) or not math.isfinite(value)
                or abs(stock) >= 10**12 or abs(value) >= 10**12):
            raise ValidationError(_('Bodegas, fila %s: Bodega, nBodega, Stock y Valor válidos son obligatorios.') % index)
        vals = {'code': code, 'name': name, 'stock': stock, 'value': value}
        if code in result and result[code] != vals:
            raise ValidationError(_('El código de bodega %s aparece con datos diferentes. Se conserva el maestro; confirme el formato de la API.') % code)
        result[code] = vals
    return list(result.values())


class AnalyticsSalesWarehouse(models.Model):
    _name = 'analytics.sales.warehouse'
    _description = 'Bodega externa de Analytics Sales'
    _order = 'code, id'
    _rec_name = 'name'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company, ondelete='cascade')
    code = fields.Char(string='Código', required=True, index=True, readonly=True)
    name = fields.Char(string='Nombre de la bodega', required=True, readonly=True)
    stock = fields.Float(string='Stock', digits=(18, 2), readonly=True,
                         help='Cantidad total de existencias informada por la API.')
    # El campo anterior no se interpreta como stock: se conserva solo por compatibilidad.
    item = fields.Char(string='Item (anterior)', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.ref('base.USD'), required=True, readonly=True)
    value = fields.Float(string='Valor (uds.)', digits=(18, 6), readonly=True,
                         help='Valor total de la bodega recibido con seis decimales; no se multiplica por el stock.')
    updated_at = fields.Datetime(string='Última actualización', readonly=True)
    establishment_id = fields.Many2one('analytics.sales.establishment', string='Establecimiento',
                                       index=True, check_company=True, ondelete='restrict',
                                       domain="[('company_id', '=', company_id)]",
                                       help='Establecimiento al que pertenece esta bodega. La API conserva esta relación.')
    _sql_constraints = [('warehouse_company_code_unique', 'unique(company_id, code)',
                         'El código de bodega ya existe para esta compañía.')]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = '%s · %s' % (rec.code, rec.name)

    @api.constrains('establishment_id', 'company_id')
    def _check_assignment(self):
        for rec in self:
            if rec.establishment_id and rec.establishment_id.company_id != rec.company_id:
                raise ValidationError(_('La bodega y el establecimiento deben pertenecer a la misma compañía.'))

    def _check_access(self, operation):
        # Odoo 18: central hook for check_access / has_access / _filtered_access.
        # Keep the company-specific Analytics role check in addition to ACLs/rules.
        if not self.env.su:
            try:
                self.env['analytics.sales.security'].check_admin()
            except AccessError as error:
                return self, lambda error=error: error
        return super()._check_access(operation)

    def write(self, vals):
        if not self.env.su:
            self.env['analytics.sales.security'].check_admin()
            if any(rec.company_id != self.env.company for rec in self):
                raise AccessError(_('Solo puede editar bodegas de la compañía actual.'))
            if set(vals) - {'establishment_id'}:
                raise AccessError(_('Los datos de la bodega se actualizan desde la API.'))
        return super().write(vals)

    @api.model
    def _merge_warehouse_rows(self, rows, company):
        records = _warehouse_rows(rows)
        model = self.sudo().with_company(company)
        existing = {rec.code: rec for rec in model.search([('company_id', '=', company.id)])}
        now = fields.Datetime.now()
        created, updated = [], 0
        for vals in records:
            rec = existing.get(vals['code'])
            changes = dict(vals, updated_at=now)
            if rec:
                rec.write(changes)
                updated += 1
            else:
                created.append(dict(changes, company_id=company.id))
        if created:
            model.create(created)
        return {'rows': len(rows), 'created': len(created), 'updated': updated,
                'refreshed': len(records), 'removed': 0}

    @api.model
    def _dashboard_warehouses(self, company, selected_establishment=False):
        """Valorización por establecimiento (sin filtros de ventas)."""
        self.env['analytics.sales.security'].check_admin()
        if company != self.env.company:
            raise AccessError(_('Solo puede consultar bodegas de la compañía actual.'))
        domain = [('company_id', '=', company.id)]
        if selected_establishment:
            domain.append(('establishment_id', '=', selected_establishment))
        groups = {}
        for rec in self.sudo().search(domain):
            establishment = rec.establishment_id
            if establishment and establishment.company_id != company:
                establishment = False
            est_id = establishment.id if establishment else 0
            if selected_establishment and est_id != selected_establishment:
                continue
            group = groups.setdefault(est_id, {
                'id': est_id, 'name': establishment.name if establishment else 'Sin establecimiento',
                'value': 0.0, 'stock': 0.0, 'warehouses': [],
            })
            group['warehouses'].append({'id': rec.id, 'code': rec.code, 'name': rec.name,
                                         'stock': rec.stock, 'value': rec.value})
        # Sumar la precisión original y redondear solo los totales mostrados.
        total_value = sum((Decimal(str(w['value'])) for g in groups.values()
                           for w in g['warehouses']), Decimal('0'))
        total_stock = sum((Decimal(str(w['stock'])) for g in groups.values()
                           for w in g['warehouses']), Decimal('0'))
        for group in groups.values():
            group['value'] = float(sum((Decimal(str(w['value'])) for w in group['warehouses']),
                                       Decimal('0')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
            group['stock'] = float(sum((Decimal(str(w['stock'])) for w in group['warehouses']), Decimal('0')))
        groups = sorted(groups.values(), key=lambda row: (row['id'] == 0, row['name'].casefold()))
        latest = self.env['analytics.sales.sync.log'].sudo().search([
            ('company_id', '=', company.id), ('origin', '=', 'api'),
            ('api_kind', '=', 'warehouse'), ('state', '=', 'ok'),
        ], order='ended_at desc, id desc', limit=1)
        return {'groups': groups, 'value': float(total_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                'stock': float(total_stock),
                'count': sum(len(row['warehouses']) for row in groups),
                'updated_at': fields.Datetime.to_string(latest.ended_at) if latest else False}


class AnalyticsSalesWarehouseSync(models.AbstractModel):
    _inherit = 'analytics.sales.sync'

    @api.model
    def _configured_warehouse_api(self, company, raise_missing=True):
        saved = self._saved_binding(company, 'warehouse_api_id', 'api_warehouse_id')
        if saved and saved != '0':
            try:
                return self._api_record_by_id(company, saved)
            except UserError:
                if raise_missing:
                    raise
                return False
        if raise_missing:
            raise UserError(_('Seleccione la API actualizar_bodega en Administración > Configuración API y guarde.'))
        return False

    @api.model
    def _run_warehouse(self, company):
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (171707, company.id))
        log = self.env['analytics.sales.sync.log'].sudo().create({
            'company_id': company.id, 'origin': 'api', 'state': 'running', 'api_kind': 'warehouse',
        })
        endpoint, record_id = '', 0
        try:
            with self.env.cr.savepoint():
                record = self._configured_warehouse_api(company)
                endpoint, record_id = self._api_identifier(record), record.id
                raw = self._fetch_api(company, endpoint, selected_record=record)
                result = self.env['analytics.sales.warehouse']._merge_warehouse_rows(raw, company)
        except Exception as error:
            message = str(error)[:850]
            log.write({'ended_at': fields.Datetime.now(), 'state': 'error', 'api_endpoint': endpoint,
                       'api_config_id': record_id, 'message': message})
            _logger.exception('Analytics Sales warehouse sync failed (company %s, API ID %s)', company.id, record_id)
            return {'error': message, 'rows': 0, 'created': 0, 'updated': 0, 'removed': 0, 'refreshed': 0}
        log.write({'ended_at': fields.Datetime.now(), 'state': 'ok', 'api_endpoint': endpoint,
                   'api_config_id': record_id, 'total_rows': result['rows'], 'created_rows': result['created'],
                   'updated_rows': result['updated'], 'refreshed_rows': result['refreshed'], 'removed_rows': 0,
                   'message': _('Bodegas actualizadas por código. Se conservaron las relaciones y bodegas ausentes.')})
        return result

    @api.model
    def action_sync_warehouses_now(self):
        self.env['analytics.sales.security'].check_admin()
        return self._run_warehouse(self.env.company)

    @api.model
    def configure_warehouse_cron(self):
        """Migrate the existing noupdate job; preserve nextcall and enable daily execution."""
        if not self.env.su and not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Solo el usuario técnico puede configurar el cron.'))
        cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_warehouses', raise_if_not_found=False)
        if cron:
            cron.sudo().write({'interval_number': 1, 'interval_type': 'days',
                               'active': True})
        return True

    @api.model
    def cron_sync_warehouses(self):
        if not self.env.user.has_group('base.group_system'):
            raise AccessError(_('Solo el usuario técnico del cron puede ejecutar esta tarea.'))
        for company in self.env['res.company'].sudo().search([]):
            if self._saved_binding(company, 'warehouse_api_id', 'api_warehouse_id') in (None, False, '', '0'):
                continue
            try:
                with self.env.cr.savepoint():
                    self.sudo().with_company(company)._run_warehouse(company)
            except Exception:
                _logger.exception('Analytics Sales: fallo inesperado de cron de bodegas, empresa %s', company.id)
        return True
