# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError, UserError


class AnalyticsSalesSettings(models.Model):
    _name = 'analytics.sales.settings'
    _description = 'Configuración de conexión por compañía Analytics Sales'

    company_id = fields.Many2one('res.company', readonly=True, required=True, index=True,
                                 ondelete='cascade', default=lambda self: self.env.company)
    _sql_constraints = [('settings_company_unique', 'unique(company_id)',
                         'Ya existe una configuración API para esta compañía.')]

    dashboard_logo_text = fields.Char(string='Siglas de la cabecera', size=6,
                                      help='Texto del recuadro de marca. Vacío: iniciales de la compañía.')
    dashboard_brand_title = fields.Char(string='Nombre comercial',
                                        help='Vacío: nombre de la compañía activa.')
    dashboard_brand_subtitle = fields.Char(string='Subtítulo comercial',
                                           default='INTELIGENCIA COMERCIAL',
                                           help='Vacío: Inteligencia comercial.')
    dashboard_scope_name = fields.Char(string='Nombre del ámbito personalizado',
                                       default='Líneas seleccionadas')
    dashboard_category_ids = fields.Many2many(
        'analytics.sales.category', 'analytics_sales_settings_category_rel',
        'settings_id', 'category_id', string='Atributos del botón personalizado',
        domain="[('company_id', '=', company_id)]",
        help='Seleccione atributos del maestro de ventas (campo Línea). Sin selección, el ámbito personalizado se oculta.')
    dashboard_scope_default = fields.Boolean(string='Abrir con el ámbito personalizado', default=False)

    @api.constrains('dashboard_category_ids', 'company_id')
    def _check_dashboard_categories(self):
        for record in self:
            if record.dashboard_category_ids.filtered(lambda cat: cat.company_id != record.company_id):
                raise ValidationError(_('Las líneas del ámbito deben pertenecer a la compañía activa.'))

    @api.model
    def _dashboard_preferences(self, company):
        # Private helper called after dashboard authorization. Return presentation
        # settings only, never API credentials, identifiers or other settings.
        record = self.sudo().search([('company_id', '=', company.id)], limit=1)
        name = (company.name or 'Analytics Sales').strip() or 'Analytics Sales'
        words = name.split()
        initials = (''.join(word[0] for word in words[:3]) if len(words) > 1
                    else name[:3]).upper()
        categories = (sorted(record.dashboard_category_ids.filtered(
            lambda cat: cat.company_id == company).mapped('name')) if record else [])
        return {
            # La cabecera toma la identidad corporativa directamente de la compañía
            # activa. Si la empresa aún no tiene logo cargado, el frontend muestra
            # las iniciales como respaldo visual.
            'logo': initials,
            'logo_url': ('/web/image?model=res.company&id=%s&field=logo' % company.id) if company.logo else False,
            'title': name,
            'subtitle': 'INTELIGENCIA COMERCIAL',
            'scope_name': ((record.dashboard_scope_name or '').strip() or 'Líneas seleccionadas') if record else 'Líneas seleccionadas',
            'scope_lines': categories,
            'default_scope': 'configured' if categories and record.dashboard_scope_default else 'all',
        }

    _binding_fields = {
        'annual': ('annual_api_id',),
        'monthly': ('monthly_api_id',),
        'warehouse': ('warehouse_api_id',),
    }
    # Store the selected API Administrator record ID (not its name) in config parameters.
    # A dynamic selection avoids exposing API credentials or requiring extra ACLs for
    # Analytics Sales administrators. The cron resolves the selected record each run.
    annual_api_id = fields.Selection(selection='_available_api_records', string='API de ventas anuales',
                                     help='Seleccione un registro existente en API Administrator; su ID no cambia al renombrarlo.')
    monthly_api_id = fields.Selection(selection='_available_api_records', string='API de ventas mensuales',
                                      help='Seleccione un registro existente en API Administrator; su ID no cambia al renombrarlo.')
    warehouse_api_id = fields.Selection(selection='_available_api_records', string='API actualizar_bodega',
                                      help='Seleccione el registro de API Administrator para actualizar las bodegas una vez al día.')
    # Se conservan los campos de cron de ventas para compatibilidad.
    # Los valores se resuelven desde los XML ID fijos al abrir el formulario.
    annual_cron_id = fields.Selection(selection='_available_sales_crons',
                                      string='Cron de ventas anuales', readonly=True,
                                      help='Vinculación automática al cron diario de medianoche.')
    monthly_cron_id = fields.Selection(selection='_available_sales_crons',
                                       string='Cron de ventas mensuales', readonly=True,
                                       help='Vinculación automática al cron de cada dos horas.')
    warehouse_cron_name = fields.Char(string='Cron de actualización de bodegas',
                                      compute='_compute_warehouse_cron_name', readonly=True)

    def _compute_warehouse_cron_name(self):
        cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_warehouses', raise_if_not_found=False)
        for record in self:
            record.warehouse_cron_name = cron.sudo().name if cron else False

    @api.model
    def _available_api_records(self):
        sync = self.env['analytics.sales.sync'].sudo()
        company = self.env.company
        options = [(str(rec.id), sync._api_label(rec))
                   for rec in sync._available_api_records(company)]
        known = {value for value, label in options}
        for kind in ('annual', 'monthly', 'warehouse'):
            saved = sync._saved_binding(company, '%s_api_id' % kind, 'api_%s_id' % kind)
            if saved and saved != '0' and saved not in known:
                options.append((saved, _('API guardada [ID %s] (no disponible)') % saved))
                known.add(saved)
        return options

    @api.model
    def _available_sales_crons(self):
        # Solo los cron propios de este módulo; cada uno conserva su frecuencia.
        sync = self.env['analytics.sales.sync'].sudo()
        return [(str(cron.id), cron.name) for cron in sync._sales_cron_records()]

    @api.model
    def action_open_saved(self):
        """Open one permanent configuration per company, for every administrator.

        Parameters remain the canonical runtime bindings. Reloading must never
        overwrite them (e.g. when an endpoint was temporarily disabled).
        """
        self.env['analytics.sales.security'].check_admin()
        company = self.env.company
        fields_to_load = ('company_id', 'annual_api_id', 'monthly_api_id',
                          'annual_cron_id', 'monthly_cron_id', 'warehouse_api_id')
        # Serialize initialization; the SQL constraint is the last line of defense.
        self.env.cr.execute('SELECT pg_advisory_xact_lock(%s, %s)', (171708, company.id))
        self.env['analytics.sales.category']._refresh_from_sales(company)
        saved = self.default_get(list(fields_to_load))
        saved['company_id'] = company.id
        record = self.search([('company_id', '=', company.id)], limit=1)
        if record:
            changes = {key: val for key, val in saved.items()
                       if key != 'company_id' and record[key] != val}
            if changes:
                # Internal refresh; default_get preserves unavailable saved API IDs.
                super(AnalyticsSalesSettings, record).write(changes)
        else:
            record = super(AnalyticsSalesSettings, self).create(saved)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Configuración de API'),
            'res_model': self._name,
            'view_mode': 'form',
            'views': [(self.env.ref('analytics_sales.view_analytics_sales_settings_form').id, 'form')],
            'res_id': record.id,
            'target': 'current',
        }

    @api.model
    def action_open_scope(self):
        """Reuse the permanent company settings; never create a second scope."""
        action = self.action_open_saved()
        action.update({
            'name': _('Ámbito de análisis'),
            'views': [(self.env.ref('analytics_sales.view_analytics_sales_scope_form').id, 'form')],
        })
        return action

    @api.model
    def default_get(self, names):
        self.env['analytics.sales.security'].check_admin()
        values = super().default_get(names)
        sync = self.env['analytics.sales.sync'].sudo()
        for kind in ('annual', 'monthly', 'warehouse'):
            saved = sync._saved_binding(self.env.company, '%s_api_id' % kind, 'api_%s_id' % kind)
            if saved is not None:
                values['%s_api_id' % kind] = saved if saved != '0' else False
            elif kind != 'warehouse':
                record = sync._configured_api(self.env.company, kind, raise_missing=False)
                values['%s_api_id' % kind] = str(record.id) if record else False
            else:
                values['warehouse_api_id'] = False
            if kind != 'warehouse':
                cron_id = sync._configured_cron_id(self.env.company, kind)
                values['%s_cron_id' % kind] = str(cron_id) if cron_id else False
        return values

    def _get_selected_record(self, kind):
        value = self['%s_api_id' % kind]
        if not value:
            return False
        try:
            record_id = int(value)
        except (ValueError, TypeError):
            raise ValidationError(_('Identificador de API inválido. Vuelva a seleccionar la API.'))
        return self.env['analytics.sales.sync'].sudo()._api_record_by_id(self.env.company, record_id)

    def _check_settings_company(self):
        self.env['analytics.sales.security'].check_admin()
        if any(row.company_id != self.env.company for row in self):
            raise AccessError(_('Cambie a la compañía de la configuración para gestionarla.'))

    @api.model
    def _edited_kinds(self, vals):
        return {kind for kind, names in self._binding_fields.items()
                if set(names).intersection(vals)}

    @api.model_create_multi
    def create(self, vals_list):
        self.env['analytics.sales.security'].check_admin()
        for vals in vals_list:
            if vals.get('company_id', self.env.company.id) != self.env.company.id:
                raise AccessError(_('No puede crear una configuración en otra compañía.'))
        with self.env.cr.savepoint():
            records = super().create(vals_list)
            records._check_settings_company()
            for record, vals in zip(records, vals_list):
                record._persist_links(self._edited_kinds(vals))
        return records

    def write(self, vals):
        self._check_settings_company()
        if 'company_id' in vals and vals['company_id'] != self.env.company.id:
            raise AccessError(_('La configuración pertenece a su compañía original.'))
        # Ordinary Odoo Save (including automatic form save before a button)
        # must persist the links, not just the form record.
        with self.env.cr.savepoint():
            result = super().write(vals)
            kinds = self._edited_kinds(vals)
            for record in self:
                record._persist_links(kinds)
        return result

    def _persist_links(self, kinds):
        self.ensure_one()
        self._check_settings_company()
        if not kinds:
            return
        params = self.env['ir.config_parameter'].sudo()
        cid = self.company_id.id
        sync = self.env['analytics.sales.sync'].sudo()
        # Validate every selected ID, but only write the groups being edited.
        # A missing/disabled endpoint in an unrelated group must not erase it.
        records = {}
        for kind in self._binding_fields:
            if kind in kinds:
                records[kind] = self._get_selected_record(kind)
            elif kind == 'warehouse':
                records[kind] = sync._configured_warehouse_api(self.company_id, raise_missing=False)
            else:
                records[kind] = sync._configured_api(self.company_id, kind, raise_missing=False)
        ids = [record.id for record in records.values() if record]
        if len(ids) != len(set(ids)):
            raise ValidationError(_('Seleccione una API diferente para cada una de las tres sincronizaciones.'))
        for kind in kinds:
            record = records[kind]
            # A nonempty sentinel differentiates an intentional removal from
            # missing old configuration. Odoo drops empty config parameters.
            params.set_param('analytics_sales.api_%s_id.%s' % (kind, cid), str(record.id) if record else '0')
            cron_id = sync._configured_cron_id(self.company_id, kind)
            cron = self.env['ir.cron'].sudo().browse(cron_id).exists() if cron_id else False
            if kind != 'warehouse':
                suffix = 'annual_name' if kind == 'annual' else 'monthly_name'
                params.set_param('analytics_sales.api_%s.%s' % (suffix, cid),
                                 sync._api_identifier(record) if record else '')
                params.set_param('analytics_sales.cron_%s_id.%s' % (kind, cid), str(cron.id) if cron else '0')
                params.set_param('analytics_sales.cron_%s_enabled.%s' % (kind, cid), 'True' if cron else 'False')
            if record and cron and not cron.active:
                cron.sudo().write({'active': True})

    def action_save(self):
        self.ensure_one()
        self._check_settings_company()
        # Normal edits have already been persisted by write(). Explicitly save
        # valid selections too, including a legacy name resolved on first load.
        # Do not erase an unavailable API just because its selector is blank.
        kinds = set()
        unavailable = []
        for kind in self._binding_fields:
            if not self['%s_api_id' % kind]:
                continue
            # A temporarily unavailable saved endpoint is preserved, not erased.
            try:
                self._get_selected_record(kind)
            except (UserError, ValidationError):
                unavailable.append(self['%s_api_id' % kind])
                continue
            kinds.add(kind)
        self._persist_links(kinds)
        if unavailable:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('Vínculos conservados'),
                               'message': _('Se conservaron las APIs guardadas que no están disponibles (IDs: %s). Revise API Administrator.') % ' , '.join(unavailable),
                               'type': 'warning', 'sticky': True}}
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Vínculos guardados'),
                           'message': _('La configuración se guardó de forma permanente para esta compañía.'),
                           'type': 'success', 'sticky': False}}

    def action_verify_links(self):
        self.ensure_one()
        self._check_settings_company()
        sync = self.env['analytics.sales.sync'].sudo()
        status = []
        for kind, title in (('annual', _('Anual')), ('monthly', _('Mensual'))):
            # Verificar valores guardados, no cambios de formulario aún sin guardar.
            record = sync._configured_api(self.env.company, kind, raise_missing=False)
            cron_id = sync._configured_cron_id(self.env.company, kind)
            cron = self.env['ir.cron'].sudo().browse(cron_id).exists() if cron_id else False
            api_label = sync._api_label(record) if record else _('SIN API SELECCIONADA')
            if cron and cron.active:
                cron_label = cron.name
            elif cron:
                cron_label = _('%s (DESACTIVADO)') % cron.name
            else:
                cron_label = _('SIN CRON VINCULADO')
            status.append('%s: %s | Cron: %s' % (title, api_label, cron_label))
        warehouse = sync._configured_warehouse_api(self.env.company, raise_missing=False)
        warehouse_cron = self.env.ref('analytics_sales.ir_cron_analytics_sales_warehouses').sudo()
        status.append(_('Bodegas: %s | Cron: %s') % (
            sync._api_label(warehouse) if warehouse else _('SIN API SELECCIONADA'),
            warehouse_cron.name if warehouse_cron.active else _('DESACTIVADO')))
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Relación guardada de APIs con cron'),
                           'message': '\n'.join(status) + '\n' + _('(Configuración guardada; no ejecuta llamadas API)'),
                           'type': 'info', 'sticky': True}}

    def _notification(self, title, result):
        if result.get('error'):
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': title, 'message': result['error'],
                               'type': 'danger', 'sticky': True}}
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': title,
                           'message': _('%s movimientos leídos. Nuevos: %s, actualizados: %s, eliminados: %s.') %
                                      (result['rows'], result['created'], result['updated'], result['removed']),
                           'type': 'success', 'sticky': False}}

    def action_sync_now(self):
        self.ensure_one()
        self._check_settings_company()
        result = self.env['analytics.sales.sync'].action_sync_now()
        if result.get('error'):
            return self._notification(_('Actualización de información'), result)
        warehouse = result['warehouse']
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Información actualizada'), 'type': 'success', 'sticky': False,
                           'message': _('Movimientos de ventas: %s; bodegas: %s. Bodegas nuevas: %s, actualizadas: %s.') %
                                      (result['rows'], warehouse['rows'], warehouse['created'], warehouse['updated'])}}

    def action_sync_annual_now(self):
        self.ensure_one()
        self._check_settings_company()
        return self._notification(_('Ventas anuales'), self.env['analytics.sales.sync'].action_sync_annual_now())

    def action_sync_monthly_now(self):
        self.ensure_one()
        self._check_settings_company()
        return self._notification(_('Ventas mensuales'), self.env['analytics.sales.sync'].action_sync_monthly_now())

    def action_sync_warehouses_now(self):
        self.ensure_one()
        self._check_settings_company()
        # The standard form save already persisted any edits. Use the canonical
        # binding, not a potentially stale value from another open browser tab.
        result = self.env['analytics.sales.sync'].action_sync_warehouses_now()
        if result.get('error'):
            return self._notification(_('Actualización de bodegas'), result)
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Bodegas actualizadas'), 'type': 'success', 'sticky': False,
                           'message': _('%s filas recibidas. Bodegas nuevas: %s, actualizadas: %s.') %
                                      (result['rows'], result['created'], result['updated'])}}

    def action_open_import_wizard(self):
        self.ensure_one()
        self._check_settings_company()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importar Excel de ventas'),
            'res_model': 'analytics.sales.excel.import',
            'view_mode': 'form', 'target': 'new',
            'context': {'default_company_id': self.env.company.id},
        }
