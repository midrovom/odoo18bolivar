from odoo import models, fields, api
from datetime import datetime, date
import json
import logging
from decimal import Decimal, ROUND_HALF_UP

_logger = logging.getLogger(__name__)


def to_decimal(value):
    return float(Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def format_millions(value):
    value = float(value or 0)
    return f"{value:,.2f}"


class SalesReportTipo(models.Model):
    _name = 'sales.report.tipo'
    _description = 'Opciones de tipo de reporte'

    code = fields.Char(required=True)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)


class SalesReportEmpresa(models.Model):
    _name = 'sales.report.empresa'
    _description = 'Empresas para reporte de ventas'

    id_empresa = fields.Char(required=True)
    name = fields.Char(required=True)
    api_id = fields.Many2one(
        'api.administrator',
        string="API Relacionada",
        required=True,
        help="Referencia al API desde el cual se consulta esta empresa"
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('empresa_api_uniq', 'unique(id_empresa, api_id)',
         'No puede haber dos empresas con el mismo ID en la misma API.')
    ]

class JsonSalesReport(models.TransientModel):
    _name = 'json.sales.report'
    _description = 'Reporte de Ventas desde API externa'

    date_from = fields.Date(default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(default=lambda self: date.today())
    tipo = fields.Char(string="Tipo de reporte")

    @api.model
    def get_filter_options(self):
        tipos = self.env['sales.report.tipo'].search([('active', '=', True)])

        empresas = self.env.user.empresa_rel_ids.sorted(
            key=lambda x: (x.sequence, x.id)
        )

        return {
            "tipos": [{"id": t.code, "name": t.name} for t in tipos],
            "empresas": [
                {
                    "id_empresa": e.empresa_id.id_empresa,
                    "name": e.empresa_id.name,
                }
                for e in empresas
            ],
        }

    def _format_date_api(self, date_str):
        return datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y.%m.%d")

    def _get_api_data(self, date_from, date_to, tipo_code):
        fecha_desde = self._format_date_api(date_from)
        fecha_hasta = self._format_date_api(date_to)

        apis = self.env['api.administrator'].search([
            ('type', '=', 'get'),
            ('status', '=', 'A'),
            ('end_point', 'ilike', 'ventas_gerencia')
        ])

        all_data = []

        for api in apis:
            parts = (api.end_point or '').strip('/').split('/')
            empresa_code = False

            if 'ventas_gerencia' in parts:
                idx = parts.index('ventas_gerencia')
                if len(parts) > idx + 1:
                    empresa_code = parts[idx + 1]

            response = self.env['api.administrator'].call_api_replace(
                api_name=api.name,
                method='get',
                headers_extra={
                    "fecha_desde": fecha_desde,
                    "fecha_hasta": fecha_hasta,
                    "tipo": tipo_code
                }
            )

            if isinstance(response, str):
                response = json.loads(response)

            registros = response.get("data", []) if isinstance(response, dict) else response

            for r in registros:
                r['_empresa_code'] = empresa_code
                r['_api_id'] = api.id   # 🔑 guardamos el id del API

            all_data.extend(registros)

        return all_data

    @api.model
    def processed_data(self, date_from, date_to, tipo):

        tipo_code = tipo or "0"
        registros = self._get_api_data(date_from, date_to, tipo_code)
        empresas_usuario = self.env.user.empresa_rel_ids

        if not empresas_usuario:
            return {
                "error": "El usuario no tiene empresas relacionadas."
            }

        empresas_permitidas = empresas_usuario.mapped('empresa_id.id_empresa')
        order_map = {
            f"{rel.empresa_id.id_empresa}_{rel.empresa_id.api_id.id if rel.empresa_id.api_id else 0}": rel.sequence
            for rel in empresas_usuario
        }

        empresas_map = {}

        total_costo_general = 0
        total_ventas_general = 0
        total_rentabilidad_general = 0
        total_ptarjeta_general = 0

        for r in registros:
            empresa = (r.get("empresa") or "").strip()
            empresa_obj = False

            empresa_code = r.get('_empresa_code')
            api_id = r.get('_api_id')

            if not empresa:
                empresa_obj = self.env['sales.report.empresa'].search(
                    [('id_empresa', '=', empresa_code),
                    ('api_id', '=', api_id),
                    ('active', '=', True)],
                    limit=1
                )
                empresa = empresa_obj.name if empresa_obj else "Empresa desconocida"
            else:
                empresa_obj = self.env['sales.report.empresa'].search(
                    [('name', '=', empresa),
                    ('api_id', '=', api_id),
                    ('active', '=', True)],
                    limit=1
                )

            if not empresa_obj:
                continue

            if empresa_obj.id_empresa not in empresas_permitidas:
                continue

            # 🔑 clave compuesta: id_empresa + api_id
            key = f"{empresa_obj.id_empresa}_{api_id}"

            if key not in empresas_map:
                empresas_map[key] = {
                    "id_empresa": empresa_obj.id_empresa,
                    "api_id": api_id,
                    "nombre": empresa_obj.name,
                    "vendedores": [],
                    "total_costo": 0,
                    "total_ventas": 0,
                    "total_rentabilidad": 0,
                    "total_ptarjeta": 0,
                    "total_general": 0,
                }

            costo = float(r.get("costo") or 0)
            ventas = float(r.get("ventas") or 0)
            rentabilidad = float(r.get("utilidad") or 0)
            putilidad = float(r.get("putilidad") or 0)
            ptarjeta = float(r.get("ptarjeta") or 0)

            empresas_map[key]["vendedores"].append({
                "vendedor": r.get("vendedor"),
                "costo": to_decimal(costo),
                "monto_ventas": to_decimal(ventas),
                "rentabilidad": to_decimal(rentabilidad),
                "utilidad": to_decimal(putilidad),
                "ptarjeta": to_decimal(ptarjeta),
                "costo_fmt": format_millions(costo),
                "monto_ventas_fmt": format_millions(ventas),
                "rentabilidad_fmt": format_millions(rentabilidad),
                "ptarjeta_fmt": format_millions(ptarjeta),
            })

            empresas_map[key]["total_costo"] += costo
            empresas_map[key]["total_ventas"] += ventas
            empresas_map[key]["total_rentabilidad"] += rentabilidad
            empresas_map[key]["total_ptarjeta"] += ptarjeta
            empresas_map[key]["total_general"] += ventas

            total_costo_general += costo
            total_ventas_general += ventas
            total_rentabilidad_general += rentabilidad
            total_ptarjeta_general += ptarjeta

        empresas = []

        for rel in empresas_usuario.sorted(key=lambda x: (x.sequence, x.id)):
            emp_id = rel.empresa_id.id_empresa
            emp_name = rel.empresa_id.name
            api_id = rel.empresa_id.api_id.id if rel.empresa_id.api_id else 0
            key = f"{emp_id}_{api_id}"

            if key in empresas_map:
                e = empresas_map[key]
            else:
                # Empresa sin datos
                e = {
                    "id_empresa": emp_id,
                    "api_id": api_id,
                    "nombre": emp_name,
                    "vendedores": [],
                    "total_costo": 0,
                    "total_ventas": 0,
                    "total_rentabilidad": 0,
                    "total_ptarjeta": 0,
                    "total_general": 0,
                }

            # Calcular totales SIEMPRE
            e["total_costo"] = to_decimal(e["total_costo"])
            e["total_ventas"] = to_decimal(e["total_ventas"])
            e["total_rentabilidad"] = to_decimal(e["total_rentabilidad"])

            e["total_utilidad"] = to_decimal(
                (e["total_rentabilidad"] / e["total_ventas"]) * 100
                if e["total_ventas"] else 0
            )

            e["total_ptarjeta"] = to_decimal(e["total_ptarjeta"])
            e["total_general"] = to_decimal(e["total_general"])

            e["total_costo_fmt"] = format_millions(e["total_costo"])
            e["total_ventas_fmt"] = format_millions(e["total_ventas"])
            e["total_rentabilidad_fmt"] = format_millions(e["total_rentabilidad"])
            e["total_ptarjeta_fmt"] = format_millions(e["total_ptarjeta"])
            e["total_general_fmt"] = format_millions(e["total_general"])

            empresas.append(e)

        total_general_empresas = sum(e["total_general"] for e in empresas)

        total_utilidad_general = to_decimal(
            (total_rentabilidad_general / total_ventas_general) * 100
            if total_ventas_general else 0
        )

        return {
            "empresas": empresas,
            "totales_generales": {
                "costo": to_decimal(total_costo_general),
                "ventas": to_decimal(total_ventas_general),
                "rentabilidad": to_decimal(total_rentabilidad_general),
                "utilidad": total_utilidad_general,
                "ptarjeta": to_decimal(total_ptarjeta_general),
                "total_general": to_decimal(total_general_empresas),

                "costo_fmt": format_millions(total_costo_general),
                "ventas_fmt": format_millions(total_ventas_general),
                "rentabilidad_fmt": format_millions(total_rentabilidad_general),
                "ptarjeta_fmt": format_millions(total_ptarjeta_general),
                "total_general_fmt": format_millions(total_general_empresas),
            }
        }
