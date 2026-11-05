from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from collections import defaultdict
from markupsafe import Markup

_logger = logging.getLogger(__name__)

MONTHS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


class SaleRankingReport(models.TransientModel):
    _name = 'sale.ranking.report'
    _description = 'Matriz de Clientes y Marcas'

    def _get_api_data(self):
        """Obtiene y procesa datos de la API"""
        try:
            company_id = self.env.user.company_id.id
            api_response = self.env['api.administrator'].call_api(
                api_name='ranking_ventas',
                method='get',
                company_id=company_id,
                params=[]
            ).get('data', [])
            
            return api_response
        
        except Exception as e:
            _logger.error(f"Error al obtener datos de API: {str(e)}")
            raise ValidationError(f"Error al obtener datos: {str(e)}")
    

    @api.model
    def processed_data(self, vendor_code_filter=None):
        _logger.info(f'MOSTRANDO VENDOR >>>>>> { vendor_code_filter }')
        data = self._get_api_data()

        # --------
        # PRIMER PASO: Construir sets de todas las marcas y todos los meses existentes
        # --------

        marcas_global = set()
        meses_global = set()

        for item in data:
            marca = item["marca"].strip().capitalize()
            mes = int(item["mes"])
            marcas_global.add(marca)
            meses_global.add(mes)

        marcas_global = sorted(marcas_global)
        meses_sorted = sorted(meses_global)
        meses_abrev = [MONTHS[m - 1] for m in meses_sorted]

        # --------
        # SEGUNDO PASO: Filtrar datos por vendedor (si corresponde)
        # --------

        is_vendor = self.env.user.has_group("sale_ranking_report.group_sale_ranking_vendor_code")

        if is_vendor:
            balance_code = (self.env.user.balance_code or '').strip()
            balance_code = balance_code.lower()

            if not balance_code:
                raise ValidationError("No tiene configurado el código de vendedor, contactese con el administrador.")

            data = [
                item for item in data
                if item.get("vendedor", "").strip().lower() == balance_code
            ]

        if vendor_code_filter:
            data = [
                item for item in data
                if item.get("vendedor", "").strip().lower() == vendor_code_filter.strip().lower()
            ]

        # --------
        # TERCER PASO: Agrupar datos filtrados
        # --------

        grouped = defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(float)
            )
        )

        for item in data:
            cliente = item["cliente"].strip().title()
            marca = item["marca"].strip().capitalize()
            mes = int(item["mes"])
            cantidad = float(item["cantidad"].strip())
            grouped[cliente][marca][mes] += cantidad

        # --------
        # CUARTO PASO: Completar marcas y meses con ceros para TODOS los clientes
        # --------

        clientes = []
        for cliente, marcas_dict in grouped.items():
            data_cliente = {}
            total_cliente = 0.0
            for marca in marcas_global:
                data_marca = {}
                for mes in meses_sorted:
                    nombre_mes = MONTHS[mes - 1]
                    valor = marcas_dict.get(marca, {}).get(mes, 0.0)
                    data_marca[nombre_mes] = valor
                    total_cliente += valor
                data_cliente[marca] = data_marca
            clientes.append({
                "nombre": cliente,
                "data": data_cliente,
                "total": total_cliente
            })

        # --------
        # QUINTO PASO: Calcular totales por marca y mes
        # --------

        totales = defaultdict(lambda: defaultdict(float))
        for cliente, marcas_dict in grouped.items():
            for marca in marcas_global:
                for mes in meses_sorted:
                    valor = marcas_dict.get(marca, {}).get(mes, 0.0)
                    totales[marca][mes] += valor

        totales_dict = {}
        for marca in marcas_global:
            data_marca = {}
            for mes in meses_sorted:
                nombre_mes = MONTHS[mes - 1]
                data_marca[nombre_mes] = totales[marca].get(mes, 0.0)
            totales_dict[marca] = data_marca

        total_general = sum(c["total"] for c in clientes)

        data_final = {
            "marcas": marcas_global,
            "meses": meses_abrev,
            "clientes": clientes,
            "totales": totales_dict,
            "total_general": total_general,
        }

        return data_final



    @api.model
    def is_not_user_admin(self):
        return not self.env.user.has_group("sale_ranking_report.group_sale_ranking_vendor_code")

