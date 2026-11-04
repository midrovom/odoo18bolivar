# -*- coding: utf-8 -*-

import logging
import requests 
import json
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
from datetime import datetime
from itertools import groupby



class balance_portfolio(models.Model):
    _name = 'balance.portfolio'
    _description = 'balance_portfolio'

    @api.depends('client_id')
    def _compute_display_name(self):
        for record in self:
            record.display_name = record.client_id.display_name or ""

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    client_id = fields.Many2one('res.partner', string='Cliente', required=True)
    client_vat = fields.Char(related='client_id.vat', string='Cédula del Cliente')
    client_detail_ids = fields.One2many('balance.portfolio.lines', 'client_id', string='Detalles de Pagos')
    sales_man =   fields.Char( string='Vendedor')
    status = fields.Selection([("A", "Activo"),("I", "Inactivo"),("P", "Pendiente")],
        string="Estado",
        copy=False,
        default="I",
        index=True,
        readonly=False, 
        tracking=True,
    )  

    current_date = fields.Date(
        string='Fecha Actual',
        compute='_compute_current_date',
        store=True
    )

    factura_ids = fields.One2many(
        'balance.portfolio.lines',
        'client_id',
        domain=[('tipo', '!=', 'CH')],
        string='Pagos con Factura'
    )

    cheque_ids = fields.One2many(
        'balance.portfolio.lines',
        'client_id',
        domain=[('tipo', '=', 'CH')],
        string='Pagos con Cheque'
    )



    total_amount = fields.Float(string='Total facturado', compute='_compute_total_amount')
    total_balance = fields.Float(string='Saldo de cartera', compute='_compute_total_balance')
    overdue_accounts = fields.Float(string='Cartera vencida', compute='_compute_overdue_accounts')
    accounts_collected = fields.Float(string='Cartera por vencer', compute='_compute_accounts_collected')
    postdated_checks = fields.Float(string='Cheques posfechados', compute='_compute_postdated_checks')
    #balance_amount = fields.Float(string='Saldo', compute='_compute_balance_amount')
    

    @api.depends_context('uid')  # Asegura que se recalcula por contexto
    def _compute_current_date(self):
        today = fields.Date.today()
        for record in self:
            record.current_date = today

    @api.depends('client_detail_ids.total')
    def _compute_total_amount(self):
        for balance in self:
            total = sum(float(line.total) for line in balance.client_detail_ids)
            balance.total_amount = total

    @api.depends('client_detail_ids.balance')
    def _compute_total_balance(self):
        for balance in self:
            details_filtered = balance.client_detail_ids.filtered(lambda detail: detail.tipo != 'CH')
            total_balance = sum(float(line.balance) for line in details_filtered)
            balance.total_balance = total_balance

    @api.depends('client_detail_ids.balance', 'client_detail_ids.days', 'client_detail_ids.tipo')
    def _compute_overdue_accounts(self):
        for balance in self:
            total_balance = sum(
                float(line.balance) for line in balance.client_detail_ids 
                if line.days and line.days.isdigit() and int(line.days) > 0 and line.tipo != "CH"
            )
            balance.overdue_accounts = total_balance

    @api.depends('client_detail_ids.balance', 'client_detail_ids.days', 'client_detail_ids.tipo')
    def _compute_accounts_collected(self):
        for balance in self:
            total_collected = sum(
                float(line.balance) for line in balance.client_detail_ids
                if line.days and isinstance(line.days, str) and line.days.lstrip('-').isdigit() 
                and int(line.days) <= 0 and line.tipo != "CH"
            )
            balance.accounts_collected = total_collected

    @api.depends('client_detail_ids.balance', 'client_detail_ids.tipo')
    def _compute_postdated_checks(self):
        for balance in self:
            total_balance = sum(
                float(line.balance) for line in balance.client_detail_ids 
                if line.tipo == "CH"
            )
            balance.postdated_checks = total_balance

    @api.onchange('client_detail_ids')
    def _onchange_client_detail_ids(self):
        if not self.client_detail_ids:
            self.status = 'I'
        else:
            self.status = 'A'

    @api.onchange('total_amount')
    def _compute_balance_state(self):
        for balance in self:
            total = balance.total_amount
            # _logger.info("API CHANGE AMOUNT %s", total)
            if total == 0:
                balance.write({'status': 'I'})  # Cambiar el estado a 'Innactivo a nivel de modelo' si el total es 0
            else:
                balance.write({'status': 'A'})  

    @api.model
    def date_format( self, date_id):
        fecha_str = date_id
        fecha_str = fecha_str.replace('.', '-') 
        # _logger.info("FECHAS STRING %s", fecha_str)
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d')
        return fecha_obj

    @api.model
    def mark_all_inactive(self):
        cabeceras = self.search([])
        cabeceras.write({'status': 'I'})


    def create_balance_portfolio_api(self):
        """ Crea saldo de cartera """
        lines_value = []
        count = 1
        detalles_creados = 1
        data = 0
        partern_id = self.client_id
        company_id = self.company_id
        api_url = ''
        #LLamo al api 
        api_data = self.env['api.administrator'].sudo().search(
                        [ ( 'name', '=', 'api_balance_detail_report' ),('type','=','get'),('company_id','=', company_id.id)], limit=1)
        
        try:
            if (api_data.id) :
                old_str = "$num_cedula"
                new_str = self.client_id.vat 
                api_url = api_data.url + api_data.end_point.strip()
                api_url_new = api_url.replace(old_str, new_str)

                # _logger.info(f'MOSTRANDO EL NEW STR >>> { new_str }')
                # _logger.info(f'MOSTRANDO EL API URL >>> { api_url }')
                # _logger.info(f'MOSTRANDO EL API URL NEW >>> { api_url_new }')

                headers = {
                        'Accept': 'application/json',
                        'version': '1',
                        'framework': 'PRUEBAS',
                        'userid': api_data.user_id.strip(),
                        'password': api_data.password.strip(),
                        'deviceid': '000000000000000',
                        'sessionid': '0'
                    }
                response = requests.get(api_url_new, headers= headers)


                parsed_data = response.json()
                if  parsed_data.get('success') == True :
                    count = 0
                    partners_request = parsed_data.get("data")
                    if partners_request:
                        # Elimina las líneas del balnace que no están en la lista de line_ids
                        for line in self.client_detail_ids:
                            if line.id_register not in partners_request:
                                line.unlink()                        
                        for line_list in partners_request:
                            balance_portfolio_line = []
                            balance_portfolio_line = {
                                        'client_id': self.id,
                                        'tipo': line_list["tipo"],
                                        'id_register': line_list["registro"],
                                        'record_date': self.date_format(line_list["fecha_emision"]),
                                        'end_date': self.date_format(line_list["fecha_vencimiento"]),
                                        'days': line_list["dias"],
                                        'total': line_list["total"],
                                        'balance': line_list["saldo"],
                                        'quota':line_list["cupo"],
                                        'term': line_list["plazo"],
                                    }
                            

                            balance_portfolio_line_new = self.env['balance.portfolio.lines'].create(balance_portfolio_line)
                            # _logger.info("DEATTALES CREADOS %s", balance_portfolio_line_new.record_date)

                else:
                    for line in self.client_detail_ids:
                        line.unlink()


        except Exception as e:
            _logger.error("Error al hacer la solicitud a la API: %s", str(e))
            data = {'datos': False, 'count': 0 ,'st_data':str(e)}
            return data

    @api.model
    def _create_balance_portfolio_all( self, company_id):
        """ Crea saldo de cartera """
        try:
            data = 0
            api_url = ''
            api_data = self.env['api.administrator'].sudo().search(
                        [ ( 'name', '=', 'api_balance_detail_report_all' ),('type','=','get'),('company_id','=',company_id)], limit=1)
            
            if (api_data.id) :
                api_url = api_data.url + api_data.end_point.strip()
                # _logger.info("__DEBUG: %s", api_url)
                payload = {}
                files={}
                headers = {
                    'Accept': 'application/json',
                    'version': '1',
                    'framework': 'PRUEBAS',
                    'userid': api_data.user_id.strip(),
                    'password': api_data.password.strip(),
                    'deviceid': '000000000000000',
                    'sessionid': '0'
                }
                response = requests.get(api_url, headers= headers)
                parsed_data = response.json()
                ##si el api trae resultados
                if  parsed_data.get('success') == True :
                    self.mark_all_inactive()
                    count = 0
                    #balance_lines_request = parsed_data.get("data")
                    request = parsed_data.get("data")
                    
                    if request :
                        only_registers = [ d['registro'] for d in request  ]
                        balance_porfolio_search = self.search([])

                        if balance_porfolio_search:
                            balance_lines = balance_porfolio_search.client_detail_ids.filtered(lambda l : l.id_register not in only_registers)

                            if balance_lines:
                                balance_lines.sudo().unlink()

                        request.sort(key=lambda x: x["ruc"])
                        request_data = {ruc: list(group) for ruc, group in groupby(request, key=lambda x: x["ruc"])}
                        #_logger.info("__DEBUG request_data: %s", request_data)
                        for ruc, detail in request_data.items():
                            # _logger.info("__DEBUG ruc : %s", ruc)
                            # _logger.info("__DEBUG detail : %s", detail)
                            res_balance_portfolio = self.search([('client_vat', '=', ruc)],limit=1)
                            
                            if res_balance_portfolio :
                                # Elimina las líneas del balnace que no están en la lista de line_ids_to_keep.
                                for line in res_balance_portfolio.client_detail_ids:
                                    only_registers = [ d['registro'] for d in detail  ]

                                    if line.id_register not in only_registers:
                                        line.sudo().unlink() 
                                #res_balance_portfolio.client_detail_ids.unlink() # tambien funciona
                                # _logger.info("balance portfolio %s", res_balance_portfolio)
                                for details in detail:
                                    lines_exist = res_balance_portfolio.client_detail_ids.filtered(lambda x: x.id_register == details['registro'])
                                    # balance_portfolio_line = []
                                    balance_portfolio_line = { 
                                        'tipo': details['tipo'].upper(),
                                        'id_register': details['registro'],
                                        'record_date': self.date_format(details['fecha_emision']),
                                        'end_date': self.date_format(details['fecha_vencimiento']),
                                        'days': details['dias'],
                                        'total': details['total'],
                                        'balance': details['saldo'],
                                        'quota':details['cupo'],
                                        'term': details['plazo'],
                                    }
                                    if not lines_exist:
                                        agree_client = {'client_id': res_balance_portfolio.id}
                                        balance_portfolio_line.update(agree_client)
                                        balance_portfolio_line_new = self.env['balance.portfolio.lines'].create(balance_portfolio_line)
                                        # _logger.info("DEATTALES CREADOS %s", balance_portfolio_line_new)
                                    else:
                                        lines_exist.write(balance_portfolio_line)
                                        #tambien funciona 
                                        # new_balance.write({'client_detail_ids': [(1, new_balance.id, balance_portfolio_line)] })
                                        # _logger.info("DETALLES ACTUALIZADO ")
                                    res_balance_portfolio._compute_balance_state()
                    else :
                        _logger.error("Error 404 no existe data: %s", 0)            
        except Exception as e:
            _logger.error("Error al hacer la solicitud a la API: %s", str(e))
            data = {'datos': False, 'count': 0 ,'st_data':str(e)}
            return data


    @api.model
    def crete_balance_portfolio_head( self, partern_id, company_id, vendedor):
        """ Crear cabeceras """
        res_balance_portfolio = self.search([('client_id', '=', partern_id)],limit=1)
        if not res_balance_portfolio:
            balance_vals = { 'client_id': partern_id, 'sales_man': vendedor } # Antes se anadia sales man 'sales_man': vendedor
            new_balance = self.create(balance_vals)
            # _logger.info("API BALANCE PORTFOLIO NUEVO Cliente  %s", new_balance)
        else:
            if not res_balance_portfolio.sales_man:
                res_balance_portfolio.write({ 'sales_man': vendedor }) # Antes se anadia sales man 'sales_man': vendedor
            # _logger.info("API BALANCE PORTFOLIO Cliente Actualizado  %s", new_balance)

        # _logger.info("API CREATE USER %s", new_balance.client_id.name)


    @api.model
    def _balance_portfolio_partner_api(self, company_id=1):
        try:
            api_data = self.env['api.administrator'].sudo().search([
                ('name', '=', 'balance_partner_update'),
                ('type', 'in', ['post', 'get']),
                ('company_id', '=', company_id)
            ], limit=1)

            if not api_data:
                _logger.warning("No API configuration found for company %s", company_id)
                return {'datos': False, 'count': 0, 'st_data': 'No API configuration found'}

            api_url = api_data.url + api_data.end_point.strip()
            headers = {
                'Accept': 'application/json',
                'version': '1',
                'framework': 'PRUEBAS',
                'userid': api_data.user_id.strip(),
                'password': api_data.password.strip(),
                'deviceid': '000000000000000',
                'sessionid': '0'
            }

            if api_data.type == 'get':
                response = requests.get(api_url, headers=headers)
            else:
                response = requests.post(api_url, headers=headers)
                
            parsed_data = response.json()
            
            # _logger.info("__DEBUG parsed_data partner: %s", parsed_data)

            if not parsed_data.get('success'):
                return {'datos': False, 'count': 0, 'st_data': 'API request failed'}

            partners_request = parsed_data.get("data", [])

            # _logger.info("__DEBUG parsed_data partner: %s", partners_request)
            
            identification_types = {
                'F': 4,  # Consumidor final
                'P': 2,  # Pasaporte
                'C': 5,  # Cédula
                'R': 4,  # RUC
            }
            
            for elements in partners_request:
                vendedor = elements.get('vendedor', '').strip()
                res_users_id = self.env['res.users'].sudo().search(
                    [("balance_code", "=", vendedor)], limit=1
                )

                partner_vat = elements.get('ruc', '').strip()
                tipoid = elements.get('tipoid', '').strip()
                
                if tipoid not in identification_types:
                    _logger.warning("Tipo de documento inválido: %s para RUC: %s", tipoid, partner_vat)
                    continue

                id_type = identification_types[tipoid]
                id_type_record = self.env['l10n_latam.identification.type'].sudo().browse(id_type)

                try:
                    candidate = self.env['res.partner'].new({
                        'name': elements.get('nombre') or '',
                        'vat': partner_vat,
                        'l10n_latam_identification_type_id': id_type_record.id,
                    })
                    candidate.check_vat()
                except (UserError, ValidationError) as e:
                    _logger.warning("Número de identificación incorrecto: %s. Se asignará como Pasaporte", partner_vat)
                    validated_type = 'passport'
                    id_type = 2  # Pasaporte

                res_partner = self.env['res.partner'].sudo().search([('vat', '=', partner_vat)], limit=1)
                
                partner_data = {
                    'name': elements.get('nombre', '').strip(),
                    'vat': partner_vat,
                    'l10n_latam_identification_type_id': id_type
                }
                
                
                if not res_partner:
                    new_partner = self.env['res.partner'].sudo().create(partner_data)
                    # _logger.info("API INFO CREATE USER %s", new_partner.id)
                else:
                    res_partner.write(partner_data)
                    # _logger.info("API INFO UPDATE USER %s", res_partner.id)
                
                self.crete_balance_portfolio_head(res_partner.id if res_partner else new_partner.id, company_id, vendedor)

        except Exception as e:
            _logger.error("Error al hacer la solicitud a la API: %s", str(e))
            return {'datos': False, 'count': 0, 'st_data': str(e)}

        
    #@api.model
    #def _balance_portfolio_partner_api(self, company_id = 1):
    #    ''' Call from cron or direct '''
    #    try:
    #        data = 0
    #        api_url = ''
    #        api_data = self.env['api.administrator'].sudo().search(
    #                    [ ( 'name', '=', 'balance_partner_update' ),('api_type','=','post'),('company_id','=',company_id)], limit=1)
    #        #si existe el end point
    #        if (api_data.id) :
    #            api_url = api_data.url + api_data.end_point.strip()
    #            payload = {}
    #            files={}
    #            headers = {
    #                'Accept': 'application/json',
    #                'version': '1',
    #                'framework': 'PRUEBAS',
    #                'userid': api_data.user_id.strip(),
    #                'password': api_data.password.strip(),
    #                'deviceid': '000000000000000',
    #                'sessionid': '0'
    #            }
    #            response = requests.post(api_url, headers= headers)
    #            parsed_data = response.json()
    #            _logger.info("__DEBUG parsed_data partner : %s", parsed_data)
    #            ##si el api trae resultados
    #            if  parsed_data.get('success') == True :
    #                count = 0
    #                partners_request = parsed_data.get("data")
    #                
    #                if partners_request :
    #                    #se crea a los clientes
    #                    for elements in partners_request :
    #                        seller_code = elements.get('vendedor').strip()
    #                        res_users_id = self.env['res.users'].sudo().search(
    #                                    [("balance_code","=", seller_code)], limit=1)
    #                        
    #                        partner_ruc = elements.get('ruc').strip()
    #                        res_partner = self.env['res.partner'].sudo().search([('vat', '=', partner_ruc)],limit=1)
    #                        dict_q = {}
    #                        dict_q['name'] = elements.get('nombre').strip()
    #                        dict_q['vat'] = elements.get('ruc').strip()
    #                        if res_users_id :
    #                            dict_q['user_id'] = res_users_id.id
    #                        #_logger.info("API INFO ARREGLO %s", dict_q)
    #                        # no existe el cliente se lo crea
    #                        if not res_partner:
    #                            newclient = self.env['res.partner'].sudo().create(dict_q)
    #                            partern_id = newclient.id
    #                            _logger.info("API INFO CREATE USER %s", partern_id)
    #                                
    #                        else:
    #                            partern_id = res_partner.id
    #                            res_partner.write(dict_q)
    #                            res_partner.env.cr.commit()
    #                            _logger.info("API INFO UPDATE USER %s", res_partner.id)
    #                        # se crea el saldo de cartera toma mucho tiempo y mata al servidor
    #                        if partern_id :
    #                            self.crete_balance_portfolio_head(partern_id, company_id)
    #                            
    #    except Exception as e:
    #        _logger.error("Error al hacer la solicitud a la API: %s", str(e))
    #        data = {'datos': False, 'count': 0 ,'st_data':str(e)}
    #        return data