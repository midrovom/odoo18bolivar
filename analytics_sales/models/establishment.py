# -*- coding: utf-8 -*-
from html import escape
from markupsafe import Markup

from .goal_report import seller_identity
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AnalyticsSalesEstablishment(models.Model):
    _name = 'analytics.sales.establishment'
    _description = 'Establecimiento que agrupa locales nlocal (Analytics Sales)'
    _order = 'name'

    name = fields.Char(string='Establecimiento', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True,
                                 default=lambda self: self.env.company, index=True, ondelete='cascade')
    local_ids = fields.Many2many('analytics.sales.local', 'analytics_sales_establishment_local_rel',
                                 'establishment_id', 'local_id', string='Locales',
                                 domain="[('company_id', '=', company_id)]",
                                 help='Seleccione los locales ERP que pertenecen al establecimiento.')
    warehouse_record_ids = fields.One2many(
        'analytics.sales.warehouse', 'establishment_id', string='Bodegas relacionadas',
        groups='analytics_sales.group_analytics_sales_admin')
    warehouse_ids = fields.Many2many(
        'analytics.sales.warehouse', string='Bodegas',
        compute='_compute_warehouse_ids', inverse='_inverse_warehouse_ids',
        compute_sudo=False, readonly=False,
        domain="[('company_id', '=', company_id), '|', ('establishment_id', '=', False), ('establishment_id', '=', id)]",
        groups='analytics_sales.group_analytics_sales_admin',
        help='Seleccione las bodegas de la API que pertenecen a este establecimiento.')
    seller_count = fields.Integer(
        string='Vendedores', compute='_compute_seller_roster', readonly=True,
        groups='analytics_sales.group_analytics_sales_admin')
    seller_report = fields.Html(
        string='Vendedores de los locales', compute='_compute_seller_roster',
        readonly=True, sanitize=False,
        groups='analytics_sales.group_analytics_sales_admin',
        help='Vendedores identificados automáticamente en los movimientos FA/DE vigentes '
             'de los locales asociados a este establecimiento.')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Observaciones')

    _sql_constraints = [
        ('unique_establishment_per_company', 'unique(company_id, name)',
         'Ya existe un establecimiento con este nombre en la compañía.'),
    ]

    @api.depends('warehouse_record_ids')
    def _compute_warehouse_ids(self):
        for rec in self:
            rec.warehouse_ids = rec.warehouse_record_ids

    def _inverse_warehouse_ids(self):
        warehouse_model = self.env['analytics.sales.warehouse']
        # Guardar las selecciones antes de que una escritura de la relación
        # inversa invalide el campo calculado de otro registro.
        selections = [(rec, rec.warehouse_ids) for rec in self]
        for rec, selected in selections:
            if not self.env.su:
                self.env['analytics.sales.security'].check_admin()
            selected.check_access('read')
            current = warehouse_model.search([('establishment_id', '=', rec.id)])
            # Serializar cambios concurrentes de la misma bodega.
            ids = sorted((current | selected).ids)
            if ids:
                self.env.cr.execute('SELECT id FROM analytics_sales_warehouse WHERE id IN %s ORDER BY id FOR UPDATE', (tuple(ids),))
                (current | selected).invalidate_recordset(['establishment_id'])
            if any(w.company_id != rec.company_id for w in selected):
                raise ValidationError(_('Todas las bodegas deben pertenecer a la misma compañía del establecimiento.'))
            duplicates = selected.filtered(lambda w: w.establishment_id and w.establishment_id != rec)
            if duplicates:
                raise ValidationError(_('Las bodegas %s ya pertenecen a otro establecimiento.') % ', '.join(duplicates.mapped('code')))
            removed = (current - selected).filtered(lambda w: w.establishment_id == rec)
            if removed:
                removed.write({'establishment_id': False})
            added = selected.filtered(lambda w: w.establishment_id != rec)
            if added:
                added.write({'establishment_id': rec.id})

    @api.constrains('local_ids', 'company_id')
    def _check_local_assignments(self):
        for rec in self:
            if any(local.company_id != rec.company_id for local in rec.local_ids):
                raise ValidationError(_('Todos los locales deben pertenecer a la misma compañía del establecimiento.'))
            if rec.local_ids:
                others = self.sudo().search([
                    ('id', '!=', rec.id), ('local_ids', 'in', rec.local_ids.ids),
                ])
                if others:
                    existing_ids = set(others.mapped('local_ids').ids)
                    duplicates = rec.local_ids.filtered(lambda local: local.id in existing_ids)
                    raise ValidationError(_(
                        'Los locales %s ya pertenecen a otro establecimiento. Cada nlocal solo puede estar en uno.'
                    ) % ', '.join(duplicates.mapped('name')))

    @api.depends('company_id', 'local_ids')
    def _compute_seller_roster(self):
        """Listado vivo de los vendedores de los nlocal del establecimiento.

        No crea fichas maestras ni modifica movimientos. Igual que el dashboard,
        si existe información de API para la compañía, prioriza esa fuente
        frente a Excel y no suma dos veces la misma venta.
        """
        move_model = self.env['analytics.sales.move'].sudo()
        for rec in self:
            roster = {}
            locals_by_id = {local.id: local.name for local in rec.local_ids}
            if rec.company_id and locals_by_id:
                api_available = bool(move_model.with_context(active_test=False).search_count([
                    ('company_id', '=', rec.company_id.id), ('source_kind', '=', 'api')]))
                source_kind = 'api' if api_available else 'historico'
                rows = move_model.read_group([
                    ('company_id', '=', rec.company_id.id),
                    ('source_kind', '=', source_kind),
                    ('document_type', 'in', ['FA', 'DE']),
                    ('local_id', 'in', list(locals_by_id)),
                ], ['local_id', 'seller_code', 'seller'],
                    ['local_id', 'seller_code', 'seller'], lazy=False)
                for row in rows:
                    local_value = row.get('local_id')
                    loc_id = local_value[0] if isinstance(local_value, (tuple, list)) else local_value
                    if loc_id not in locals_by_id:
                        continue
                    code = str(row.get('seller_code') or '').strip()
                    name = str(row.get('seller') or '').strip()
                    key = seller_identity(code, name)
                    if key is None:
                        continue
                    person = roster.setdefault(key, {
                        'name': name or code, 'code': code, 'local_ids': set()})
                    if not person['name'] and name:
                        person['name'] = name
                    person['local_ids'].add(loc_id)
            rec.seller_count = len(roster)
            # Un vendedor aparece UNA sola vez por establecimiento. Los locales
            # en los que participa se listan juntos; no se crean filas repetidas
            # por local y no se modifica la identidad ni el conteo del vendedor.
            pieces = [
                '<div class="as-establishment-sellers" '
                'style="display:block;width:100%;max-width:100%;min-width:0;'
                'max-height:500px;overflow-x:auto;overflow-y:auto">',
                '<table class="table table-sm table-striped table-bordered" '
                'style="width:100%;min-width:790px;table-layout:fixed;'
                'border-collapse:collapse;white-space:normal">',
                '<colgroup><col style="width:36%"/><col style="width:17%"/>'
                '<col style="width:47%"/></colgroup>',
                '<thead><tr><th>Vendedor</th><th>Código</th><th>Locales</th>'
                '</tr></thead><tbody>',
            ]
            for person in sorted(roster.values(), key=lambda item: (
                    item['name'].casefold(), item['code'])):
                local_labels = []
                for local_id in sorted(person['local_ids'], key=lambda lid: (
                        locals_by_id[lid].casefold(), lid)):
                    label = locals_by_id[local_id]
                    local_labels.append(label[2:].lstrip()
                                        if label[:2].lower() == 'c/' else label)
                pieces.append(
                    '<tr><td style="white-space:normal;overflow-wrap:break-word">%s</td>'
                    '<td style="white-space:normal;overflow-wrap:break-word">%s</td>'
                    '<td style="white-space:normal;overflow-wrap:break-word">%s</td>'
                    '</tr>' % (escape(person['name']), escape(person['code']),
                               escape(', '.join(local_labels))))
            if not roster:
                message = ('Seleccione los locales del establecimiento.' if not locals_by_id
                           else 'No hay vendedores identificados en estos locales.')
                pieces.append('<tr><td colspan="3">%s</td></tr>' % escape(message))
            pieces.append('</tbody></table></div>')
            rec.seller_report = Markup(''.join(pieces))
