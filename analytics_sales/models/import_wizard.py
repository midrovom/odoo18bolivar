# -*- coding: utf-8 -*-
import base64
import binascii

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from ..excel_reader import load_sales_file, SalesExcelError, MAX_UPLOAD_BYTES


class AnalyticsSalesExcelImport(models.TransientModel):
    _name = 'analytics.sales.excel.import'
    _description = 'Importar ventas desde archivo Excel seleccionado'

    company_id = fields.Many2one('res.company', string='Compañía', required=True,
                                 default=lambda self: self.env.company, readonly=True)
    upload_file = fields.Binary(string='Archivo Excel', required=True, attachment=False)
    filename = fields.Char(string='Nombre del archivo', required=True)
    sheet_name = fields.Char(string='Nombre de hoja (opcional)',
                             help='Si no se indica, se buscará la primera hoja con las columnas de ventas.')
    import_mode = fields.Selection([
        ('merge', 'Agregar y actualizar sin borrar otros archivos'),
        ('replace', 'Reemplazar todo el histórico importado por Excel'),
    ], string='Tratamiento de datos', default='merge', required=True)

    @api.model
    def default_get(self, fields_list):
        self.env['analytics.sales.security'].check_admin()
        return super().default_get(fields_list)

    def action_import(self):
        self.ensure_one()
        self.env['analytics.sales.security'].check_admin()
        if self.company_id != self.env.company:
            raise ValidationError(_('La compañía cambió. Cierre la ventana y vuelva a abrirla desde la compañía correcta.'))
        if not self.upload_file or not self.filename:
            raise ValidationError(_('Seleccione primero el Excel que desea importar.'))
        try:
            data = base64.b64decode(self.upload_file, validate=True)
        except (ValueError, binascii.Error, TypeError):
            raise ValidationError(_('No fue posible decodificar el archivo cargado.'))
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValidationError(_('El archivo Excel supera el tamaño máximo de 30 MB.'))
        try:
            rows, sheet = load_sales_file(data, self.filename, self.sheet_name)
        except SalesExcelError as error:
            raise ValidationError(str(error))
        bad_sku = {'', '#NAME?', '#N/A', '#REF!', '#VALUE!', '#DIV/0!', '#NUM!', '#NULL!'}
        missing_codes = sum(str(row.get('Codproducto') or '').strip().upper() in bad_sku for row in rows)
        result = self.env['analytics.sales.sync'].action_import_excel(rows, self.import_mode,
                                                                       self.filename, sheet)
        if result.get('error'):
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': _('No se importó el Excel'), 'message': result['error'],
                               'type': 'danger', 'sticky': True}}
        message = _('Archivo: %s | Hoja: %s | Filas: %s | Nuevas: %s | Actualizadas: %s | Eliminadas: %s. API sin cambios.') % (
            self.filename, sheet, result['rows'], result['created'], result['updated'], result['removed'])
        if missing_codes:
            message += _(' %s productos sin código válido se conservaron con identificador temporal basado en su descripción.') % missing_codes
        return {'type': 'ir.actions.client', 'tag': 'display_notification',
                'params': {'title': _('Importación de Excel completada'),
                           'message': message,
                           'type': 'success', 'sticky': True,
                           'next': {'type': 'ir.actions.act_window_close'}}}
