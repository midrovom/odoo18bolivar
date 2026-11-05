import requests
import logging
import inspect
from odoo import models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class APIAdministrator(models.Model):
    _inherit = 'api.administrator'

    def call_api_replace(self, api_name, method="get", params=None, headers_extra=None):
        _logger.warning("========== INICIO CALL_API_REPLACE ==========")
        _logger.warning(f"CALLER >>> {inspect.stack()[1].function}")
        _logger.warning(f"HEADERS_EXTRA RAW >>> {headers_extra}")

        api_data = self.sudo().search([
            ("name", "=", api_name),
            ("type", "=", method)
        ], limit=1)

        if not api_data:
            raise ValidationError(f"Configuración de API '{api_name}' no encontrada.")

        base_url = (api_data.url or '').strip()
        endpoint_original = (api_data.end_point or '').strip()

        _logger.warning(f"BASE URL >>> {base_url}")
        _logger.warning(f"ENDPOINT ORIGINAL BD >>> {endpoint_original}")

        fecha_desde = (headers_extra or {}).get("fecha_desde")
        fecha_hasta = (headers_extra or {}).get("fecha_hasta")
        tipo = (headers_extra or {}).get("tipo") or "0"

        _logger.warning(f"PARAMS >>> desde:{fecha_desde} hasta:{fecha_hasta} tipo:{tipo}")

        if not fecha_desde or not fecha_hasta:
            raise ValidationError(
                f"Faltan parámetros para la API.\n"
                f"fecha_desde: {fecha_desde}\n"
                f"fecha_hasta: {fecha_hasta}"
            )

        try:
            endpoint = (endpoint_original or '').strip('/')
            endpoint = endpoint.replace("FECHA_DESDE", f"'{fecha_desde}'")
            endpoint = endpoint.replace("FECHA_HASTA", f"'{fecha_hasta}'")
            endpoint = endpoint.replace("TIPO", tipo)

            base_clean = base_url.rstrip('/')
            api_url = f"{base_clean}/{endpoint}"

            _logger.warning(f"URL FINAL ARMADA >>> {api_url}")

        except Exception as e:
            _logger.error(f"Error construyendo endpoint: {e}", exc_info=True)
            raise ValidationError("Error construyendo la URL de la API.")

        headers = {
            'Accept': 'application/json',
            'version': '1',
            'framework': 'PRUEBAS',
            'userid': (api_data.user_id or '').strip(),
            'password': (api_data.password or '').strip(),
            'deviceid': '000000000000000',
            'sessionid': '0',
        }

        try:
            response = requests.get(api_url, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            _logger.error(f"ERROR API: {str(e)}", exc_info=True)
            raise ValidationError(f"Error API: {str(e)}")
