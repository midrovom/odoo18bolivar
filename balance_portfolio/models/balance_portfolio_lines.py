# -*- coding: utf-8 -*-

import logging
import requests 
import json
from odoo import models, fields, api
_logger = logging.getLogger(__name__)
from datetime import datetime

class balance_portfolio_lines(models.Model):
    _name = 'balance.portfolio.lines'
    _description = 'balance_portfolio_lines'
    _order = 'days_order desc'


    #parameter to One2many, 
    client_id = fields.Many2one( "balance.portfolio", 
                                string="head_key",
                                required=True,
                                readonly=True,
                                index=True,
                                auto_join=True,
                                ondelete="cascade",
                                check_company=True,
                            )
    
    # type = fields.Char( string = 'Tipo')
    tipo = fields.Char(string='Tipo')

    id_register = fields.Char( string = 'Registro')
    date = fields.Datetime(string='Fecha',default=fields.Datetime.now,)
    record_date = fields.Date(string='Fecha de emision')  
    end_date = fields.Date(string='Fecha de vencimiento')  
    days = fields.Char( string = 'Dias')

    # Campo computado
    # Ordenacion de mayor a menor
    days_order = fields.Integer(string='Días', compute='_compute_days_order', store=True)

    total = fields.Char(string = 'Total')  
    balance = fields.Char(string = 'Saldo')  
    quota = fields.Char(string = 'Cupo')  
    term = fields.Char(string = 'Plazo')  
    status = fields.Selection(
        selection=[
            ("A", "Activo"),
            ("I", "Inactivo"),
            ("P", "Pendiente"),
        ],
        string="Estado",
        copy=False,
        default="A",
        index=True,
        readonly=True,
        tracking=True,
    )
    description = fields.Text(string='Observaciones')

    @api.depends('days')
    def _compute_days_order(self):
        for record in self:
            record.days_order = int(record.days) if (record.days or '').lstrip('-').isdigit() else 0

    # @api.depends('balance', 'client_id')
    # def _compute_suma_saldo_fa(self):
    #     if not self:
    #         return

    #     # Obtener todos los clientes involucrados en self
    #     client_ids = self.mapped('client_id').ids  

    #     # Buscar todos los registros de estos clientes con tipo 'FA'
    #     all_records = self.search([
    #         ('client_id', 'in', client_ids),
    #         ('tipo', '=', 'FA')
    #     ], order='days_order desc')

    #     # Agrupar por cliente
    #     clientes_dict = {}
    #     for record in all_records:
    #         clientes_dict.setdefault(record.client_id.id, []).append(record)

    #     # Calcular saldo acumulado
    #     for client_id, records in clientes_dict.items():
    #         suma_acumulada = 0
    #         for linea in records:
    #             _logger.info(f'MOSTRANDO BALANCE >>> { linea.balance }')
    #             suma_acumulada += float(linea.balance)
    #             linea.suma_saldo_fa = suma_acumulada

    #     # Asegurar que todos los registros en self tienen un valor
    #     for record in self:
    #         if not record.suma_saldo_fa:
    #             record.suma_saldo_fa = 0


    # @api.depends('balance', 'client_id')
    # def _compute_suma_saldo_ch(self):
    #     if not self:
    #         return

    #     # Obtener todos los clientes involucrados en self
    #     client_ids = self.mapped('client_id').ids  

    #     # Buscar todos los registros de estos clientes con tipo 'FA'
    #     all_records = self.search([
    #         ('client_id', 'in', client_ids),
    #         ('tipo', '=', 'CH')
    #     ], order='days_order desc')

    #     # Agrupar por cliente
    #     clientes_dict = {}
    #     for record in all_records:
    #         clientes_dict.setdefault(record.client_id.id, []).append(record)

    #     # Calcular saldo acumulado
    #     for client_id, records in clientes_dict.items():
    #         suma_acumulada = 0
    #         for linea in records:
    #             suma_acumulada += float(linea.balance)
    #             linea.suma_saldo_ch = suma_acumulada

    #     # Asegurar que todos los registros en self tienen un valor
    #     for record in self:
    #         if not record.suma_saldo_ch:
    #             record.suma_saldo_ch = 0

