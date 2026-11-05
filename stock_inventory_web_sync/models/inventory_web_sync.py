# -*- coding: utf-8 -*-
"""Importación independiente de productos, lista de precios y stock por bodega.

Compatible con Odoo 18. Utiliza las APIs GET activas de api.administrator y
sus mismas cabeceras/autenticación. No recibe ningún endpoint fijo.
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

from .combined_payload import combine_catalogs
from .endpoint_routing import endpoint_company_and_price
from .warehouse_payload import (
    as_number, declared_warehouse_codes, resolve_warehouse_ids, stock_targets, trace_state,
)

_logger = logging.getLogger(__name__)


class StockInventoryWebLog(models.Model):
    _name = 'stock.inventory.web.log'
    _description = 'Resultado de sincronización de inventario web'
    _order = 'date desc, id desc'

    date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    api_id = fields.Many2one('api.administrator', string='Configuración API', readonly=True, ondelete='set null')
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True)
    state = fields.Selection([
        ('success', 'Correcto'), ('warning', 'Con advertencias'), ('error', 'Error'),
    ], required=True, default='success', readonly=True)
    created_count = fields.Integer(string='Productos creados', readonly=True)
    updated_count = fields.Integer(string='Productos existentes procesados', readonly=True)
    modified_count = fields.Integer(string='Existentes con cambios', readonly=True)
    unchanged_count = fields.Integer(string='Existentes sin cambios', readonly=True)
    stock_count = fields.Integer(string='Bodegas ajustadas', readonly=True)
    warning_count = fields.Integer(string='Advertencias', readonly=True)
    error_count = fields.Integer(string='Errores', readonly=True)
    details = fields.Text(string='Detalle', readonly=True)
    product_log_ids = fields.One2many('stock.inventory.web.product.log', 'sync_log_id',
                                      string='Detalle por producto', readonly=True)


class StockInventoryWebProductLog(models.Model):
    _name = 'stock.inventory.web.product.log'
    _description = 'Historial de sincronización API por producto'
    _order = 'date desc, id desc'

    date = fields.Datetime(string='Fecha', default=fields.Datetime.now, readonly=True, required=True)
    sync_log_id = fields.Many2one('stock.inventory.web.log', string='Ejecución',
                                  readonly=True, ondelete='cascade', index=True)
    api_id = fields.Many2one('api.administrator', string='API', readonly=True, ondelete='set null')
    company_id = fields.Many2one('res.company', string='Empresa', readonly=True, index=True)
    product_id = fields.Many2one('product.product', string='Variante', readonly=True,
                                  ondelete='set null', index=True)
    product_tmpl_id = fields.Many2one('product.template', string='Producto', readonly=True,
                                       ondelete='set null', index=True)
    sku = fields.Char(string='Código SKU', readonly=True, index=True)
    product_name = fields.Char(string='Nombre recibido', readonly=True)
    execution_type = fields.Selection([('cron', 'Cron'), ('manual', 'Manual')],
                                      string='Origen', readonly=True)
    state = fields.Selection([
        ('created', 'Creado'), ('updated', 'Actualizado'),
        ('unchanged', 'Sin cambios'), ('warning', 'Con advertencias'),
        ('error', 'Error'),
    ], string='Resultado', readonly=True, required=True, default='unchanged')
    stock_count = fields.Integer(string='Bodegas ajustadas', readonly=True)
    details = fields.Text(string='Detalle de la actualización', readonly=True)


class StockInventoryWebSync(models.Model):
    _name = 'stock.inventory.web.sync'
    _description = 'Servicio de sincronización Inventario Web API'

    @api.model
    def _check_sync_access(self):
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise UserError(_('Solo un responsable de inventario puede ejecutar la sincronización.'))

    @api.model
    def _api_endpoint_identity(self, api_record):
        """Parse external company and external pricelist from the URL.

        The external company ID groups source feeds; it is NOT res.company.id.
        API Administrator company_id chooses the destination Odoo company.
        The final URL segment selects the external pricelist; price_list_id
        chooses the corresponding destination pricelist in Odoo.
        """
        return endpoint_company_and_price(api_record.url, api_record.end_point)

    @api.model
    def sync_inventory_web_products(self, company_id=False, execution_type='cron', selected_api_id=False):
        """One pass per *external* company, updating its configured Odoo company.

        company_id is an optional external-company filter (URL segment), not
        an Odoo res.company ID. One configured endpoint contains both fields.
        """
        self._check_sync_access()
        domain = [('type', '=', 'get'), ('status', '=', 'A'),
                  ('inventory_web_products_enabled', '=', True)]
        apis = self.env['api.administrator'].sudo().search(domain)
        grouped = defaultdict(list)
        routes_by_id = {}
        invalid = 0
        for api_record in sorted(apis, key=lambda rec: rec.id):
            try:
                endpoint_company, external_price = self._api_endpoint_identity(api_record)
            except ValueError as exc:
                invalid += 1
                _logger.error('[INV_WEB_SYNC] API_RUTA_INVALIDA api_id=%s: %s',
                              api_record.id, exc)
                continue
            if company_id and endpoint_company != int(company_id):
                continue
            grouped[endpoint_company].append(api_record.id)
            routes_by_id[api_record.id] = external_price
            _logger.info('[INV_WEB_SYNC] API_SELECCIONADA api_id=%s '
                         'empresa_externa=%s lista_externa=%s empresa_odoo=%s '
                         'lista_odoo=%s', api_record.id, endpoint_company, external_price,
                         api_record.company_id.id, api_record.price_list_id.id or 'precio_venta')
        _logger.info('[INV_WEB_SYNC] CRON_INICIO origen=%s empresa_endpoint=%s '
                     'apis_marcadas=%s rutas_invalidas=%s empresas=%s',
                     execution_type, company_id or 'todas', len(apis), invalid, len(grouped))
        results = []
        for endpoint_company, ids in grouped.items():
            # Una empresa EXTERNA se sincroniza con UN solo endpoint. Durante
            # la migración pueden seguir marcadas las dos API antiguas: no
            # duplicar HTTP ni aplicar stock dos veces por esa configuración.
            # El botón manual prioriza expresamente la API seleccionada.
            selected_id = min(ids, key=lambda record_id: (
                routes_by_id[record_id], record_id))
            if selected_api_id in ids:
                selected_id = selected_api_id
            ignored_ids = sorted(set(ids) - {selected_id})
            if ignored_ids:
                _logger.warning('[INV_WEB_SYNC] ENDPOINTS_EXTRA_OMITIDOS '
                                'empresa_externa=%s api_seleccionada=%s '
                                'apis_omitidas=%s motivo=solo_un_endpoint',
                                endpoint_company, selected_id, ignored_ids)
            _logger.info('[INV_WEB_SYNC] LOTE_API empresa_endpoint=%s api_ids=[%s]',
                         endpoint_company, selected_id)
            try:
                with self.env.cr.savepoint():
                    result = self.sync_api(selected_id, execution_type=execution_type)
                results.append(result)
            except Exception:
                _logger.exception('[INV_WEB_SYNC] LOTE_ERROR empresa_endpoint=%s api_ids=%s',
                                  endpoint_company, ids)
                results.append(dict(created=0, updated=0, stocks=0, errors=1,
                                    modified=0, unchanged=0, warnings=0))
        if not grouped:
            _logger.warning('[INV_WEB_SYNC] SIN_APIS: ninguna API válida marcada para empresa_endpoint=%s.',
                            company_id or 'todas')
        _logger.info('[INV_WEB_SYNC] CRON_FIN empresas=%s apis_procesadas=%s '
                     'productos=%s stock=%s errores=%s',
                     len(grouped), len(grouped),
                     sum(r['created'] + r['updated'] for r in results),
                     sum(r['stocks'] for r in results), sum(r['errors'] for r in results))
        return results

    @api.model
    def _hide_radis_inventory_menu(self):
        """Hide only Radis/Rady inventory navigation, never delete its data/cron."""
        root = self.env.ref('stock.menu_stock_root', raise_if_not_found=False)
        if not root:
            return True
        Menu = self.env['ir.ui.menu'].sudo()
        for menu in Menu.search(['|', ('name', 'ilike', 'radis'),
                                  ('name', 'ilike', 'rady')]):
            name = (menu.name or '').lower()
            if not ('radis' in name or 'rady' in name):
                continue
            parent = menu.parent_id
            inside_inventory = False
            while parent:
                if parent.id == root.id:
                    inside_inventory = True
                    break
                parent = parent.parent_id
            if inside_inventory and menu.active:
                menu.write({'active': False})
                _logger.info('[INV_WEB_SYNC] MENU_OCULTO Radis/Rady id=%s name=%s',
                             menu.id, menu.name)
        return True

    @api.model
    def _migrate_inventory_web_price_warehouses(self):
        """Copy existing warehouse_id to M2M without changing the legacy API.

        Called on upgrades as well as installation; idempotent. Never replaces
        or deletes manually selected additional warehouses.
        """
        Api = self.env['api.administrator'].sudo()
        for record in Api.search([
            ('inventory_web_products_enabled', '=', True),
            ('inventory_web_warehouses_initialized', '=', False),
        ]):
            values = {'inventory_web_warehouses_initialized': True}
            if (record.warehouse_id and record.warehouse_id.company_id == record.company_id
                    and not record.inventory_web_price_warehouse_ids):
                values['inventory_web_price_warehouse_ids'] = [
                    (4, record.warehouse_id.id),
                ]
            record.write(values)
        return True

    @api.model
    def _migrate_inventory_web_cron_code(self):
        """Reescribe únicamente los crons asociados al modelo nuevo.

        El XML ID del cron original tiene `noupdate=1`, por lo que una simple
        modificación del XML no basta para actualizar instalaciones existentes.
        No se modifica ningún cron de `stock.api.sync` del módulo antiguo.
        """
        target_model = 'stock.inventory.web.sync'
        old_call = 'model.sync_all_inventory('
        new_call = 'model.sync_inventory_web_products('
        jobs = self.env['ir.cron'].sudo().search([
            ('model_id.model', '=', target_model),
            ('state', '=', 'code'),
            ('code', 'ilike', 'sync_all_inventory'),
        ])
        for job in jobs:
            replacement = (job.code or '').replace(old_call, new_call)
            if replacement != job.code:
                job.write({'code': replacement})
                _logger.info('Inventario Web API: cron %s (%s) actualizado al nuevo método.',
                             job.name, job.id)
        # El registro original fue creado con noupdate=1 y active=False.
        # Cambiar solo el XML no lo activa en bases que ya tenían el módulo.
        # Se toca EXCLUSIVAMENTE el cron que pertenece a este módulo,
        # nunca stock_api_assing ni las tareas Radis.
        cron = self.env.ref('stock_inventory_web_sync.ir_cron_inventory_web_sync',
                            raise_if_not_found=False)
        if cron and cron.model_id.model == target_model:
            expected_code = 'model.sync_inventory_web_products()'
            vals = {}
            if not cron.active:
                vals['active'] = True
            if cron.code != expected_code:
                vals['code'] = expected_code
            if vals:
                cron.sudo().write(vals)
                _logger.info('[INV_WEB_SYNC] CRON_ACTIVADO id=%s code=%s',
                             cron.id, expected_code)
        return True

    @api.model
    def _price_list_destination(self, api_record, external_price_id):
        """Precio público al producto; Precio_2 a la lista Odoo EXISTENTE.

        Una sola API contiene ambos precios. La selección realizada por el
        usuario en API Administrator es la única lista utilizada. Incluso
        una lista llamada 'Public Pricelist' se respeta como tal; nunca debe
        confundirse con product.template.list_price al escribir Precio_2.
        """
        if external_price_id == 1:
            return False
        return api_record.price_list_id or False

    @api.model
    def _validate_existing_pricelist(self, api_record, company):
        """Evitar creación y reutilización involuntaria de listas autogeneradas.

        Las listas autogeneradas por versiones anteriores se conservan en la
        base de datos: pueden tener clientes, reglas o pedidos asociados.
        El usuario debe seleccionar su lista pública existente explícitamente.
        """
        selected = api_record.price_list_id
        if not selected:
            raise UserError(_(
                'Seleccione una lista de precios ya existente en API Administrator '
                'antes de sincronizar. Inventario Web no crea listas nuevas.'
            ))
        if (selected.name or '').startswith((
                'Inventario Web Mayorista - Empresa externa ',
                'Inventario Web - Empresa externa ')):
            raise UserError(_(
                'La API sigue vinculada a la lista creada automáticamente «%s». '
                'Seleccione su lista pública existente en el campo Lista de Precios '
                'de API Administrator. No se creará ni eliminará ninguna lista.'
            ) % selected.display_name)
        if selected.company_id and selected.company_id != company:
            raise UserError(_(
                'La lista de precios «%s» pertenece a otra empresa. '
                'Seleccione una lista existente de %s.'
            ) % (selected.display_name, company.display_name))
        return selected

    @api.model
    def sync_api(self, api_id, execution_type='manual'):
        """Download selected APIs first; synchronize each SKU only once."""
        self._check_sync_access()
        ids = ([int(one) for one in api_id] if isinstance(api_id, (list, tuple, set))
               else [int(api_id)])
        api_records = self.env['api.administrator'].sudo().browse(ids).exists().sorted('id')
        if len(api_records) != len(set(ids)):
            raise UserError(_('Una o varias configuraciones API no existen.'))
        for candidate in api_records:
            if (candidate.type != 'get' or candidate.status != 'A'
                    or not candidate.inventory_web_products_enabled):
                raise UserError(_('Todas las API deben ser GET, activas y tener marcado Inventario Web.'))
            if candidate.is_stock_update:
                raise UserError(_('Desactiva el check antiguo de stock en las API de productos.'))
        api_record = api_records[0]
        identities = {api.id: self._api_endpoint_identity(api) for api in api_records}
        endpoint_company_ids = {identity[0] for identity in identities.values()}
        if len(endpoint_company_ids) != 1:
            raise UserError(_('No se pueden mezclar empresas de distintos endpoints en una sincronización.'))
        endpoint_company_id = next(iter(endpoint_company_ids))
        # /show_inventory_web/2/1 => company 2 belongs to the EXTERNAL API.
        # The original stock_api_assing integration uses the company configured
        # on api_administrator to choose res.company in Odoo. Keep that mapping.
        target_company_ids = {api.company_id.id for api in api_records if api.company_id}
        if len(target_company_ids) != 1 or any(not api.company_id for api in api_records):
            raise UserError(_(
                'Las API de la empresa externa %s deben tener la misma Empresa '
                'de Odoo en API Administrator. Revise el campo Empresa en las '
                'dos configuraciones antes de sincronizar.'
            ) % endpoint_company_id)
        target_company_id = next(iter(target_company_ids))
        company = self.env['res.company'].sudo().browse(target_company_id).exists()
        if not company:
            raise UserError(_(
                'La empresa de Odoo configurada (ID %s) no existe. Revise '
                'api_administrator.company_id. El ID %s del endpoint es '
                'un identificador EXTERNO y no debe buscarse en res.company.'
            ) % (target_company_id, endpoint_company_id))
        _logger.info('[INV_WEB_SYNC] EMPRESA_MAPEADA empresa_externa=%s '
                     'empresa_odoo=%s nombre_empresa_odoo=%s api_ids=%s',
                     endpoint_company_id, company.id, company.display_name,
                     api_records.ids)
        # Un endpoint = una lista externa. No mezclar /2/1 con otras rutas /3/1.
        # La lista externa se mapea a la lista Odoo elegida en api_administrator.
        external_lists = [identity[1] for identity in identities.values()]
        if len(external_lists) != len(set(external_lists)):
            raise UserError(_('Hay dos API marcadas para la misma lista externa en la empresa %s. '
                              'Deje un endpoint activo por lista de precios.') % endpoint_company_id)
        price_warehouses = api_record.inventory_web_price_warehouse_ids
        codes = sorted(set(price_warehouses.mapped('code')))
        _logger.info('[INV_WEB_SYNC] PRECIO_POR_BODEGA api_id=%s lista_odoo=%s '
                     'bodegas_precio_publico=%s precio_otras_bodegas=Precio_2 '
                     'stock_todas_las_bodegas=si',
                     api_record.id, api_record.price_list_id.id or 'auto',
                     ','.join(codes) if codes else 'ninguna')
        # La API usa exclusivamente la lista existente indicada por el usuario.
        # No se crea ni asigna ninguna lista nueva (tampoco "Mayorista").
        for price_api in api_records:
            self._validate_existing_pricelist(price_api, company)
        price_targets = []
        for api in api_records:
            price_list = api.price_list_id
            if price_list and price_list.company_id and price_list.company_id != company:
                raise UserError(_('La lista de precios Odoo %s de API %s pertenece a otra empresa. '
                                  'La empresa destino es %s (ID %s), configurada en '
                                  'API Administrator para la empresa externa %s.') %
                                (price_list.display_name, api.name, company.display_name,
                                 company.id, endpoint_company_id))
            # Los destinos dependen de cada campo JSON, no de la ruta /empresa/lista.
            for field_id, field_name in ((1, 'Precio'), (2, 'Precio_2')):
                effective_pricelist = self._price_list_destination(api, field_id)
                target = ('list', effective_pricelist.id) if effective_pricelist else ('base', 0)
                price_targets.append(target)
                _logger.info('[INV_WEB_SYNC] PRECIO_RUTA empresa_externa=%s '
                             'empresa_odoo=%s campo_json=%s api_id=%s '
                             'destino=%s lista_odoo=%s',
                             endpoint_company_id, company.id, field_name, api.id,
                             'product.template.list_price' if not effective_pricelist else 'product.pricelist.item.fixed_price',
                             effective_pricelist.id if effective_pricelist else 'PRECIO_PUBLICO')
        if len(price_targets) != len(set(price_targets)) and len(api_records) > 1:
            raise UserError(_('Las API de listas distintas apuntan a la misma lista de precios en Odoo. '
                              'Seleccione listas distintas en API Administrator (una por endpoint).'))

        result = dict(created=0, updated=0, modified=0, unchanged=0, stocks=0, warnings=0, errors=0)
        notes = ['API agrupadas: %s. Empresa externa desde endpoint: %s. '
                 'Empresa destino Odoo configurada: %s (%s). Listas externas: %s.' %
                 (', '.join(str(api.id) for api in api_records), endpoint_company_id,
                  company.display_name, company.id,
                  ', '.join(str(identities[api.id][1]) for api in api_records))]
        # Cabecera persistente que permite abrir todos los SKU de una ejecución.
        run_log = self.env['stock.inventory.web.log'].sudo().create({
            'api_id': api_record.id,
            'company_id': company.id,
            'state': 'success',
            'details': 'Sincronización iniciada.',
        })
        _logger.info('[INV_WEB_SYNC] API_INICIO origen=%s api_id=%s api=%s '
                     'empresa_externa=%s empresa_odoo=%s ejecucion_id=%s',
                     execution_type, api_record.id, api_record.name,
                     endpoint_company_id, company.id, run_log.id)

        def warn(message):
            result['warnings'] += 1
            _logger.warning('[INV_WEB_SYNC] API_ADVERTENCIA api=%s: %s', api_record.name, message)
            if len(notes) < 200:
                notes.append('ADVERTENCIA: ' + message)

        def error(message):
            result['errors'] += 1
            _logger.error('[INV_WEB_SYNC] API_ERROR api=%s: %s', api_record.name, message)
            if len(notes) < 200:
                notes.append('ERROR: ' + message)

        download_started = time.monotonic()
        downloads = []
        if len(api_records) == 1:
            try:
                downloads = [(api_record, self._get_api_items(api_record))]
            except (requests.RequestException, ValueError, TypeError) as exc:
                error('No se pudo obtener la API %s: %s' % (api_record.id, exc))
        else:
            # Only immutable HTTP configuration is sent to worker threads.
            # Odoo records/cursors are never accessed from a worker thread.
            configs = [(record, self._api_request_config(record)) for record in api_records]
            with ThreadPoolExecutor(max_workers=min(4, len(configs))) as executor:
                futures = {executor.submit(self._fetch_inventory_http, conf): rec
                           for rec, conf in configs}
                for future in as_completed(futures):
                    api = futures[future]
                    try:
                        downloads.append((api, future.result()))
                    except (requests.RequestException, ValueError, TypeError) as exc:
                        error('Descarga fallida API %s: %s' % (api.id, exc))
                    except Exception as exc:
                        _logger.exception('[INV_WEB_SYNC] DESCARGA_ERROR api_id=%s', api.id)
                        error('Descarga fallida API %s: %s' % (api.id, exc))
            downloads.sort(key=lambda result: result[0].id)
        if not downloads:
            self._create_log(api_record, result, notes, run_log=run_log)
            return result
        # Cada SKU llega con ambos campos de precio en una única respuesta:
        # Precio = público (list_price); Precio_2 = mayorista (tarifa Odoo).
        price_api_by_id = {api.id: api for api in api_records}
        price_api_targets = ({1: api_record.id, 2: api_record.id}
                             if len(api_records) == 1 else
                             {identities[api.id][1]: api.id for api in api_records})
        items, merge_warnings = combine_catalogs([
            (api.id,
             (self._price_list_destination(api, identities[api.id][1]).id
              if self._price_list_destination(api, identities[api.id][1]) else False),
             rows) for api, rows in downloads], price_targets=price_api_targets)
        for message in merge_warnings:
            warn(message)
        _logger.info('[INV_WEB_SYNC] API_RESPUESTA empresa_externa=%s empresa_odoo=%s '
                     'ejecucion_id=%s endpoints_solicitados=%s exitosos=%s '
                     'sku_unicos=%s descarga_segundos=%.2f',
                     endpoint_company_id, company.id, run_log.id, len(api_records), len(downloads),
                     len(items), time.monotonic() - download_started)
        # warehouse_id asignado en API Administrator es referencia para SU código.
        # No limita las demás bodegas de un endpoint que trae múltiples códigos.
        configured = next((source.warehouse_id for source in api_records
                           if source.warehouse_id and source.warehouse_id.company_id == company), False)
        for source in api_records:
            if source.warehouse_id and source.warehouse_id.company_id != company:
                warn('API %s: Bodega Relacionada (%s) pertenece a otra empresa; '
                     'se ignora esa referencia y se relacionan bodegas por stock.warehouse.code '
                     'en empresa %s.' % (source.id, source.warehouse_id.display_name, company.id))

        warehouses = self.env['stock.warehouse'].sudo().with_company(company).search([
            ('company_id', '=', company.id),
        ])
        by_id = {wh.id: wh for wh in warehouses}
        try:
            code_ids, mapping_notices = resolve_warehouse_ids(
                [(wh.id, wh.code) for wh in warehouses],
                preferred_id=configured.id if configured else None,
            )
        except ValueError as exc:
            error(str(exc))
            self._create_log(api_record, result, notes, total=len(items), run_log=run_log)
            return result
        by_code = {code: by_id[wh_id] for code, wh_id in code_ids.items()}
        for notice in mapping_notices:
            warn(notice)

        # Consultas agrupadas: evita una búsqueda de SKU y de regla de precio
        # por cada registro de la API. 250 limita el tamaño de los recordsets.
        seen = set()
        pending_last_sync = set()
        pending_product_logs = []
        created_by_code = {}
        Product = self.env['product.product'].sudo().with_company(company).with_context(active_test=False)
        # Resolver una sola vez las ubicaciones internas pertenecientes a cada
        # almacén. Esto habilita una consulta de quants por SKU, no por bodega.
        warehouse_location_ids = self._warehouse_locations(by_code)
        clock = time.monotonic()
        batch_size = 250
        for offset in range(0, len(items), batch_size):
            batch = items[offset:offset + batch_size]
            batch_codes = {self._string(item.get('codigo')) for item in batch
                           if isinstance(item, dict) and self._string(item.get('codigo'))}
            # Products are loaded once, while pricelist rules are loaded for
            # both configured lists in one batched search.
            matches_by_code, rules_by_template = self._preload_product_batch(
                batch_codes, company, False)
            rules_by_template = self._preload_multi_price_rules(
                matches_by_code, price_api_by_id, company)
            # UNA búsqueda de existencias por lote de SKU, en lugar de una
            # búsqueda por producto. Se agrupa por product_id, y cada almacén
            # conserva su conjunto de ubicaciones independientes.
            quants_by_product = self._preload_stock_batch(
                matches_by_code, warehouse_location_ids, company)
            processed_stock_ids = set()
            for index, item in enumerate(batch, 1):
                position = offset + index
                if not isinstance(item, dict):
                    message = 'Registro %s ignorado: no es un objeto JSON.' % position
                    warn(message)
                    self._create_product_log(run_log, api_record, execution_type, '', {},
                                             {'lines': [message]}, 'warning', buffer=pending_product_logs)
                    continue
                code = self._string(item.get('codigo'))
                if not code:
                    message = 'Registro %s ignorado: falta codigo.' % position
                    warn(message)
                    self._create_product_log(run_log, api_record, execution_type, '', item,
                                             {'lines': [message]}, 'warning', buffer=pending_product_logs)
                    continue
                if code in seen:
                    # La API puede repetir el mismo SKU: aplicar el último dato,
                    # sin silenciar la segunda entrada. La traza refleja ambas.
                    warn('Código %s repetido en el JSON: se procesarán todas las apariciones; '
                         'la última cantidad/precio recibido prevalece.' % code)
                seen.add(code)
                # Cada variante que comparte default_code es un producto real
                # independiente de Odoo. Se actualizan TODAS en vez de abortar
                # todo el SKU por encontrar dos coincidencias.
                matching = matches_by_code.get(code)
                if not matching:
                    # Un SKU creado en una página anterior (o antes en la misma)
                    # no figura en la precarga; reusar su producto, no crearlo dos veces.
                    previous_id = created_by_code.get(code)
                    matching = Product.browse([previous_id]) if previous_id else Product.browse()
                variants = list(matching) if matching else [False]
                if len(variants) > 1:
                    warn('%s: existen %s variantes con el mismo código; se actualizarán '
                         'TODAS (cada una mantiene su propio inventario).' % (code, len(variants)))
                for variant in variants:
                    trace = {'lines': [], 'created': False, 'changed': False,
                             'product_id': False, 'product_tmpl_id': False,
                             'warehouse_events': [], 'price_event': None}
                    if item.get('_inventory_web_sources'):
                        trace['lines'].append('APIs consultadas para este SKU: %s.' %
                                              ', '.join(str(api_id) for api_id
                                                        in item['_inventory_web_sources']))
                    if len(variants) > 1:
                        trace['lines'].append('SKU compartido: procesando variante ID %s '
                                              'de %s coincidencias.' % (variant.id, len(variants)))
                    try:
                        # Un savepoint por variante: si falla no impide actualizar
                        # las demás variantes del mismo SKU ni el siguiente SKU.
                        with self.env.cr.savepoint():
                            created, stocks, notices = self._sync_one_product(
                                item, code, company, api_record, by_code, trace,
                                matching=Product.browse([variant.id]) if variant else Product.browse(),
                                price_rules=rules_by_template,
                                price_source_records=price_api_by_id,
                                pending_last_sync=pending_last_sync,
                                warehouse_location_ids=warehouse_location_ids,
                                preloaded_quant_ids=(
                                    quants_by_product.get(variant.id, [])
                                    if (variant and warehouse_location_ids is not None
                                        and variant.id not in processed_stock_ids)
                                    else None),
                            )
                        processed_stock_ids.add(trace['product_id'])
                    except (ValueError, ValidationError, UserError) as exc:
                        self._evict_price_rules(rules_by_template,
                                                trace.get('product_tmpl_id'),
                                                multi=len(api_records) > 1)
                        error('%s (variante %s): %s' % (code, variant.id if variant else '-', exc))
                        self._log_failed_product(run_log, api_record, execution_type, code,
                                                 item, trace, str(exc), buffer=pending_product_logs)
                        continue
                    except Exception as exc:
                        self._evict_price_rules(rules_by_template,
                                                trace.get('product_tmpl_id'),
                                                multi=len(api_records) > 1)
                        _logger.exception('[INV_WEB_SYNC] ERROR sku=%s variante=%s',
                                          code, variant.id if variant else '-')
                        error('%s (variante %s): error inesperado (%s)' %
                              (code, variant.id if variant else '-', exc))
                        self._log_failed_product(run_log, api_record, execution_type, code,
                                                 item, trace, 'Error inesperado: %s' % exc,
                                                 buffer=pending_product_logs)
                        continue
                    if created:
                        new_id = trace['product_id']
                        created_by_code[code] = new_id
                        # Prepara futuras apariciones del SKU en el mismo lote.
                        matches_by_code[code] = Product.browse([new_id])
                    result['created' if created else 'updated'] += 1
                    result['stocks'] += stocks
                    if not created:
                        result['modified' if trace['changed'] else 'unchanged'] += 1
                    for message in notices:
                        warn('%s variante=%s: %s' %
                             (code, trace['product_id'], message))
                    state = trace_state(created, trace['changed'], bool(notices))
                    self._create_product_log(run_log, api_record, execution_type, code, item,
                                             trace, state, stock_count=stocks,
                                             buffer=pending_product_logs)
                    self._emit_product_audit(run_log, api_record, code, item, trace, state, stocks)

            # Una escritura para múltiples fechas de revisión y un INSERT ORM
            # agrupado para el historial; se conservan errores por SKU.
            self._flush_last_sync(pending_last_sync, company)
            self._flush_product_logs(pending_product_logs, run_log)
            elapsed = time.monotonic() - clock
            _logger.info('[INV_WEB_SYNC] PROGRESO api_id=%s ejecucion_id=%s '
                         'procesados=%s total=%s avance=%.1f%% segundos=%.1f '
                         'productos_por_segundo=%.2f bodegas_ajustadas=%s errores=%s',
                         api_record.id, run_log.id, min(offset + len(batch), len(items)),
                         len(items), 100.0 * min(offset + len(batch), len(items)) / len(items),
                         elapsed, min(offset + len(batch), len(items)) / max(elapsed, .001),
                         result['stocks'], result['errors'])

        if len(notes) >= 200:
            notes.append('Se alcanzó el límite de detalles visibles; revise los logs por producto.')
        self._create_log(api_record, result, notes, total=len(items), run_log=run_log)
        _logger.info('[INV_WEB_SYNC] API_FIN api=%s ejecucion_id=%s '
                     'productos_recibidos=%s creados=%s existentes=%s con_cambios=%s '
                     'sin_cambios=%s bodegas_ajustadas=%s advertencias=%s errores=%s',
                     api_record.name, run_log.id, len(items), result['created'],
                     result['updated'], result['modified'], result['unchanged'],
                     result['stocks'], result['warnings'], result['errors'])
        return result

    @api.model
    def _preload_product_batch(self, codes, company, pricelist):
        """Busca SKUs/reglas por grupos sin alterar la detección de duplicados.

        Con un catálogo grande evita N SELECT de product.product y N SELECT
        de product.pricelist.item; el stock continúa ajustándose mediante Odoo.
        """
        Product = self.env['product.product'].sudo().with_company(company).with_context(active_test=False)
        by_code = {}
        by_tmpl = {}
        if not codes:
            return by_code, by_tmpl
        products = Product.search([
            ('default_code', 'in', list(codes)),
            ('product_tmpl_id.company_id', 'in', [False, company.id]),
        ])
        product_ids_by_code = {}
        for product in products:
            product_ids_by_code.setdefault(product.default_code, []).append(product.id)
        for code, ids in product_ids_by_code.items():
            by_code[code] = Product.browse(ids)
        for code in codes:
            by_code.setdefault(code, Product.browse())
        if not pricelist:
            return by_code, by_tmpl
        template_ids = list({p.product_tmpl_id.id for p in products})
        if not template_ids:
            return by_code, by_tmpl
        Item = self.env['product.pricelist.item'].sudo().with_company(company)
        rules = Item.search([
            ('pricelist_id', '=', pricelist.id),
            ('applied_on', '=', '1_product'),
            ('product_tmpl_id', 'in', template_ids),
            ('min_quantity', '=', 0),
        ])
        rule_ids_by_tmpl = {}
        for rule in rules:
            rule_ids_by_tmpl.setdefault(rule.product_tmpl_id.id, []).append(rule.id)
        for tmpl_id, ids in rule_ids_by_tmpl.items():
            by_tmpl[tmpl_id] = Item.browse(ids)
        # La ausencia de reglas también está precargada para evitar fallback SELECT.
        for tmpl_id in template_ids:
            by_tmpl.setdefault(tmpl_id, Item.browse())
        return by_code, by_tmpl

    @api.model
    def _preload_multi_price_rules(self, matches_by_code, api_by_id, company):
        templates = list({p.product_tmpl_id.id for matches in matches_by_code.values()
                          for p in matches})
        rules_by_api = {api_id: {} for api_id in api_by_id}
        pricelist_ids = {price_list.id for api in api_by_id.values()
                         for price_list in [self._price_list_destination(api, 2)] if price_list}
        if not templates or not pricelist_ids:
            return rules_by_api
        Item = self.env['product.pricelist.item'].sudo().with_company(company)
        rules = Item.search([
            ('pricelist_id', 'in', list(pricelist_ids)),
            ('applied_on', '=', '1_product'),
            ('product_tmpl_id', 'in', templates),
            ('min_quantity', '=', 0),
        ])
        grouped = defaultdict(list)
        for rule in rules:
            grouped[(rule.pricelist_id.id, rule.product_tmpl_id.id)].append(rule.id)
        for api_id, api_record in api_by_id.items():
            effective_pricelist = self._price_list_destination(api_record, 2)
            if effective_pricelist:
                for tmpl_id in templates:
                    rules_by_api[api_id][tmpl_id] = Item.browse(
                        grouped.get((effective_pricelist.id, tmpl_id), []))
        return rules_by_api

    @api.model
    def _evict_price_rules(self, cached, tmpl_id, multi=False):
        if tmpl_id:
            if multi:
                for rules in cached.values():
                    rules.pop(tmpl_id, None)
            else:
                cached.pop(tmpl_id, None)

    @api.model
    def _preload_stock_batch(self, matches_by_code, warehouse_location_ids, company):
        """Un SELECT de quants por lote para productos existentes.

        No se reutiliza este caché cuando un SKU se repite después de que ya
        se ajustaron sus existencias, ni para productos creados en la ejecución.
        El ajuste real sigue usando action_apply_inventory de Odoo.
        """
        if warehouse_location_ids is None:
            return {}
        ids = list({p.id for products in matches_by_code.values() for p in products})
        locations = list(set().union(*warehouse_location_ids.values())) if warehouse_location_ids else []
        if not ids or not locations:
            return {}
        quants = self.env['stock.quant'].sudo().with_company(company).search([
            ('company_id', '=', company.id),
            ('product_id', 'in', ids),
            ('location_id', 'in', locations),
        ])
        by_product = {}
        for q in quants:
            by_product.setdefault(q.product_id.id, []).append(q.id)
        return by_product

    @api.model
    def _flush_last_sync(self, pending_ids, company):
        if not pending_ids:
            return
        ids = list(pending_ids)
        pending_ids.clear()
        try:
            with self.env.cr.savepoint():
                self.env['product.template'].sudo().with_company(company).browse(ids).write({
                    'inventory_web_last_sync': fields.Datetime.now(),
                })
        except Exception:
            _logger.exception('[INV_WEB_SYNC] FECHA_SYNC_ERROR productos=%s', len(ids))
            # La fecha es informativa; el stock y el historial son prioritarios.

    @api.model
    def _flush_product_logs(self, buffer, run_log):
        if not buffer:
            return
        vals = list(buffer)
        buffer.clear()
        Log = self.env['stock.inventory.web.product.log'].sudo()
        try:
            with self.env.cr.savepoint():
                Log.create(vals)
        except Exception:
            _logger.exception('[INV_WEB_SYNC] HISTORIAL_BATCH_ERROR ejecucion_id=%s '
                              'Se reintentará registrar los SKU individualmente.', run_log.id)
            for entry in vals:
                try:
                    with self.env.cr.savepoint():
                        Log.create(entry)
                except Exception:
                    _logger.exception('[INV_WEB_SYNC] HISTORIAL_ERROR sku=%s ejecucion_id=%s',
                                      entry.get('sku'), run_log.id)

    def _log_failed_product(self, run_log, api_record, execution_type, code, item,
                            trace, reason, buffer=None):
        # Un producto creado dentro de un savepoint fallido deja de existir;
        # no conservar sus IDs ya revertidos en el registro de error.
        if trace.get('created'):
            trace['product_id'] = False
            trace['product_tmpl_id'] = False
        if not trace.get('product_id') and not trace.get('created'):
            self._attach_existing_product_to_trace(code, run_log.company_id, trace)
        trace.setdefault('lines', []).append('ERROR: %s' % reason)
        trace['lines'].append('Los cambios de este SKU fueron revertidos.')
        self._create_product_log(run_log, api_record, execution_type, code, item,
                                 trace, 'error', buffer=buffer)
        _logger.error('[INV_WEB_SYNC] PRODUCTO_ERROR sku=%s api_id=%s '
                      'ejecucion_id=%s motivo=%s ajustes_revertidos=si',
                      code, api_record.id, run_log.id, reason)

    @api.model
    def _emit_product_audit(self, run_log, api_record, code, item, trace, state, stocks):
        """Logs de servidor para diagnosticar cada SKU y bodega del cron.

        Las entradas AJUSTADA/SIN_CAMBIOS se emiten al finalizar el savepoint
        del producto. El detalle durable se conserva en el historial de Odoo.
        """
        run_id = run_log.id if run_log else 'sin_historial'
        latest_prices = {event.get('campo_json'): event.get('after')
                         for event in trace.get('price_events') or []}
        _logger.info('[INV_WEB_SYNC] PRODUCTO sku=%s nombre=%s producto_id=%s '
                     'api_id=%s empresa_id=%s ejecucion_id=%s resultado=%s '
                     'precio_publico_api=%s precio_venta_api=%s '
                     'stock_total_api=%s bodegas_procesadas=%s bodegas_ajustadas=%s',
                     code, self._log_value(self._string(item.get('Nombre'))),
                     trace.get('product_id') or 'no_asignado', api_record.id,
                     run_log.company_id.id, run_id, state,
                     self._log_value(latest_prices['Precio'])
                     if 'Precio' in latest_prices else 'no_enviado',
                     self._log_value(latest_prices['Precio_2'])
                     if 'Precio_2' in latest_prices else 'no_enviado',
                     self._log_value(item.get('StockTotal')) if 'StockTotal' in item else 'no_enviado',
                     len(trace.get('warehouse_events') or []), stocks)
        for price_event in trace.get('price_events') or ([trace['price_event']]
                                                         if trace.get('price_event') else []):
            _logger.info('[INV_WEB_SYNC] PRECIO_CAMPO sku=%s campo_json=%s precio=%s '
                         'api_origen=%s api_destino=%s',
                         code, price_event.get('campo_json'),
                         self._log_value(price_event['after']),
                         price_event.get('origen_api_id'), price_event.get('api_id'))
            _logger.info('[INV_WEB_SYNC] PRECIO sku=%s api_id=%s ejecucion_id=%s '
                         'lista_externa=%s destino=%s anterior=%s nuevo=%s resultado=%s',
                         code, price_event.get('api_id') or api_record.id, run_id,
                         price_event.get('lista_externa', 'no_identificada'),
                         price_event['label'], self._log_value(price_event['before']),
                         self._log_value(price_event['after']), price_event['state'])
        for event in trace.get('warehouse_events') or []:
            level = logging.WARNING if event['state'] in ('OMITIDA', 'ERROR') else logging.INFO
            _logger.log(level, '[INV_WEB_SYNC] BODEGA sku=%s bodega=%s almacen_id=%s '
                        'almacen=%s empresa_id=%s ejecucion_id=%s anterior=%s '
                        'cantidad_api=%s final=%s resultado=%s motivo=%s',
                        code, event['code'], event.get('warehouse_id') or 'no_encontrado',
                        event.get('warehouse_name') or 'no_encontrado',
                        run_log.company_id.id, run_id,
                        self._log_value(event.get('before')),
                        self._log_value(event.get('target')),
                        self._log_value(event.get('after')),
                        event['state'], event.get('reason') or '-')
        if not trace.get('warehouse_events'):
            _logger.info('[INV_WEB_SYNC] SIN_BODEGAS sku=%s ejecucion_id=%s '
                         'motivo=sin_ajustes_de_stock_realizados', code, run_id)

    def _attach_existing_product_to_trace(self, code, company, trace):
        # Los fallos antes de guardar un producto también se visualizan en su ficha
        # cuando el código identifica una sola variante existente.
        products = self.env['product.product'].sudo().with_company(company).with_context(
            active_test=False).search([
                ('default_code', '=', code),
                ('product_tmpl_id.company_id', 'in', [False, company.id]),
            ], limit=2)
        if len(products) == 1:
            trace['product_id'] = products.id
            trace['product_tmpl_id'] = products.product_tmpl_id.id

    def _create_product_log(self, run_log, api_record, execution_type, code, item,
                            trace, state, stock_count=0, buffer=None):
        values = {
            'sync_log_id': run_log.id,
            'api_id': api_record.id,
            'company_id': run_log.company_id.id,
            'product_id': trace.get('product_id') or False,
            'product_tmpl_id': trace.get('product_tmpl_id') or False,
            'sku': code or '(sin código)',
            'product_name': self._string(item.get('Nombre')) if isinstance(item, dict) else '',
            'execution_type': execution_type,
            'state': state,
            'stock_count': stock_count,
            'details': '\n'.join(trace.get('lines') or ['Sin cambios en los datos recibidos.']),
        }
        if buffer is not None:
            buffer.append(values)
            return
        # Compatibilidad con otros llamadores del método sin buffer.
        self._flush_product_logs([values], run_log)

    def _create_log(self, api_record, result, notes, total=0, run_log=None):
        values = {
            'api_id': api_record.id,
            'company_id': run_log.company_id.id if run_log else api_record.company_id.id,
            'state': 'error' if result['errors'] else ('warning' if result['warnings'] else 'success'),
            'created_count': result['created'],
            'updated_count': result['updated'],
            'modified_count': result['modified'],
            'unchanged_count': result['unchanged'],
            'stock_count': result['stocks'],
            'warning_count': result['warnings'],
            'error_count': result['errors'],
            'details': 'Registros recibidos: %s\n%s' % (total, '\n'.join(notes) or 'Sin incidencias.'),
        }
        try:
            with self.env.cr.savepoint():
                if run_log:
                    run_log.sudo().write(values)
                else:
                    self.env['stock.inventory.web.log'].sudo().create(values)
        except Exception:
            _logger.exception('[INV_WEB_SYNC] RESUMEN_ERROR api_id=%s No se pudo '
                              'persistir el resumen; consulte el archivo odoo.log.', api_record.id)

    @api.model
    def _api_request_config(self, api_record):
        # Build plain values in Odoo's main thread (no ORM use in HTTP threads).
        return {
            'url': (api_record.url or '').strip() + (api_record.end_point or '').strip(),
            'user': (api_record.user_id or '').strip(),
            'password': (api_record.password or '').strip(),
        }

    @staticmethod
    def _fetch_inventory_http(config):
        if not config['url'] or not config['user'] or not config['password']:
            raise ValueError('Falta URL, endpoint, userid o password en api_administrator.')
        headers = {
            'Accept': 'application/json', 'version': '1', 'framework': 'PRUEBAS',
            'userid': config['user'], 'password': config['password'],
            'deviceid': '000000000000000', 'sessionid': '0',
        }
        response = requests.get(config['url'], headers=headers, timeout=120)
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError:
            raise ValueError('La respuesta no contiene JSON válido.')
        if isinstance(payload, dict):
            if 'data' not in payload:
                raise ValueError('Falta la clave data; no se ajustará inventario.')
            items = payload['data']
        else:
            items = payload
        if not isinstance(items, list):
            raise ValueError('La API debe responder una lista de productos en data.')
        return items

    @api.model
    def _get_api_items(self, api_record):
        return self._fetch_inventory_http(self._api_request_config(api_record))

    @api.model
    def _string(self, value):
        return str(value).strip() if value is not None else ''

    @api.model
    def _number(self, value, field_name):
        return as_number(value, field_name)

    @api.model
    def _log_value(self, value):
        if value is None or value is False:
            return '(vacío)'
        if isinstance(value, float):
            return '%g' % value
        text = str(value).replace('\r', ' ').replace('\n', ' ')
        return text[:160] + '…' if len(text) > 160 else text

    def _sync_one_product(self, item, code, company, api_record, by_code, trace,
                          matching=None, price_rules=None, price_source_records=None,
                          pending_last_sync=None,
                          warehouse_location_ids=None, preloaded_quant_ids=None):
        notices = []
        product_model = self.env['product.product'].sudo().with_company(company).with_context(active_test=False)
        if matching is None:
            # Seguridad para invocaciones externas sin precarga.
            matching = product_model.search([
                ('default_code', '=', code),
                ('product_tmpl_id.company_id', 'in', [False, company.id]),
            ], limit=2)
        if len(matching) > 1:
            raise ValueError('Uso interno: _sync_one_product requiere una sola variante (el proceso principal itera todas).')
        if matching and not matching.active:
            trace['lines'].append('Producto archivado: se actualizan sus datos sin reactivarlo.')

        # Validar antes de crear el producto para no generar registros inconsistentes.
        values = {}
        name = self._string(item.get('Nombre'))
        if name:
            values['name'] = name
        field_map = {
            'Linea': 'inventory_web_line',
            'Marca': 'inventory_web_brand',
            'formato': 'inventory_web_format',
        }
        for api_field, odoo_field in field_map.items():
            if api_field in item:
                values[odoo_field] = self._string(item.get(api_field))
        for api_field, odoo_field in {
            'mxpallets': 'inventory_web_mxpallets',
            'mxplaca': 'inventory_web_mxplaca',
            'mxcaja': 'inventory_web_mxcaja',
            'Peso': 'weight',
        }.items():
            if api_field in item:
                values[odoo_field] = self._number(item[api_field], api_field)
        # Se conserva el número del CAMPO JSON en la estructura consolidada.
        # De otro modo, usar el mismo API ID para dos precios mezclaría ambos.
        received_prices = (item.get('_inventory_web_price_fields', {})
                           if price_source_records is not None else
                           {field_id: (api_record.id, item[field_name])
                            for field_id, field_name in ((1, 'Precio'), (2, 'Precio_2'))
                            if field_name in item and item[field_name] is not None})
        price_sources_map = price_source_records or {api_record.id: api_record}
        for field_id, (price_api_id, raw_price) in received_prices.items():
            if price_api_id not in price_sources_map:
                raise ValueError('No existe la API de precio %s.' % price_api_id)
            price_field = 'Precio' if field_id == 1 else 'Precio_2'
            amount = self._number(raw_price, price_field)
            if amount < 0:
                raise ValueError('%s negativo recibido en API %s.' % (price_field, price_api_id))
            values['inventory_web_price_%s' % field_id] = amount

        if 'StockTotal' in item:
            values['inventory_web_stock_total'] = self._number(item['StockTotal'], 'StockTotal')
            if values['inventory_web_stock_total'] < 0:
                raise ValueError('StockTotal no puede ser negativo.')
        if 'Peso' in item and 'peso' in self.env['product.template']._fields:
            # Campo personalizado utilizado por el módulo anterior, si está instalado.
            values['peso'] = values['weight']
        values['inventory_web_last_sync'] = fields.Datetime.now()

        is_new = not bool(matching)
        trace['created'] = is_new
        if matching:
            trace['product_id'] = matching.id
            trace['product_tmpl_id'] = matching.product_tmpl_id.id
            prev = matching.product_tmpl_id
            updated_fields = []
            changed_values = {}
            for key, value in values.items():
                if key == 'inventory_web_last_sync':
                    continue
                old = prev[key]
                field_type = prev._fields[key].type
                if field_type in ('char', 'text', 'html'):
                    differs = (old or '') != (value or '')
                elif field_type in ('float', 'monetary'):
                    differs = bool(float_compare(old or 0.0, value or 0.0, precision_digits=6))
                else:
                    differs = old != value
                if differs:
                    changed_values[key] = value
                    updated_fields.append('%s: %s → %s' % (
                        prev._fields[key].string, self._log_value(old), self._log_value(value)))
            if updated_fields:
                trace['changed'] = True
                trace['lines'].append('Datos de producto modificados:')
                trace['lines'].extend('  ' + line for line in updated_fields)
            else:
                trace['lines'].append('Datos de producto: sin cambios (se renovó la fecha de revisión).')
        if is_new:
            if not name:
                raise ValueError('El producto no existe y Nombre está vacío.')
            # Set Precio 1 when creating to avoid a second ORM write;
            # if only Precio 2 exists, retain the old stock_api default 0.0.
            values.update({'default_code': code, 'type': 'consu', 'is_storable': True,
                           'company_id': company.id,
                           'list_price': values.get('inventory_web_price_1', 0.0)})
            tmpl = self.env['product.template'].sudo().with_company(company).create(values)
            product = tmpl.product_variant_id
            trace['product_tmpl_id'] = tmpl.id
            trace['product_id'] = product.id if product else False
            trace['changed'] = True
            trace['lines'].append('Producto creado en Odoo: %s (SKU %s).' % (name, code))
            if not product:
                raise ValueError('No se pudo generar la variante del producto.')
        else:
            product = matching
            tmpl = product.product_tmpl_id
            # Evita reescribir todos los campos de productos sin cambios.
            # La fecha de lectura se actualiza después por lotes.
            if changed_values:
                changed_values['inventory_web_last_sync'] = values['inventory_web_last_sync']
                tmpl.write(changed_values)
            elif pending_last_sync is not None:
                # Se programa SOLO tras concluir con éxito el SKU completo.
                pass
            else:
                tmpl.write({'inventory_web_last_sync': values['inventory_web_last_sync']})

        price_sources = received_prices
        trace['price_events'] = []
        for external_price_id, (source_api_id, raw_price) in price_sources.items():
            source_api = price_sources_map.get(source_api_id)
            if not source_api:
                raise ValueError('No se encontró la API de precio %s.' % source_api_id)
            price_field = 'Precio' if external_price_id == 1 else 'Precio_2'
            price = self._number(raw_price, price_field)
            if price < 0:
                raise ValueError('%s negativo no permitido en API %s.' % (price_field, source_api_id))
            cache = (price_rules or {}).get(source_api_id, {}) if price_source_records else price_rules
            target_pricelist = self._price_list_destination(source_api, external_price_id)
            previous, current, price_changed, price_label = self._sync_price(
                tmpl, target_pricelist, price, company, cached_rules=cache)
            trace['changed'] = trace['changed'] or price_changed
            origin_api_id = item.get('_inventory_web_price_sources', {}).get(external_price_id, source_api_id)
            event = {'api_id': source_api_id, 'origen_api_id': origin_api_id,
                     'campo_json': price_field, 'lista_externa': external_price_id,
                     'label': price_label,
                     'before': previous, 'after': current,
                     'state': 'ACTUALIZADO' if price_changed else 'SIN_CAMBIOS'}
            trace['price_events'].append(event)
            trace['lines'].append('%s (%s; destino API %s; origen API %s) / %s: %s → %s (%s).' % (
                price_field, 'precio público' if external_price_id == 1 else 'precio mayorista',
                source_api_id, origin_api_id, price_label, self._log_value(previous),
                self._log_value(current),
                'actualizado' if price_changed else 'sin cambios'))
        if not price_sources:
            trace['lines'].append('Precio: no recibido en ninguna API, no se modificó.')
        trace['price_event'] = trace['price_events'][0] if trace['price_events'] else None

        if 'StockTotal' in item:
            trace['lines'].append('StockTotal recibido: %s.' %
                                  self._log_value(values['inventory_web_stock_total']))
        else:
            trace['lines'].append('StockTotal: no recibido.')

        stock_changes = 0
        if not product.is_storable:
            notices.append('No se ajustó inventario: el producto no es almacenable.')
            trace['lines'].append('Inventario: omitido, producto no almacenable.')
        elif product.tracking != 'none':
            notices.append('No se ajustó inventario: producto con lotes/series; la API no entrega detalle por lote.')
            trace['lines'].append('Inventario: omitido, seguimiento por lote/serie.')
        else:
            stock_changes, stock_notices = self._sync_warehouses(
                item, product, company, by_code, trace,
                warehouse_location_ids=warehouse_location_ids,
                preloaded_quant_ids=preloaded_quant_ids)
            notices.extend(stock_notices)
            trace['changed'] = trace['changed'] or bool(stock_changes)

        # Asociar producto a las múltiples bodegas que aparecen en el JSON.
        old_ids = set(product.inventory_web_warehouse_ids.ids)
        self._link_product_warehouses(product, item, company, by_code)
        if set(product.inventory_web_warehouse_ids.ids) != old_ids:
            trace['changed'] = True
            trace['lines'].append('Relaciones de bodegas del producto: actualizadas.')
        if not is_new and not changed_values and pending_last_sync is not None:
            pending_last_sync.add(tmpl.id)
        return is_new, stock_changes, notices

    def _link_product_warehouses(self, product, item, company, by_code):
        """Vincula códigos existentes respetando relaciones de otras empresas.

        Si el JSON no tiene bodegas válidas, no borra vínculos previos.
        """
        codes = declared_warehouse_codes(item, by_code)
        if not codes:
            return
        valid_ids = {by_code[code].id for code in codes}
        previous = product.inventory_web_warehouse_ids
        other_company_ids = {wh.id for wh in previous if wh.company_id != company}
        new_ids = other_company_ids | valid_ids
        if set(previous.ids) != new_ids:
            product.write({'inventory_web_warehouse_ids': [(6, 0, sorted(new_ids))]})

    def _sync_price(self, tmpl, pricelist, price, company, cached_rules=None):
        if not pricelist:
            previous = tmpl.list_price
            changed = bool(float_compare(previous, price, precision_digits=6))
            if changed:
                tmpl.write({'list_price': price})
            return previous, price, changed, 'Precio público (list_price)'
        if pricelist.company_id and pricelist.company_id != company:
            raise ValueError('La lista de precios seleccionada pertenece a otra empresa.')
        Item = self.env['product.pricelist.item'].sudo().with_company(company)
        if cached_rules is not None and tmpl.id in cached_rules:
            rules = cached_rules[tmpl.id]
        else:
            rules = Item.search([
                ('pricelist_id', '=', pricelist.id),
                ('applied_on', '=', '1_product'),
                ('product_tmpl_id', '=', tmpl.id),
                ('min_quantity', '=', 0),
            ], limit=2)
        # Hay catálogos que ya contienen varias reglas para la misma
        # plantilla y lista. No bloquear el SKU: al recibir precio único
        # por producto se actualizan todas esas reglas (mínimo cero).
        old_prices = rules.mapped('fixed_price') if rules else []
        previous = (old_prices[0] if len(old_prices) == 1 else
                    (old_prices if old_prices else None))
        changed = not rules or any(
            rule.compute_price != 'fixed' or
            bool(float_compare(rule.fixed_price, price, precision_digits=6))
            for rule in rules)
        if rules:
            if len(rules) > 1:
                _logger.warning('[INV_WEB_SYNC] PRECIO_REGLAS_DUPLICADAS '
                                'producto_tmpl_id=%s lista_id=%s cantidad=%s; '
                                'se aplica Precio a todas las reglas.',
                                tmpl.id, pricelist.id, len(rules))
            if changed:
                rules.write({'compute_price': 'fixed', 'fixed_price': price})
        else:
            new_rule = Item.create({
                'pricelist_id': pricelist.id,
                'applied_on': '1_product',
                'product_tmpl_id': tmpl.id,
                'min_quantity': 0,
                'compute_price': 'fixed',
                'fixed_price': price,
            })
            if cached_rules is not None:
                # Otras variantes de la misma plantilla, en el mismo lote,
                # deben reutilizar esta regla y no crear duplicados.
                cached_rules[tmpl.id] = new_rule
        return previous, price, changed, 'Lista de precios %s' % pricelist.display_name

    @api.model
    def _warehouse_locations(self, by_code):
        """Ubicaciones de cada almacén, consultadas una vez por API.

        Si dos almacenes comparten alguna ubicación interna se deshabilita la
        precarga de quants para mantener la lógica original segura.
        """
        Location = self.env['stock.location'].sudo()
        by_wh = {}
        seen = set()
        overlap = False
        for code, wh in by_code.items():
            if not wh.lot_stock_id:
                continue
            location_ids = set(Location.search([
                ('id', 'child_of', wh.lot_stock_id.id),
                ('usage', '=', 'internal'),
            ]).ids)
            if seen.intersection(location_ids):
                overlap = True
            seen.update(location_ids)
            by_wh[code] = location_ids
        if overlap:
            _logger.warning('[INV_WEB_SYNC] UBICACIONES_COMPARTIDAS: se usa el '
                            'método tradicional por bodega para mayor seguridad.')
            return None
        return by_wh

    @api.model
    def _wh_stock_already_correct(self, quants, product, warehouse, target):
        """Lectura sin escrituras para omitir savepoints en bodegas sin cambios.

        Un stock reservado, con lotes, paquetes o propietarios NUNCA se
        considera apto para vía rápida: lo valida el ajuste original.
        """
        rounding = product.uom_id.rounding
        if any(q.lot_id or q.package_id or q.owner_id or
               float_compare(q.reserved_quantity, 0, precision_rounding=rounding) > 0
               for q in quants):
            return None
        if not float_compare(target, 0, precision_rounding=rounding):
            if all(not float_compare(q.quantity, 0, precision_rounding=rounding)
                   for q in quants):
                return 0.0
            return None
        before = sum(quants.mapped('quantity'))
        if float_compare(before, target, precision_rounding=rounding):
            return None
        root = warehouse.lot_stock_id.id
        children_total = sum(q.quantity for q in quants if q.location_id.id != root)
        expected_root = target - children_total
        if float_compare(expected_root, 0, precision_rounding=rounding) < 0:
            return None
        root_quants = quants.filtered(lambda q: q.location_id.id == root)
        if len(root_quants) > 1:
            return None
        actual_root = sum(root_quants.mapped('quantity'))
        if not float_compare(actual_root, expected_root, precision_rounding=rounding):
            return before
        return None

    def _sync_warehouses(self, item, product, company, by_code, trace,
                         warehouse_location_ids=None, preloaded_quant_ids=None):
        targets, notices = stock_targets(item, by_code)
        count = 0
        # Única lectura por SKU: los almacenes con códigos distintos deben tener
        # árboles de ubicaciones disjuntos (ver _warehouse_locations).
        by_location_quants = None
        if warehouse_location_ids is not None:
            location_ids = set().union(*(warehouse_location_ids.get(code, set())
                                        for code in targets)) if targets else set()
            Quant = self.env['stock.quant'].sudo().with_company(company)
            # Para productos existentes de la precarga, reconstruir el recordset
            # por ID evita otra búsqueda SQL. Para productos nuevos o un SKU
            # repetido y ya ajustado, consultar quants frescos.
            if preloaded_quant_ids is not None:
                quants = Quant.browse(preloaded_quant_ids)
            else:
                quants = Quant.search([
                    ('company_id', '=', company.id),
                    ('product_id', '=', product.id),
                    ('location_id', 'in', list(location_ids)),
                ]) if location_ids else Quant.browse()
            by_location_quants = {}
            for quant in quants:
                by_location_quants.setdefault(quant.location_id.id, []).append(quant.id)
        trace['lines'].append('Bodegas incluidas en esta sincronización: %s.' % len(targets))
        for code, new_qty in targets.items():
            wh = by_code.get(code)
            event = {
                'code': code, 'target': new_qty, 'before': None, 'after': None,
                'warehouse_id': wh.id if wh else False,
                'warehouse_name': wh.display_name if wh else '',
                'state': 'OMITIDA', 'reason': '',
            }
            trace.setdefault('warehouse_events', []).append(event)
            if not wh:
                event['reason'] = 'Almacén no encontrado por stock.warehouse.code en la empresa'
                notices.append('Bodega %s inexistente en la empresa %s; no se creó.' % (code, company.name))
                trace['lines'].append('Bodega %s: NO EXISTE (solicitado %s).' %
                                      (code, self._log_value(new_qty)))
                continue
            if not wh.lot_stock_id:
                event['reason'] = 'Almacén sin ubicación principal de stock'
                notices.append('Bodega %s sin ubicación principal de stock; se omitió.' % code)
                trace['lines'].append('Bodega %s: sin ubicación de stock, omitida.' % code)
                continue
            try:
                if by_location_quants is not None:
                    Quant = self.env['stock.quant'].sudo().with_company(company)
                    ids = [qid for loc_id in warehouse_location_ids.get(code, set())
                           for qid in by_location_quants.get(loc_id, [])]
                    selected = Quant.browse(ids)
                    already = self._wh_stock_already_correct(selected, product, wh, new_qty)
                    if already is not None:
                        # Sin savepoint ni acción de inventario: no hay cambio.
                        changed, before, after = False, already, already
                    else:
                        with self.env.cr.savepoint():
                            changed, before, after = self._set_wh_stock(
                                product, wh, new_qty, company, quants=selected)
                else:
                    with self.env.cr.savepoint():
                        changed, before, after = self._set_wh_stock(product, wh, new_qty, company)
                event.update({'before': before, 'after': after,
                              'state': 'AJUSTADA' if changed else 'SIN_CAMBIOS'})
                if changed:
                    count += 1
                trace['lines'].append('Bodega %s (%s): %s → %s (API %s), %s.' % (
                    code, wh.display_name, self._log_value(before),
                    self._log_value(after), self._log_value(new_qty),
                    'AJUSTADA' if changed else 'SIN CAMBIOS'))
            except (UserError, ValidationError, ValueError) as exc:
                event['reason'] = str(exc)
                notices.append('No se pudo ajustar %s: %s' % (code, exc))
                trace['lines'].append('Bodega %s: NO APLICADO (API %s). Motivo: %s' %
                                      (code, self._log_value(new_qty), exc))
            except Exception as exc:
                _logger.exception('[INV_WEB_SYNC] BODEGA_ERROR sku=%s bodega=%s', product.default_code, code)
                event['state'] = 'ERROR'
                event['reason'] = str(exc)
                notices.append('Error inesperado al ajustar %s: %s' % (code, exc))
                trace['lines'].append('Bodega %s: ERROR (API %s). Motivo: %s' %
                                      (code, self._log_value(new_qty), exc))
        return count, notices

    def _set_wh_stock(self, product, warehouse, target, company, quants=None):
        """Ajuste contable de inventario: nunca escribir directamente quant.quantity.

        Respeta ubicaciones hijas con stock: al aumentar el objetivo ajusta la
        ubicación principal; si el objetivo es menor que las existencias en las
        ubicaciones hijas, rechaza el ajuste ambiguo. Para cero, todas las
        ubicaciones internas hijas de la bodega se ajustan a cero.
        """
        if product.tracking != 'none':
            raise ValueError('Requiere información de lote/serie.')
        root = warehouse.lot_stock_id
        Quant = self.env['stock.quant'].sudo().with_company(company).with_context(inventory_mode=True)
        if quants is None:
            quants = Quant.search([
                ('company_id', '=', company.id),
                ('product_id', '=', product.id),
                ('location_id', 'child_of', root.id),
                ('location_id.usage', '=', 'internal'),
            ])
        # Stock individual en paquetes, propietarios o lotes no puede reconciliarse
        # correctamente a partir de una cantidad agregada sin más desglose.
        complex_q = quants.filtered(lambda q: q.lot_id or q.package_id or q.owner_id)
        if complex_q and any(float_compare(q.quantity, 0, precision_rounding=product.uom_id.rounding)
                             for q in complex_q):
            raise ValueError('Existen existencias con lote, paquete o propietario; ajuste manual requerido.')
        if any(float_compare(q.reserved_quantity, 0, precision_rounding=product.uom_id.rounding) > 0
               for q in quants):
            raise ValueError('Hay stock reservado en la bodega; se evita alterar reservas activas.')

        before = sum(quants.mapped('quantity'))
        simple = quants - complex_q
        rounding = product.uom_id.rounding
        if not float_compare(target, 0, precision_rounding=rounding):
            changed = False
            for quant in simple:
                if float_compare(quant.quantity, 0, precision_rounding=rounding):
                    self._apply_count(quant, 0.0)
                    changed = True
            after = self._current_wh_stock(product, warehouse, company) if changed else before
            if float_compare(after, target, precision_rounding=rounding):
                raise UserError(_('Odoo no confirmó el stock esperado (%s); stock actual: %s.') %
                                (target, after))
            return changed, before, after

        root_quants = simple.filtered(lambda q: q.location_id.id == root.id)
        if len(root_quants) > 1:
            raise ValueError('Hay varias existencias raíz para el mismo producto; ajuste manual requerido.')
        child_total = sum(simple.filtered(lambda q: q.location_id.id != root.id).mapped('quantity'))
        root_target = target - child_total
        if float_compare(root_target, 0, precision_rounding=rounding) < 0:
            raise ValueError('Las ubicaciones internas hijas suman más que el stock de API; '
                             'no se redistribuye stock entre ubicaciones sin detalle.')
        current_root = sum(root_quants.mapped('quantity'))
        if not float_compare(current_root, root_target, precision_rounding=rounding):
            return False, before, before
        if root_quants:
            self._apply_count(root_quants, root_target)
        else:
            quant = Quant.create({
                'product_id': product.id,
                'location_id': root.id,
                'inventory_quantity': root_target,
            })
            self._confirm_inventory_adjustment(quant)
        after = self._current_wh_stock(product, warehouse, company)
        if float_compare(after, target, precision_rounding=rounding):
            raise UserError(_('Odoo no confirmó el stock esperado (%s); stock actual: %s.') %
                            (target, after))
        return True, before, after

    @api.model
    def _current_wh_stock(self, product, warehouse, company):
        Quant = self.env['stock.quant'].sudo().with_company(company)
        # Invalidar para obtener el resultado del ajuste y no una cantidad anterior en caché.
        Quant.invalidate_model(['quantity'])
        quants = Quant.search([
            ('company_id', '=', company.id),
            ('product_id', '=', product.id),
            ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ('location_id.usage', '=', 'internal'),
        ])
        return sum(quants.mapped('quantity'))

    @api.model
    def _apply_count(self, quant, value):
        quant.write({'inventory_quantity': value})
        self._confirm_inventory_adjustment(quant)

    @api.model
    def _confirm_inventory_adjustment(self, quant):
        action = quant.action_apply_inventory()
        # Una confirmación o conflicto pendiente significa que aún NO se aplicó.
        # Evita marcar como sincronizado un stock que permanece sin cambios.
        if isinstance(action, dict):
            raise UserError(_('Odoo requiere confirmación manual del ajuste de inventario.'))

