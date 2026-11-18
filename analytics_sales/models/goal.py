# -*- coding: utf-8 -*-
from datetime import date
from decimal import Decimal, InvalidOperation
import re
from html import escape
from markupsafe import Markup

from .goal_report import build_monthly_goals, month_from_read_group
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AnalyticsSalesGoal(models.Model):
    _name = 'analytics.sales.goal'
    _description = 'Metas y ventas netas reales anuales (Analytics Sales)'
    _order = 'year desc, establishment_id, id'

    name = fields.Char(string='Descripción', required=True, default='Meta anual')
    company_id = fields.Many2one('res.company', string='Compañía', required=True,
                                 default=lambda self: self.env.company, index=True, ondelete='cascade')
    year = fields.Integer(string='Año', required=True, index=True, default=lambda self: date.today().year)
    establishment_id = fields.Many2one('analytics.sales.establishment', string='Establecimiento',
                                       ondelete='restrict', index=True,
                                       domain="[('company_id', '=', company_id)]",
                                       help='Deje vacío para calcular las ventas anuales de toda la compañía.')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    # Legacy value retained in PostgreSQL to avoid losing old user data.
    # Not displayed in the UI and no longer used to calculate distributions.
    target_amount = fields.Monetary(
        string='Objetivo anual anterior (legado)', currency_field='currency_id',
        required=True, default=0.0,
        help='Dato histórico de versiones anteriores. No participa en cálculos ni se muestra en Metas.')

    # Importes reales NO almacenados: cada lectura vuelve a sumar las líneas
    # vigentes, incluyendo cambios posteriores de ventas_anuales / ventas_mensuales.
    annual_net_sales = fields.Monetary(
        string='Meta anual de ventas netas', currency_field='currency_id',
        compute='_compute_annual_sales', readonly=True,
        help='Ventas netas reales del año elegido: total FA menos total DE, '
             'sumado para todos los nlocal del establecimiento seleccionado. '
             'Si no se selecciona establecimiento, comprende la compañía.')
    annual_fa_sales = fields.Monetary(
        string='Facturado FA del año', currency_field='currency_id',
        compute='_compute_annual_sales', readonly=True)
    annual_de_sales = fields.Monetary(
        string='Devuelto DE del año', currency_field='currency_id',
        compute='_compute_annual_sales', readonly=True)
    local_count = fields.Integer(
        string='Locales incluidos', compute='_compute_annual_sales', readonly=True)
    # Informes de lectura: se recalculan contra los movimientos vigentes, no son
    # metas/saldos persistidos. Únicamente puede verlos Analytics Sales Admin.
    distribution_amount = fields.Monetary(
        string='Base anual a distribuir', currency_field='currency_id',
        compute='_compute_monthly_distribution', readonly=True,
        groups='analytics_sales.group_analytics_sales_admin',
        help='Distribuye las ventas netas reales del año del establecimiento seleccionado como base referencial.')
    distribution_method = fields.Char(
        string='Origen de la distribución', compute='_compute_monthly_distribution',
        readonly=True, groups='analytics_sales.group_analytics_sales_admin')
    distribution_unassigned = fields.Monetary(
        string='Meta pendiente de asignar a vendedores', currency_field='currency_id',
        compute='_compute_monthly_distribution', readonly=True,
        groups='analytics_sales.group_analytics_sales_admin')
    annual_establishment_report = fields.Html(
        string='Resumen anual por establecimiento', compute='_compute_monthly_distribution',
        readonly=True, sanitize=False, groups='analytics_sales.group_analytics_sales_admin')
    monthly_local_report = fields.Html(
        string='Distribución mensual por establecimiento', compute='_compute_monthly_distribution',
        readonly=True, sanitize=False, groups='analytics_sales.group_analytics_sales_admin',
        help='Totales mensuales de los locales del establecimiento, en una sola fila por mes.')
    monthly_seller_report = fields.Html(
        string='Distribución automática mensual por vendedor', compute='_compute_monthly_distribution',
        readonly=True, sanitize=False, groups='analytics_sales.group_analytics_sales_admin',
        help='Distribución mensual equitativa por vendedor único del establecimiento; sin duplicar cuotas por local.')

    # Metas ingresadas por mes. Se guardan en la ficha y se mantienen al
    # sincronizar nuevamente las ventas de las APIs.
    # Un mes sin objetivo queda en cero: nunca se infiere de las ventas.
    monthly_goal_01 = fields.Monetary(string='Enero', currency_field='currency_id', default=0.0)
    monthly_goal_02 = fields.Monetary(string='Febrero', currency_field='currency_id', default=0.0)
    monthly_goal_03 = fields.Monetary(string='Marzo', currency_field='currency_id', default=0.0)
    monthly_goal_04 = fields.Monetary(string='Abril', currency_field='currency_id', default=0.0)
    monthly_goal_05 = fields.Monetary(string='Mayo', currency_field='currency_id', default=0.0)
    monthly_goal_06 = fields.Monetary(string='Junio', currency_field='currency_id', default=0.0)
    monthly_goal_07 = fields.Monetary(string='Julio', currency_field='currency_id', default=0.0)
    monthly_goal_08 = fields.Monetary(string='Agosto', currency_field='currency_id', default=0.0)
    monthly_goal_09 = fields.Monetary(string='Septiembre', currency_field='currency_id', default=0.0)
    monthly_goal_10 = fields.Monetary(string='Octubre', currency_field='currency_id', default=0.0)
    monthly_goal_11 = fields.Monetary(string='Noviembre', currency_field='currency_id', default=0.0)
    monthly_goal_12 = fields.Monetary(string='Diciembre', currency_field='currency_id', default=0.0)

    monthly_line_ids = fields.One2many(
        'analytics.sales.goal.month.line', 'goal_id', string='Metas mensuales')
    total_meta = fields.Monetary(
        string='Total meta', currency_field='currency_id',
        compute='_compute_total_meta', readonly=True,
        help='Suma de las 12 metas mensuales asignadas para el año de esta ficha. '
             'No incluye ventas reales ni duplica importes por vendedor.')

    @api.depends('monthly_line_ids.target_amount', 'currency_id', 'currency_id.rounding')
    def _compute_total_meta(self):
        for rec in self:
            amount = sum(rec.monthly_line_ids.mapped('target_amount'))
            currency = rec.currency_id
            rec.total_meta = currency.round(amount) if currency else round(amount, 2)

    bulk_monthly_target = fields.Char(
        string='Meta para todos los meses', copy=False,
        help='Escriba el importe y pulse Aplicar para asignarlo por igual a enero-diciembre. '
             'El campo se vacía después de aplicar; cada mes podrá seguir editándose individualmente.')

    def action_apply_monthly_target(self):
        """Only overwrites the twelve monthly targets after an explicit button click.

        Char instead of Monetary makes the input genuinely empty after applying;
        Odoo otherwise displays $0.00 for a cleared monetary input.
        """
        self.ensure_one()
        raw = (self.bulk_monthly_target or '').strip()
        if not raw:
            raise ValidationError(_('Ingrese un valor antes de pulsar Aplicar.'))
        raw = raw.replace('$', '').replace('\u00a0', '').replace(' ', '')
        # Accept 1000, 1000.50, 1000,50, 1.000,50 and 1,000.50.
        if re.fullmatch(r'\d{1,3}([.,]\d{3})+', raw):
            normalized = raw.replace(',', '').replace('.', '')
        elif '.' in raw and ',' in raw:
            decimal_sep = '.' if raw.rfind('.') > raw.rfind(',') else ','
            thousands_sep = ',' if decimal_sep == '.' else '.'
            normalized = raw.replace(thousands_sep, '').replace(decimal_sep, '.')
        else:
            normalized = raw.replace(',', '.')
        try:
            amount = Decimal(normalized)
        except InvalidOperation:
            raise ValidationError(_('La meta debe ser un importe numérico válido.'))
        if not amount.is_finite() or amount < 0:
            raise ValidationError(_('La meta mensual debe ser un importe válido no negativo.'))
        currency = self.currency_id
        amount = currency.round(float(amount)) if currency else round(float(amount), 2)
        self._ensure_month_rows()
        self.monthly_line_ids.write({'target_amount': amount})
        # Clear the only bulk input; do not reset the twelve editable rows.
        self.write({'bulk_monthly_target': False})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    monthly_table_heading = fields.Html(
        string='Encabezado mensual', compute='_compute_monthly_table_heading',
        readonly=True, sanitize=False)

    @api.depends('year', 'establishment_id', 'establishment_id.name', 'company_id')
    def _compute_monthly_table_heading(self):
        for rec in self:
            if rec.establishment_id:
                label = 'Establecimiento: %s' % (rec.establishment_id.name or '')
            else:
                label = 'Compañía: %s' % (rec.company_id.name or '')
            rec.monthly_table_heading = Markup(
                '<div style="background:#cce7e7;padding:8px 10px;font-weight:600;'
                'margin-top:8px">%s — Año %s</div>' % (
                    escape(label), escape(str(rec.year or ''))))

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'monthly_line_ids' in fields_list and not values.get('monthly_line_ids'):
            values['monthly_line_ids'] = [
                (0, 0, {'month': '%02d' % m, 'target_amount': 0.0})
                for m in range(1, 13)
            ]
        return values

    def _ensure_month_rows(self):
        '''Create only missing rows, preserving previous manually entered values.

        The 12 legacy monthly_goal_XX columns are retained for old data but are
        no longer consulted by the report after this one-time migration.
        '''
        line_model = self.env['analytics.sales.goal.month.line']
        for rec in self:
            present = set(rec.monthly_line_ids.mapped('month'))
            missing = [m for m in range(1, 13) if '%02d' % m not in present]
            if missing:
                line_model.create([{
                    'goal_id': rec.id, 'month': '%02d' % m,
                    'target_amount': rec['monthly_goal_%02d' % m] or 0.0,
                } for m in missing])

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_month_rows()
        return records

    @api.model
    def _initialize_monthly_lines(self):
        '''Idempotent backfill called by XML during install AND upgrade.'''
        self.sudo().with_context(active_test=False).search([])._ensure_month_rows()
        return True

    active = fields.Boolean(default=True)
    notes = fields.Text(string='Observaciones')

    @api.depends('year', 'company_id', 'establishment_id',
                 'establishment_id.local_ids')
    def _compute_annual_sales(self):
        """Suma FA-DE del año/compañía/nlocal, con la misma prioridad de origen del dashboard.

        Sin `store=True`: no persistimos un acumulado que se desactualizaría
        cuando una API corrige importes, agrega movimientos o anula una línea.
        Se recalcula al leer la vista, o al cambiar año/establecimiento.
        """
        move_model = self.env['analytics.sales.move'].sudo()
        for rec in self:
            fa = de = 0.0
            local_ids = rec.establishment_id.local_ids.ids if rec.establishment_id else None
            rec.local_count = len(local_ids) if local_ids is not None else 0

            if rec.company_id and 2000 <= rec.year <= 2100 and (local_ids is None or local_ids):
                # Una API cargada tiene prioridad sobre Excel para no contar
                # los mismos movimientos dos veces (igual que get_dashboard).
                has_api = bool(move_model.with_context(active_test=False).search_count([
                    ('company_id', '=', rec.company_id.id),
                    ('source_kind', '=', 'api'),
                ]))
                source = 'api' if has_api else 'historico'
                domain = [
                    ('company_id', '=', rec.company_id.id),
                    ('source_kind', '=', source),
                    ('document_type', 'in', ['FA', 'DE']),
                    ('date', '>=', '%04d-01-01' % rec.year),
                    ('date', '<=', '%04d-12-31' % rec.year),
                ]
                if local_ids is not None:
                    domain.append(('local_id', 'in', local_ids))
                for row in move_model.read_group(
                        domain, ['document_type', 'total_net:sum'],
                        ['document_type'], lazy=False):
                    if row['document_type'] == 'FA':
                        fa += row['total_net'] or 0.0
                    elif row['document_type'] == 'DE':
                        de += row['total_net'] or 0.0

            currency = rec.currency_id
            fa = currency.round(fa) if currency else round(fa, 2)
            de = currency.round(de) if currency else round(de, 2)
            net = currency.round(fa - de) if currency else round(fa - de, 2)
            rec.annual_fa_sales = fa
            rec.annual_de_sales = de
            rec.annual_net_sales = net

    @api.constrains('year', 'target_amount', 'company_id', 'establishment_id',
                 'monthly_goal_01', 'monthly_goal_02', 'monthly_goal_03', 'monthly_goal_04', 'monthly_goal_05', 'monthly_goal_06',
                 'monthly_goal_07', 'monthly_goal_08', 'monthly_goal_09', 'monthly_goal_10', 'monthly_goal_11', 'monthly_goal_12')
    def _check_goal(self):
        for rec in self:
            if not (2000 <= rec.year <= 2100):
                raise ValidationError(_('El año de la meta debe estar entre 2000 y 2100.'))
            if rec.target_amount < 0:
                raise ValidationError(_('El objetivo anual no puede ser negativo.'))
            if any((rec['monthly_goal_%02d' % month] or 0.0) < 0 for month in range(1, 13)):
                raise ValidationError(_('Las metas mensuales no pueden ser negativas.'))
            if rec.establishment_id and rec.establishment_id.company_id != rec.company_id:
                raise ValidationError(_('La meta y su establecimiento deben pertenecer a la misma compañía.'))
            # PostgreSQL UNIQUE permite varios NULL; comprobar explícitamente también metas generales.
            duplicate = self.sudo().with_context(active_test=False).search_count([
                ('id', '!=', rec.id), ('company_id', '=', rec.company_id.id),
                ('year', '=', rec.year),
                ('establishment_id', '=', rec.establishment_id.id if rec.establishment_id else False),
            ])
            if duplicate:
                raise ValidationError(_('Ya hay una meta para ese año y establecimiento (o para toda la compañía).'))

    @staticmethod
    def _report_money(amount, currency):
        symbol = escape((currency.symbol or '$') if currency else '$')
        value = float(amount or 0.0)
        # Representación legible Ecuador: miles con punto, decimales con coma.
        val = ('{:,.2f}'.format(value)).replace(',', '~').replace('.', ',').replace('~', '.')
        return '%s %s' % (symbol, val)

    @staticmethod
    def _report_percent(actual, cents):
        return ('%.1f %%' % (100.0 * float(actual or 0) / (cents / 100.0))) if cents > 0 else '—'

    def _grouped_seller_sales(self, local_ids):
        """One SQL read_group: source priority, year, company, local, month and seller."""
        self.ensure_one()
        if not local_ids or not (2000 <= self.year <= 2100):
            return []
        moves = self.env['analytics.sales.move'].sudo()
        has_api = bool(moves.with_context(active_test=False).search_count([
            ('company_id', '=', self.company_id.id), ('source_kind', '=', 'api'),
        ]))
        source = 'api' if has_api else 'historico'
        rows = moves.read_group([
            ('company_id', '=', self.company_id.id),
            ('source_kind', '=', source),
            ('document_type', 'in', ['FA', 'DE']),
            ('date', '>=', '%04d-01-01' % self.year),
            ('date', '<=', '%04d-12-31' % self.year),
            ('local_id', 'in', local_ids),
        ], ['total_net:sum', 'quantity:sum'],
            ['date:month', 'local_id', 'seller_code', 'seller', 'document_type'],
            lazy=False)
        result = []
        for row in rows:
            month = month_from_read_group(row)
            local_ref = row.get('local_id')
            local_id = local_ref[0] if isinstance(local_ref, (tuple, list)) else local_ref
            if month not in range(1, 13) or not local_id:
                continue
            result.append({
                'month': month, 'local_id': local_id,
                'seller': row.get('seller') or '',
                'seller_code': row.get('seller_code') or '',
                'document_type': row.get('document_type'),
                'total_net': row.get('total_net', 0.0) or 0.0,
                'quantity': row.get('quantity', 0.0) or 0.0,
            })
        return result

    @staticmethod
    def _report_share(percentage):
        return ('%.2f %%' % float(percentage or 0)).replace('.', ',')

    def _html_annual_establishments(self, groups):
        """Informe anual separado por establecimiento, incluso para meta de compañía."""
        self.ensure_one()
        money = self._report_money
        pieces = [
            '<div class="as-goal-report" style="display:block;width:100%;max-width:100%;max-height:540px;overflow-x:auto;overflow-y:auto">',
            '<table class="table table-sm table-striped table-bordered" style="width:1045px;min-width:1045px;table-layout:fixed;white-space:normal;overflow-wrap:anywhere;border-collapse:collapse">',
            '<colgroup><col style="width:220px"/><col style="width:90px"/><col style="width:105px"/>'
            '<col style="width:150px"/><col style="width:150px"/><col style="width:160px"/>'
            '<col style="width:170px"/></colgroup>',
            '<thead><tr><th>Establecimiento</th><th>Locales</th><th>Vendedores</th>',
            '<th>Facturado FA</th><th>Devuelto DE</th><th>Ventas netas anuales</th>',
            '<th>Meta anual distribuida</th></tr></thead><tbody>',
        ]
        fa_sum = de_sum = base_sum = 0.0
        local_total = seller_total = 0
        for group in groups:
            bd = group['breakdown']
            fa = sum(m['fa'] for m in bd['months'])
            de = sum(m['de'] for m in bd['months'])
            base = bd['annual_goal_cents'] / 100.0
            fa_sum += fa
            de_sum += de
            base_sum += base
            local_total += group['local_count']
            seller_total += bd['seller_count']
            pieces.append('<tr><th>%s</th><td>%s</td><td>%s</td>' % (
                escape(group['name']), group['local_count'], bd['seller_count']))
            for amount in (fa, de, fa - de, base):
                pieces.append('<td>%s</td>' % money(amount, self.currency_id))
            pieces.append('</tr>')
        pieces.append('<tr class="table-secondary"><th>Total</th><th>%s</th><th>%s</th>' % (
            local_total, seller_total))
        for amount in (fa_sum, de_sum, fa_sum - de_sum, base_sum):
            pieces.append('<th>%s</th>' % money(amount, self.currency_id))
        pieces.append('</tr></tbody></table></div>')
        return Markup(''.join(pieces))

    def _html_monthly_locals(self, groups):
        """Una fila por mes y establecimiento; la cabecera va sobre los títulos."""
        self.ensure_one()
        money = self._report_money
        pieces = [
            '<div class="as-goal-report" style="display:block;width:100%;max-width:100%;'
            'min-width:0;max-height:600px;overflow-x:auto;overflow-y:auto">',
        ]
        for group in groups:
            breakdown = group['breakdown']
            group_title = 'Establecimiento: %s — Año %s' % (group['name'], self.year)
            pieces.extend([
                '<table class="table table-sm table-striped table-bordered" '
                'style="width:1020px;min-width:1020px;table-layout:fixed;'
                'white-space:normal;border-collapse:collapse">',
                '<colgroup><col style="width:160px"/><col style="width:220px"/>'
                '<col style="width:165px"/><col style="width:155px"/>'
                '<col style="width:185px"/><col style="width:135px"/></colgroup>',
                '<thead><tr class="table-primary"><th colspan="6" scope="colgroup">%s</th></tr>'
                '<tr><th>Mes</th><th>Meta mensual asignada</th>'
                '<th>Facturado FA</th><th>Devuelto DE</th>'
                '<th>Ventas netas</th><th>Cumplimiento</th></tr></thead><tbody>' % escape(group_title),
            ])
            for month in breakdown['months']:
                pieces.append('<tr><th scope="row">%s</th>' % escape(month['name']))
                for number in (month['goal_cents'] / 100.0, month['fa'],
                               month['de'], month['net']):
                    pieces.append('<td style="white-space:nowrap;text-align:right">%s</td>' %
                                  money(number, self.currency_id))
                pieces.append('<td style="white-space:nowrap;text-align:right">%s</td></tr>' %
                              self._report_percent(month['net'], month['goal_cents']))
            pieces.append('</tbody></table>')
        pieces.append('</div>')
        return Markup(''.join(pieces))

    def _html_seller_distribution(self, groups):
        """Mes -> vendedores únicos; la cabecera del establecimiento precede columnas.

        Cada vendedor sigue teniendo una sola cuota y fila por mes. La presentación
        no agrega ni modifica ventas, porcentajes o importes calculados.
        """
        self.ensure_one()
        money = self._report_money
        number_style = ' style="white-space:nowrap;text-align:right;vertical-align:middle"'
        pieces = [
            '<div class="as-goal-report" style="display:block;width:100%;max-width:100%;'
            'min-width:0;max-height:650px;overflow-x:auto;overflow-y:auto">',
        ]
        for group in groups:
            breakdown = group['breakdown']
            group_title = 'Establecimiento: %s — Año %s' % (group['name'], self.year)
            pieces.extend([
                '<table class="table table-sm table-striped table-bordered" '
                'style="width:1160px;min-width:1160px;table-layout:fixed;'
                'white-space:normal;border-collapse:collapse">',
                '<colgroup><col style="width:250px"/><col style="width:210px"/>'
                '<col style="width:150px"/><col style="width:150px"/>'
                '<col style="width:150px"/><col style="width:150px"/></colgroup>',
                '<thead><tr class="table-primary"><th colspan="6" scope="colgroup">%s</th></tr>'
                '<tr><th>Vendedor</th><th>Meta mensual asignada</th>'
                '<th>Facturado FA</th><th>Devuelto DE</th>'
                '<th>Ventas netas</th><th>Cumplimiento</th></tr></thead><tbody>' % escape(group_title),
            ])
            for month in breakdown['months']:
                pieces.append('<tr class="table-secondary"><th colspan="6" '
                              'scope="rowgroup">%s</th></tr>' % escape(month['name']))
                for seller in sorted(month['sellers'], key=lambda x: x['name'].casefold()):
                    pieces.append('<tr><td style="white-space:normal;overflow-wrap:break-word">'
                                  '%s</td>' % escape(seller['name']))
                    for number in (seller['goal_cents'] / 100.0, seller['fa'],
                                   seller['de'], seller['net']):
                        pieces.append('<td%s>%s</td>' % (
                            number_style, money(number, self.currency_id)))
                    pieces.append('<td%s>%s</td></tr>' % (
                        number_style, self._report_percent(
                            seller['net'], seller['goal_cents'])))
                if not month['sellers']:
                    pieces.append('<tr><td colspan="6">Sin vendedores identificados.</td></tr>')
            pieces.append('</tbody></table>')
        pieces.append('</div>')
        return Markup(''.join(pieces))

    @api.depends('year', 'company_id', 'establishment_id', 'establishment_id.local_ids',
                 'monthly_line_ids.month', 'monthly_line_ids.target_amount')
    def _compute_monthly_distribution(self):
        """Agrupar por establecimiento/año/mes, con porcentajes iguales por persona.

        La meta de compañía se separa por establecimientos y por nlocal sin
        establecimiento, sin combinar vendedores de distintos establecimientos.
        El resultado es calculado en vivo; no persiste saldos desactualizados.
        """
        establishment_model = self.env['analytics.sales.establishment'].sudo()
        local_model = self.env['analytics.sales.local'].sudo()
        for rec in self:
            if rec.establishment_id:
                selections = [(rec.establishment_id.name, rec.establishment_id.local_ids)]
            elif rec.company_id:
                all_locals = local_model.with_context(active_test=False).search([
                    ('company_id', '=', rec.company_id.id)])
                establishments = establishment_model.with_context(active_test=False).search([
                    ('company_id', '=', rec.company_id.id)])
                selections = [(est.name, est.local_ids & all_locals) for est in establishments]
                linked = set(establishments.mapped('local_ids').ids)
                unlinked = all_locals.filtered(lambda local: local.id not in linked)
                if unlinked:
                    selections.append(('Sin establecimiento', unlinked))
            else:
                selections = []
            selected_ids = list(set(loc.id for _, locals_in_group in selections for loc in locals_in_group))
            grouped = rec._grouped_seller_sales(selected_ids) if rec.company_id else []
            configured = {int(line.month): line.target_amount or 0.0
                          for line in rec.monthly_line_ids if line.month}
            # A month with no goal is zero. Never infer a goal from FA-DE.
            monthly_targets = [configured.get(month, 0.0) for month in range(1, 13)]
            results = []
            for label, locals_in_group in selections:
                local_names = {loc.id: loc.name for loc in locals_in_group}
                rows = [r for r in grouped if r['local_id'] in local_names]
                fa = sum(abs(float(r['total_net'] or 0)) for r in rows if r['document_type'] == 'FA')
                de = sum(abs(float(r['total_net'] or 0)) for r in rows if r['document_type'] == 'DE')
                bd = build_monthly_goals(local_names, rows, fa - de,
                                         monthly_targets=monthly_targets)
                results.append({'name': label, 'local_names': local_names,
                                'local_count': len(local_names), 'breakdown': bd})
            # Legacy unassigned base on a company without any local.
            rec.distribution_amount = sum(x['breakdown']['annual_goal_cents'] for x in results) / 100.0
            rec.distribution_unassigned = sum(x['breakdown']['unassigned_cents'] for x in results) / 100.0
            rec.distribution_method = 'Metas mensuales ingresadas; reparto igual por vendedor'
            rec.annual_establishment_report = rec._html_annual_establishments(results)
            rec.monthly_local_report = rec._html_monthly_locals(results)
            rec.monthly_seller_report = rec._html_seller_distribution(results)
