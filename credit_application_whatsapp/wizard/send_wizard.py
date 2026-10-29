from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

class CreditWhatsappSendWizard(models.TransientModel):
    _name = 'credit.whatsapp.send.wizard'
    _description = 'Enviar WhatsApp manual de crédito'

    application_id = fields.Many2one('conedera.credit.application', required=True, readonly=True)
    company_id = fields.Many2one(related='application_id.company_id',readonly=True)
    event = fields.Selection([('received','Recibida'),('approved','Aprobada'),('rejected','Rechazada')],compute='_compute_event')
    template_id = fields.Many2one('credit.whatsapp.template',required=True,
        domain="[('company_id','=',company_id),('event','=',event),('active','=',True)]")
    preview = fields.Text(compute='_compute_preview')

    @api.depends('application_id.stage_id')
    def _compute_event(self):
        for w in self:
            w.event=w.application_id._whatsapp_event() if w.application_id else False

    @api.model
    def default_get(self, names):
        res=super().default_get(names)
        application_id=res.get('application_id') or self.env.context.get('default_application_id')
        if application_id:
            rec=self.env['conedera.credit.application'].browse(application_id)
            event=rec._whatsapp_event()
            template=self.env['credit.whatsapp.template'].search([
                ('company_id','=',rec.company_id.id),('event','=',event),('active','=',True)],limit=1)
            if template:
                res['template_id']=template.id
        return res

    @api.depends('template_id','application_id')
    def _compute_preview(self):
        for w in self:
            w.preview=w.template_id.render_message(w.application_id) if w.template_id and w.application_id else False

    def action_send(self):
        self.ensure_one()
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            raise AccessError(_('No tiene permiso para enviar mensajes.'))
        if not self.application_id._whatsapp_event() or self.template_id.event!=self.application_id._whatsapp_event():
            raise UserError(_('La plantilla no corresponde a la etapa actual.'))
        log=self.application_id._whatsapp_queue(event=self.template_id.event,
                                               origin='manual',template=self.template_id)
        if not log:
            raise UserError(_('No se pudo preparar el mensaje. Active la integración y verifique el celular.'))
        return {'type':'ir.actions.client','tag':'display_notification',
                'params':{'title':_('WhatsApp'),
                          'message':_('Mensaje agregado a la cola. Revise el historial de WhatsApp para verificar el envío.'),
                          'type':'success','sticky':False}}
