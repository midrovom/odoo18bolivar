import json
import logging
import re
from datetime import timedelta

import requests
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

STATUS = [('pending','Pendiente'),('processing','En proceso'),('sent','Enviado'),
          ('failed','Error'),('skipped','Omitido')]


def normalize_phone(phone, country_code):
    digits = re.sub(r'\D', '', phone or '')
    prefix = re.sub(r'\D', '', country_code or '593')
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith(prefix):
        normalized = digits
    elif digits.startswith('0'):
        normalized = prefix + digits[1:]
    else:
        normalized = prefix + digits
    return normalized if digits and 9 <= len(normalized) <= 15 else False


class CreditWhatsappLog(models.Model):
    _name = 'credit.whatsapp.log'
    _description = 'WhatsApp - historial de envíos de crédito'
    _order = 'create_date desc, id desc'

    application_id = fields.Many2one('conedera.credit.application', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='cascade')
    template_id = fields.Many2one('credit.whatsapp.template', ondelete='set null')
    campaign_id = fields.Many2one('credit.whatsapp.campaign', ondelete='set null')
    event = fields.Selection([('received','Recibida'),('approved','Aprobada'),('rejected','Rechazada')], required=True)
    origin = fields.Selection([('automatic','Automático'),('manual','Manual'),('campaign','Campaña')], required=True, default='automatic')
    unique_key = fields.Char(string='Identificador anti-duplicados', index=True, copy=False, readonly=True)
    recipient = fields.Char(string='Teléfono', required=True)
    body = fields.Text(string='Mensaje enviado', required=True)
    status = fields.Selection(STATUS, default='pending', index=True, required=True)
    attempts = fields.Integer(default=0, readonly=True)
    retryable = fields.Boolean(default=True, readonly=True)
    next_retry = fields.Datetime(index=True, readonly=True)
    sent_at = fields.Datetime(readonly=True)
    http_status = fields.Integer(readonly=True)
    response_text = fields.Text(readonly=True)
    error_message = fields.Text(readonly=True)
    payload_json = fields.Text(readonly=True)
    _sql_constraints = [('unique_key_uniq','unique(unique_key)','Este evento de WhatsApp ya fue registrado.')]

    def action_retry(self):
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator') or any(r.company_id not in self.env.companies for r in self):
            raise AccessError(_('No tiene permiso para reintentar mensajes de esta empresa.'))
        for log in self:
            if log.status == 'sent':
                continue
            log.sudo().write({'status':'pending','next_retry':False,'error_message':False,'retryable':True})
        return True

    def _send_one(self):
        self.ensure_one()
        if self.status in ('sent','skipped'):
            return
        cfg = self.env['credit.whatsapp.configuration'].sudo().search([('company_id','=',self.company_id.id)],limit=1)
        if not cfg or not cfg.enabled:
            self.sudo().write({'status':'skipped','error_message':_('La empresa tiene WhatsApp desactivado.')})
            return
        if not cfg.api_key or not cfg.api_url or not cfg.channel_id:
            self.sudo().write({'status':'failed','attempts':self.attempts+1,
                               'error_message':_('Configure API Key, URL y Channel ID.'), 'next_retry':False,'retryable':False})
            return
        payload = {'channelId':cfg.channel_id, 'to':self.recipient, cfg.text_key or 'message':self.body}
        if cfg.include_media:
            website = self.application_id.website_id
            domain = (website.domain or '').strip() if website else ''
            if domain and not domain.startswith(('https://', 'http://')):
                domain = 'https://' + domain
            base = domain or (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '')
            media_url = cfg.media_url or base.rstrip('/') + '/credit_application_whatsapp/static/src/img/status_update.png'
            payload.update({'mediaUrl':media_url, 'mediaType':cfg.media_type,
                            'filename':cfg.filename or 'estado_solicitud.png'})
        self.sudo().write({'status':'processing','attempts':self.attempts+1,
                           'payload_json':json.dumps(payload,ensure_ascii=False),'error_message':False})
        try:
            response = requests.post(cfg.api_url, json=payload, headers={
                'Authorization':'Bearer %s' % cfg.api_key,
                'Content-Type':'application/json','Accept':'application/json',
                'X-Idempotency-Key':self.unique_key or 'credit-wa-%s' % self.id,
            }, timeout=cfg.timeout)
            values={'http_status':response.status_code,'response_text':(response.text or '')[:4000]}
            if 200 <= response.status_code < 300:
                values.update({'status':'sent','sent_at':fields.Datetime.now(), 'next_retry':False,'error_message':False})
            else:
                values.update(self._failure(cfg, 'HTTP %s: %s' % (response.status_code, (response.text or '')[:300]),
                                            retryable=response.status_code in (408,409,425,429) or response.status_code >= 500))
        except requests.RequestException as exc:
            _logger.warning('No se pudo enviar WhatsApp de crédito %s: %s',self.application_id.id, exc)
            values=self._failure(cfg, str(exc), retryable=True)
        except Exception as exc:
            _logger.exception('Error inesperado en la integración WhatsApp')
            values=self._failure(cfg, str(exc), retryable=True)
        self.sudo().write(values)

    def _failure(self, cfg, reason, retryable=True):
        retry = retryable and self.attempts < cfg.max_attempts
        return {'status':'failed','error_message':reason,
                'next_retry': fields.Datetime.now()+timedelta(minutes=cfg.retry_minutes) if retry else False,
                'retryable': bool(retryable)}

    @api.model
    def _cron_process_queue(self):
        # Cada empresa define sus propios parámetros y límites de envío.
        configs=self.env['credit.whatsapp.configuration'].sudo().search([('enabled','=',True)])
        for cfg in configs:
            logs=self.sudo().search([('company_id','=',cfg.company_id.id),
                ('status','in',['pending','failed']),('attempts','<',cfg.max_attempts),('retryable','=',True),
                '|', ('next_retry','=',False),('next_retry','<=',fields.Datetime.now())],
                order='create_date asc, id asc',limit=cfg.batch_size)
            for log in logs:
                # Bloqueo por registro: evita que dos workers procesen el mismo envío.
                self.env.cr.execute('SELECT id FROM credit_whatsapp_log WHERE id = %s FOR UPDATE SKIP LOCKED', (log.id,))
                if not self.env.cr.fetchone():
                    continue
                log.invalidate_recordset(['status','attempts'])
                if log.status in ('pending','failed') and log.attempts < cfg.max_attempts:
                    log._send_one()
        return True
