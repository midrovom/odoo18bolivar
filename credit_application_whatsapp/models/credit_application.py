from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from .log import normalize_phone


class CreditApplicationWhatsapp(models.Model):
    _inherit = 'conedera.credit.application'

    whatsapp_log_ids = fields.One2many('credit.whatsapp.log','application_id',string='Mensajes WhatsApp',readonly=True)
    whatsapp_log_count = fields.Integer(compute='_compute_whatsapp_log_count')

    def _compute_whatsapp_log_count(self):
        Log=self.env['credit.whatsapp.log'].sudo()
        for rec in self:
            rec.whatsapp_log_count=Log.search_count([('application_id','=',rec.id)])

    def _whatsapp_event(self):
        self.ensure_one()
        if self.stage_id.is_initial:
            return 'received'
        if self.stage_id.is_approved:
            return 'approved'
        if self.stage_id.is_rejected:
            return 'rejected'
        return False

    def _whatsapp_queue(self, event=None, origin='automatic', template=None, unique_key=None, campaign=None):
        self.ensure_one()
        event=event or self._whatsapp_event()
        if not event or event not in ('received','approved','rejected'):
            return False
        cfg=self.env['credit.whatsapp.configuration'].sudo().search([('company_id','=',self.company_id.id)],limit=1)
        if not cfg or not cfg.enabled:
            return False
        if origin=='automatic' and not getattr(cfg,'notify_%s' % event):
            return False
        if not template:
            template=self.env['credit.whatsapp.template'].sudo().search([
                ('company_id','=',self.company_id.id),('event','=',event),
                ('active','=',True),('automatic','=',True)], order='sequence,id',limit=1)
        if not template or template.company_id != self.company_id or template.event != event:
            return False
        phone=normalize_phone(self.mobile, cfg.country_code)
        if not phone:
            self.sudo().message_post(body=_('WhatsApp omitido: número de celular inválido o ausente.'))
            return False
        Log=self.env['credit.whatsapp.log'].sudo()
        if unique_key:
            existing=Log.search([('unique_key','=',unique_key)],limit=1)
            if existing:
                return existing
        return Log.create({'application_id':self.id,'company_id':self.company_id.id,
                'template_id':template.id,'campaign_id':campaign.id if campaign else False,
                'event':event,'origin':origin,'recipient':phone,
                'body':template.render_message(self),'unique_key':unique_key or False})

    def _whatsapp_queue_stage_event(self):
        for rec in self:
            event=rec._whatsapp_event()
            if not event:
                continue
            history=rec.history_ids.sorted(key=lambda h:h.id,reverse=True)[:1]
            key='credit:%s:stage:%s:event:%s' % (rec.id, history.id if history else ('%s-%s' % (rec.stage_id.id,fields.Datetime.now())),event)
            rec._whatsapp_queue(event=event, unique_key=key)

    @api.model_create_multi
    def create(self, vals_list):
        records=super().create(vals_list)
        records._whatsapp_queue_stage_event()
        return records

    def write(self, vals):
        previous={r.id:r.stage_id.id for r in self} if 'stage_id' in vals else {}
        result=super().write(vals)
        if previous:
            for rec in self:
                if previous[rec.id] != rec.stage_id.id:
                    rec._whatsapp_queue_stage_event()
        return result

    def action_view_whatsapp_logs(self):
        self.ensure_one()
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_manager') or self.company_id not in self.env.companies:
            raise AccessError(_('No tiene permiso para consultar estos mensajes.'))
        return {'type':'ir.actions.act_window','name':_('Mensajes WhatsApp'),
                'res_model':'credit.whatsapp.log','view_mode':'list,form',
                'domain':[('application_id','=',self.id)],
                'context':{'default_application_id':self.id}}

    def action_open_whatsapp_wizard(self):
        self.ensure_one()
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator') or self.company_id not in self.env.companies:
            raise AccessError(_('No tiene permiso para enviar mensajes de esta empresa.'))
        if not self._whatsapp_event():
            raise UserError(_('Solo se admiten envíos para Recibida, Aprobada o Rechazada.'))
        return {'type':'ir.actions.act_window','name':_('Enviar WhatsApp'),
                'res_model':'credit.whatsapp.send.wizard', 'view_mode':'form', 'target':'new',
                'context':{'default_application_id':self.id}}
