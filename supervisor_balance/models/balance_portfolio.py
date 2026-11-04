# -*- coding: utf-8 -*-

import logging
import requests 
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class balance_portfolio(models.Model):
    _inherit = 'balance.portfolio'

    sales_man =   fields.Char( string='Código de Vendedor')
    supervisor = fields.Char('Supervisor')
    vendedor = fields.Char('Vendedor')
    code_super = fields.Char( string='Código de Supervisor')

    overdue_accounts = fields.Float(string='Cartera vencida', compute='_compute_overdue_accounts', store=True)

    ciudad = fields.Char('Ciudad')
    provincia = fields.Char('Provincia')

    @api.model
    def buttom_tree_balance_portfolio_all(self):
        self._create_balance_portfolio_all(1)

    @api.model
    def crete_balance_portfolio_head( self, partern_id, company_id, vendedor, code_super, supervisor, name_vendor, direccion):
        # dir_ciud = direccion.get("ciudad", "")
        # dir_prov = direccion.get("provincia", "")
        
        # sales_man = vendedor if vendedor != "" else None
        # supervisor_man = supervisor if supervisor != "" else None
        # vendedor_man = name_vendor if name_vendor != "" else None
        # code_super_man = code_super if code_super != "" else None
        # ciudad = dir_ciud if dir_ciud != "" else None
        # provincia = dir_prov if dir_prov != "" else None
        # """ Crear cabeceras """
        # res_balance_portfolio = self.search([('client_id', '=', partern_id)],limit=1)
        # if not res_balance_portfolio:
        #     balance_vals = {
        #          'client_id': partern_id, 
        #          'sales_man': sales_man, 
        #          'supervisor': supervisor_man,
        #          'vendedor': vendedor_man,
        #          'code_super': code_super_man,
        #          'ciudad': ciudad,
        #          'provincia': provincia
        #     }
        #     self.create(balance_vals)
        # else:
        #     res_balance_portfolio.write({ 'code_super': code_super_man, 'supervisor': supervisor_man })

        #     if not res_balance_portfolio.sales_man:
        #         res_balance_portfolio.write({ 'sales_man': sales_man })
        #     if not res_balance_portfolio.vendedor:
        #         res_balance_portfolio.write({ 'vendedor': vendedor_man }) 
        #     if not res_balance_portfolio.ciudad:
        #         res_balance_portfolio.write({ 'ciudad': ciudad })
        #     if not res_balance_portfolio.provincia:
        #         res_balance_portfolio.write({ 'provincia': provincia })

        dir_ciud = direccion.get("ciudad") or False
        dir_prov = direccion.get("provincia") or False

        vals = {
            'sales_man': vendedor or False,
            'supervisor': supervisor or False,
            'vendedor': name_vendor or False,
            'code_super': code_super or False,
            'ciudad': dir_ciud,
            'provincia': dir_prov,
            'company_id': company_id,
            'client_id': partern_id,
        }

        portfolio = self.sudo().search(
            [('client_id', '=', partern_id)],
            limit=1
        )

        if not portfolio:
            self.sudo().create(vals)
            return

        # Solo escribir campos vacíos
        write_vals = {}
        for field, value in vals.items():
            if field in portfolio._fields and not portfolio[field] and value:
                write_vals[field] = value

        if write_vals:
            portfolio.write(write_vals)


    # @api.model
    # def _balance_portfolio_partner_api(self, company_id=1):
    #     try:
    #         api_data = self.env['api.administrator'].sudo().search([
    #             ('name', '=', 'balance_partner_update'),
    #             ('type', 'in', ['post', 'get']),
    #             ('company_id', '=', company_id)
    #         ], limit=1)

    #         if not api_data:
    #             _logger.warning("No API configuration found for company %s", company_id)
    #             return {'datos': False, 'count': 0, 'st_data': 'No API configuration found'}

    #         api_url = api_data.url + api_data.end_point.strip()
    #         headers = {
    #             'Accept': 'application/json',
    #             'version': '1',
    #             'framework': 'PRUEBAS',
    #             'userid': api_data.user_id.strip(),
    #             'password': api_data.password.strip(),
    #             'deviceid': '000000000000000',
    #             'sessionid': '0'
    #         }

    #         if api_data.type == 'get':
    #             response = requests.get(api_url, headers=headers)
    #         else:
    #             response = requests.post(api_url, headers=headers)
                
    #         parsed_data = response.json()
            
    #         # _logger.info("__DEBUG parsed_data partner: %s", parsed_data)

    #         if not parsed_data.get('success'):
    #             return {'datos': False, 'count': 0, 'st_data': 'API request failed'}

    #         partners_request = parsed_data.get("data", [])

    #         # _logger.info("__DEBUG parsed_data partner: %s", partners_request)
            
    #         identification_types = {
    #             'F': 4,  # Consumidor final
    #             'P': 2,  # Pasaporte
    #             'C': 5,  # Cédula
    #             'R': 4,  # RUC
    #         }
            
    #         for elements in partners_request:
    #             direccion = { "ciudad": "", "provincia": "" }

    #             direccion['ciudad'] = elements.get("ciudad", "").strip()
    #             direccion['provincia'] = elements.get("provincia", "").strip()

    #             name_vendor = elements.get("name_vendor", "").strip()
    #             supervisor = elements.get("supervisor", "").strip()
    #             code_super = elements.get("code_super", "").strip()
    #             vendedor = elements.get('vendedor', '').strip()
    #             res_users_id = self.env['res.users'].sudo().search(
    #                 [("balance_code", "=", vendedor)], limit=1
    #             )

    #             partner_vat = elements.get('ruc', '').strip()
    #             tipoid = elements.get('tipoid', '').strip()
                
    #             if tipoid not in identification_types:
    #                 _logger.warning("Tipo de documento inválido: %s para RUC: %s", tipoid, partner_vat)
    #                 continue

    #             id_type = identification_types[tipoid]
    #             id_type_record = self.env['l10n_latam.identification.type'].sudo().browse(id_type)

    #             try:
    #                 validated_type = self.env['res.partner']._validate_ref(partner_vat, id_type_record)
    #             except UserError as e:
    #                 _logger.warning("Número de identificación incorrecto: %s. Se asignará como Pasaporte", partner_vat)
    #                 validated_type = 'passport'
    #                 id_type = 2  # Pasaporte

    #             res_partner = self.env['res.partner'].sudo().search([('vat', '=', partner_vat)], limit=1)
                
    #             partner_data = {
    #                 'name': elements.get('nombre', '').strip(),
    #                 'vat': partner_vat,
    #                 'l10n_latam_identification_type_id': id_type
    #             }
                
    #             if res_users_id:
    #                 partner_data['user_id'] = None
                
    #             if not res_partner:
    #                 new_partner = self.env['res.partner'].sudo().create(partner_data)
    #             else:
    #                 res_partner.write(partner_data)
                
    #             self.crete_balance_portfolio_head(
    #                 res_partner.id if res_partner else new_partner.id, 
    #                 company_id, 
    #                 vendedor, 
    #                 code_super, 
    #                 supervisor, 
    #                 name_vendor, 
    #                 direccion
    #             )

    #     except Exception as e:
    #         _logger.error("Error al hacer la solicitud a la API: %s", str(e))
    #         return {'datos': False, 'count': 0, 'st_data': str(e)}



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
                return

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

            response = (
                requests.get(api_url, headers=headers, timeout=20)
                if api_data.type == 'get'
                else requests.post(api_url, headers=headers, timeout=20)
            )

            parsed_data = response.json()
            if not parsed_data.get('success'):
                return

            partners_request = parsed_data.get("data", [])
            if not partners_request:
                return

            # ----------------------------
            # PRE-CARGAS (CLAVE)
            # ----------------------------

            vendedores = {p.get('vendedor', '').strip() for p in partners_request}
            vats = {p.get('ruc', '').strip() for p in partners_request}

            users_map = {
                u.balance_code: u.id
                for u in self.env['res.users'].sudo().search([('balance_code', 'in', list(vendedores))])
            }

            partners_map = {
                p.vat: p
                for p in self.env['res.partner'].sudo().search([('vat', 'in', list(vats))])
            }

            identification_types = {
                'F': 4,
                'P': 2,
                'C': 5,
                'R': 4,
            }

            invalid_count = 0

            for elements in partners_request:
                direccion = { 
                    "ciudad": elements.get("ciudad", "").strip(),
                    "provincia": elements.get("provincia", "").strip()
                }

                partner_vat = elements.get('ruc', '').strip()
                tipoid = elements.get('tipoid', '').strip()

                id_type = identification_types.get(tipoid, 2)

                # VALIDACIÓN SIMPLE (sin excepción)
                try:
                    candidate = self.env['res.partner'].new({
                        'name': elements.get('nombre') or '',
                        'vat': partner_vat,
                        'l10n_latam_identification_type_id': id_type,
                    })
                    candidate.check_vat()
                except (UserError, ValidationError):
                    id_type = 2
                    invalid_count += 1

                partner_data = {
                    'name': elements.get('nombre', '').strip(),
                    'vat': partner_vat,
                    'l10n_latam_identification_type_id': id_type
                }

                res_partner = partners_map.get(partner_vat)

                if not res_partner:
                    res_partner = self.env['res.partner'].sudo().create(partner_data)
                    partners_map[partner_vat] = res_partner
                else:
                    res_partner.write(partner_data)

                self.crete_balance_portfolio_head(
                    res_partner.id,
                    company_id,
                    elements.get('vendedor'),
                    elements.get('code_super'),
                    elements.get('supervisor'),
                    elements.get('name_vendor'),
                    direccion
                )

                _logger.info(f"EJECUCION EXITOSA PARA CLIENTE *********************** { res_partner.name }")

            _logger.info(
                "Balance partner cron OK. Total: %s | Identificaciones inválidas: %s",
                len(partners_request),
                invalid_count
            )

        except Exception as e:
            _logger.error("Error cron balance portfolio: %s", str(e))

        