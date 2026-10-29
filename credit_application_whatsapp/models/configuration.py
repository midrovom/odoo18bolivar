import re

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreditWhatsappConfiguration(models.Model):
    _name = 'credit.whatsapp.configuration'
    _description = 'WhatsApp - configuración por empresa'
    _rec_name = 'company_id'
    _order = 'company_id'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade', index=True,
                                 default=lambda self: self.env.company)
    enabled = fields.Boolean(string='Activar notificaciones automáticas', default=False)
    api_url = fields.Char(string='URL de envío', default='https://ia.callphoneecuador.com/api/v1/messages/send', required=True)
    api_key = fields.Char(string='API Key', copy=False, groups='custom_web_credito_conedera.group_credit_administrator')
    channel_id = fields.Integer(string='Channel ID', default=0)
    country_code = fields.Char(string='Prefijo internacional', default='593', required=True)
    text_key = fields.Selection([('message','message'),('caption','caption')],
                                string='Campo de mensaje para el proveedor', default='message', required=True,
                                help='El módulo antiguo envía el texto como message. Use caption solo si su API lo requiere.')
    include_media = fields.Boolean(string='Adjuntar imagen al mensaje', default=True)
    media_url = fields.Char(string='URL pública de imagen/archivo (opcional)')
    media_type = fields.Selection([('image','Imagen'),('document','Documento'),('video','Video'),('audio','Audio')],
                                  default='image', required=True)
    filename = fields.Char(default='estado_solicitud.png', string='Nombre del medio')
    notify_received = fields.Boolean(string='Recibida', default=True)
    notify_approved = fields.Boolean(string='Aprobada', default=True)
    notify_rejected = fields.Boolean(string='Rechazada', default=True)
    timeout = fields.Integer(string='Tiempo de espera en segundos', default=15)
    max_attempts = fields.Integer(string='Máximo de intentos', default=3)
    retry_minutes = fields.Integer(string='Minutos entre reintentos', default=10)
    batch_size = fields.Integer(string='Mensajes por lote', default=5)
    _sql_constraints = [('company_unique', 'unique(company_id)', 'Cada empresa solo puede tener una configuración WhatsApp.')]

    @api.constrains('api_url', 'country_code', 'timeout', 'max_attempts', 'retry_minutes', 'batch_size', 'channel_id')
    def _validate_settings(self):
        for r in self:
            if r.api_url and not r.api_url.startswith('https://'):
                raise ValidationError(_('La URL del API debe usar HTTPS.'))
            if not re.fullmatch(r'\d{1,5}', r.country_code or ''):
                raise ValidationError(_('El prefijo internacional debe contener entre 1 y 5 dígitos.'))
            if r.timeout < 3 or r.timeout > 120 or r.max_attempts < 1 or r.max_attempts > 20 or r.retry_minutes < 1 or r.batch_size < 1 or r.batch_size > 500:
                raise ValidationError(_('Revise los límites de espera, intentos y tamaño de lote.'))
            if r.channel_id < 0:
                raise ValidationError(_('El Channel ID no puede ser negativo.'))

    @api.model
    def _initialize_companies(self):
        Config = self.sudo()
        for company in self.env['res.company'].sudo().search([]):
            cfg = Config.search([('company_id', '=', company.id)], limit=1)
            if not cfg:
                cfg = Config.create({'company_id': company.id})
            self.env['credit.whatsapp.template'].sudo()._ensure_default_templates(company)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for r in records:
            self.env['credit.whatsapp.template'].sudo()._ensure_default_templates(r.company_id)
        return records

    def action_view_templates(self):
        self.ensure_one()
        return {'type':'ir.actions.act_window','name':_('Plantillas WhatsApp'),
                'res_model':'credit.whatsapp.template','view_mode':'list,form',
                'domain':[('company_id','=',self.company_id.id)],
                'context':{'default_company_id':self.company_id.id}}

class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        # Las compañías nuevas también tienen configuración separada, desactivada inicialmente.
        for company in companies:
            self.env['credit.whatsapp.configuration'].sudo().create({'company_id':company.id})
        return companies
