# -*- coding: utf-8 -*-
import logging
from urllib.parse import quote

import requests

from odoo import models, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class APIAdministrator(models.Model):
    _inherit = 'api.administrator'

    def call_api_stock(self, api_name, method='get', sku=None, warehouse=None, company_id=None):
        """Consulta stock Radis conservando URL: /'SKU'/'BODEGA'/ ."""
        if not sku or not warehouse:
            raise ValidationError(_('Se requieren SKU y bodega para consultar stock.'))
        domain = [('name', '=', api_name), ('type', '=', method)]
        if company_id:
            domain.append(('company_id', '=', company_id))
        api_data = self.sudo().search(domain, limit=1)
        if not api_data:
            raise ValidationError(_('Configuración de API %s no encontrada para esta empresa.') % api_name)
        base_url = (api_data.url or '').strip().rstrip('/')
        endpoint = (api_data.end_point or '').strip().strip('/')
        if not base_url:
            raise ValidationError(_('Falta URL en la configuración API %s.') % api_name)
        url = '%s/%s/\'%s\'/\'%s\'/' % (
            base_url, endpoint, quote(str(sku), safe=''), quote(str(warehouse), safe=''),
        )
        headers = {
            'Accept': 'application/json', 'version': '1', 'framework': 'PRUEBAS',
            'userid': (api_data.user_id or '').strip(),
            'password': (api_data.password or '').strip(),
            'deviceid': '000000000000000', 'sessionid': '0',
        }
        try:
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict):
                raise ValidationError(_('Respuesta de stock no válida de la API %s.') % api_name)
            _logger.info('Stock Radis consultado SKU=%s bodega=%s', sku, warehouse)
            return result
        except requests.RequestException as exc:
            _logger.exception('Error consultando stock Radis SKU=%s bodega=%s', sku, warehouse)
            raise ValidationError(_('Error consultando stock: %s') % exc) from exc
        except ValueError as exc:
            raise ValidationError(_('La API de stock devolvió JSON no válido: %s') % exc) from exc
