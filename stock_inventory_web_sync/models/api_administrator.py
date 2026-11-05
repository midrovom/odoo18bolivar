# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ApiAdministrator(models.Model):
    _inherit = 'api.administrator'

    inventory_web_products_enabled = fields.Boolean(
        string='Inventario Web: Productos y Bodegas',
        default=False,
        help='Consulta la empresa EXTERNA indicada en show_inventory_web/<empresa>/<lista> y '
             'actualiza la empresa Odoo seleccionada en este formulario. Las bodegas se '
             'resuelven por su código. No marques también «¿Es para actualización de stock?» '
             'porque el cron antiguo procesaría el mismo endpoint.',
    )

    # El Many2one warehouse_id original pertenece a api_administrator y se
    # conserva intacto para los otros procesos. El selector M2M lo sustituye
    # visualmente ÚNICAMENTE cuando se activa Inventario Web.
    inventory_web_price_warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'api_administrator_invweb_price_warehouse_rel',
        'api_id', 'warehouse_id',
        string='Bodega Relacionada',
        domain="[('company_id', '=', company_id)]",
        help='En la lista de precios elegida: Precio se aplica a los productos '
             'presentes en estas bodegas; las demás bodegas utilizan Precio_2. '
             'No restringe la sincronización de existencias: el stock se '
             'actualiza para todas las bodegas declaradas en la API.',
    )

    inventory_web_warehouses_initialized = fields.Boolean(
        string='Selector múltiple de bodegas inicializado', default=False,
        copy=False, help='Control de migración de la antigua bodega individual.',
    )

    def write(self, vals):
        if 'inventory_web_price_warehouse_ids' in vals:
            vals = dict(vals, inventory_web_warehouses_initialized=True)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'inventory_web_price_warehouse_ids' in vals:
                vals['inventory_web_warehouses_initialized'] = True
        return super().create(vals_list)

    @api.constrains('inventory_web_products_enabled', 'inventory_web_price_warehouse_ids', 'company_id')
    def _check_inventory_web_price_warehouses_company(self):
        for record in self:
            if not record.inventory_web_products_enabled:
                continue
            invalid = record.inventory_web_price_warehouse_ids.filtered(
                lambda warehouse: warehouse.company_id != record.company_id)
            if invalid:
                raise ValidationError(_(
                    'Las bodegas seleccionadas para Inventario Web deben '
                    'pertenecer a la empresa %(company)s: %(warehouses)s.') % {
                        'company': record.company_id.display_name,
                        'warehouses': ', '.join(invalid.mapped('display_name')),
                    })

    @api.onchange('warehouse_id')
    def _onchange_inventory_web_legacy_warehouse(self):
        for record in self:
            if (record.inventory_web_products_enabled and record.warehouse_id
                    and not record.inventory_web_price_warehouse_ids):
                record.inventory_web_price_warehouse_ids = [(4, record.warehouse_id.id)]

    @api.onchange('inventory_web_products_enabled')
    def _onchange_inventory_web_products_enabled(self):
        for record in self:
            if record.inventory_web_products_enabled:
                record.is_stock_update = False
                if record.warehouse_id and not record.inventory_web_price_warehouse_ids:
                    record.inventory_web_price_warehouse_ids = [(4, record.warehouse_id.id)]

    @api.constrains('inventory_web_products_enabled', 'is_stock_update')
    def _check_separate_stock_sync_channels(self):
        for record in self:
            if record.inventory_web_products_enabled and record.is_stock_update:
                raise ValidationError(_(
                    'Una misma API no puede usar simultáneamente «¿Es para actualización '
                    'de stock?» y «Inventario Web: Productos y Bodegas». '
                    'Desactiva el primero para reservar esta API al cron nuevo.'
                ))

    def action_sync_inventory_web(self):
        self.ensure_one()
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Solo un responsable de inventario puede sincronizar.'))
        # Manual and cron share one endpoint download per company.
        # Each product contains Precio and Precio_2 in its JSON object.
        if not self.inventory_web_products_enabled or self.status != 'A' or self.type != 'get':
            raise UserError(_('Active el check Inventario Web: Productos y Bodegas en esta API GET.'))
        service = self.env['stock.inventory.web.sync'].sudo()
        try:
            endpoint_company, _endpoint_list = service._api_endpoint_identity(self)
        except ValueError as exc:
            raise UserError(str(exc)) from exc
        # Procesa esta API manualmente aunque haya otra marcada de la misma empresa.
        results = service.sync_inventory_web_products(
            company_id=endpoint_company, execution_type='manual', selected_api_id=self.id)
        result = {key: sum(row.get(key, 0) for row in results)
                  for key in ('created', 'updated', 'modified', 'unchanged',
                              'stocks', 'warnings', 'errors')}
        severity = 'warning' if result['errors'] or result['warnings'] else 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Sincronización Inventario Web'),
                'message': _(
                    'Productos creados: %(created)s; existentes procesados: %(updated)s '
                    '(con cambios: %(modified)s, sin cambios: %(unchanged)s); '
                    'bodegas ajustadas: %(stocks)s; advertencias: %(warnings)s; errores: %(errors)s.'
                ) % result,
                'type': severity,
                'sticky': bool(result['errors']),
            },
        }
