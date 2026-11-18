# -*- coding: utf-8 -*-
"""Editable monthly goals, with dynamic real sales per establishment/period."""
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

MONTHS = (
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
)


class AnalyticsSalesGoalMonthLine(models.Model):
    _name = 'analytics.sales.goal.month.line'
    _description = 'Meta mensual de Analytics Sales por establecimiento'
    _order = 'month asc, id asc'

    goal_id = fields.Many2one(
        'analytics.sales.goal', required=True, ondelete='cascade', index=True)
    month = fields.Selection(
        [('%02d' % i, name) for i, name in enumerate(MONTHS, 1)],
        string='Mes', required=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='goal_id.currency_id', readonly=True)
    target_amount = fields.Monetary(
        string='Meta mensual asignada', currency_field='currency_id', default=0.0,
        help='Importe que usted define para el establecimiento en este mes. '
             'Se distribuye por igual entre sus vendedores.')
    fa_amount = fields.Monetary(
        string='Facturado FA', currency_field='currency_id',
        compute='_compute_actual_sales', readonly=True)
    de_amount = fields.Monetary(
        string='Devuelto DE', currency_field='currency_id',
        compute='_compute_actual_sales', readonly=True)
    net_amount = fields.Monetary(
        string='Ventas netas', currency_field='currency_id',
        compute='_compute_actual_sales', readonly=True)
    compliance = fields.Char(
        string='Cumplimiento', compute='_compute_actual_sales', readonly=True)

    _sql_constraints = [
        ('unique_goal_month', 'unique(goal_id, month)',
         'Ya existe una meta para este mes dentro del mismo establecimiento y año.'),
    ]

    @api.constrains('target_amount')
    def _check_nonnegative(self):
        for rec in self:
            if rec.target_amount < 0:
                raise ValidationError(_('La meta mensual asignada no puede ser negativa.'))

    @api.depends('goal_id.year', 'goal_id.company_id', 'goal_id.establishment_id',
                 'goal_id.establishment_id.local_ids', 'month', 'target_amount')
    def _compute_actual_sales(self):
        for line in self:
            line.fa_amount = 0.0
            line.de_amount = 0.0
            line.net_amount = 0.0
            line.compliance = '—'
        goals = self.mapped('goal_id')
        for goal in goals:
            if goal.establishment_id:
                local_ids = goal.establishment_id.local_ids.ids
            else:
                local_ids = self.env['analytics.sales.local'].sudo().with_context(
                    active_test=False).search([('company_id', '=', goal.company_id.id)]).ids
            data = defaultdict(lambda: {'fa': 0.0, 'de': 0.0})
            if local_ids and 2000 <= goal.year <= 2100:
                for row in goal._grouped_seller_sales(local_ids):
                    month = row['month']
                    dtype = row['document_type']
                    if dtype == 'FA':
                        data[month]['fa'] += abs(float(row['total_net'] or 0.0))
                    elif dtype == 'DE':
                        data[month]['de'] += abs(float(row['total_net'] or 0.0))
            for line in self.filtered(lambda l: l.goal_id == goal):
                values = data.get(int(line.month or '0'), {})
                fa = values.get('fa', 0.0)
                de = values.get('de', 0.0)
                currency = goal.currency_id
                line.fa_amount = currency.round(fa) if currency else round(fa, 2)
                line.de_amount = currency.round(de) if currency else round(de, 2)
                line.net_amount = line.fa_amount - line.de_amount
                line.compliance = ('%.1f %%' % (100.0 * line.net_amount / line.target_amount)
                                   if line.target_amount > 0 else '—')
