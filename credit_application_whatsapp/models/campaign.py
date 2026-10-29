from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

class CreditWhatsappCampaign(models.Model):
    _name = 'credit.whatsapp.campaign'
    _description = 'WhatsApp - campaña de crédito'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self:self.env.company)
    event = fields.Selection([('received','Recibida'),('approved','Aprobada'),('rejected','Rechazada')],required=True)
    template_id = fields.Many2one('credit.whatsapp.template',required=True,
                                   domain="[('company_id','=',company_id),('event','=',event),('active','=',True)]")
    status = fields.Selection([('draft','Borrador'),('queued','En cola'),('done','Finalizada'),('cancelled','Cancelada')],default='draft',readonly=True)
    max_recipients = fields.Integer(string='Máximo de destinatarios',default=500,required=True)
    log_ids = fields.One2many('credit.whatsapp.log','campaign_id',readonly=True)
    total_count = fields.Integer(compute='_compute_counts')
    sent_count = fields.Integer(compute='_compute_counts')
    failed_count = fields.Integer(compute='_compute_counts')
    target_count = fields.Integer(compute='_compute_target_count')

    @api.depends('log_ids.status')
    def _compute_counts(self):
        for campaign in self:
            campaign.total_count=len(campaign.log_ids)
            campaign.sent_count=len(campaign.log_ids.filtered(lambda x:x.status=='sent'))
            campaign.failed_count=len(campaign.log_ids.filtered(lambda x:x.status=='failed'))

    def _target_domain(self):
        self.ensure_one()
        marker={'received':'is_initial','approved':'is_approved','rejected':'is_rejected'}[self.event]
        return [('company_id','=',self.company_id.id),('stage_id.'+marker,'=',True)]

    def _compute_target_count(self):
        for campaign in self:
            campaign.target_count=self.env['conedera.credit.application'].search_count(campaign._target_domain()) if campaign.event and campaign.company_id else 0

    @api.constrains('company_id','template_id','event','max_recipients')
    def _check_campaign(self):
        for c in self:
            if c.template_id and (c.template_id.company_id!=c.company_id or c.template_id.event!=c.event):
                raise ValidationError(_('La plantilla debe ser de la empresa y etapa seleccionadas.'))
            if c.max_recipients < 1 or c.max_recipients > 5000:
                raise ValidationError(_('El máximo de destinatarios debe estar entre 1 y 5000.'))

    def action_queue(self):
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            raise AccessError(_('Solo el administrador puede enviar campañas.'))
        for c in self:
            if c.company_id not in self.env.companies:
                raise AccessError(_('No tiene acceso a la empresa de esta campaña.'))
            if c.status!='draft':
                raise UserError(_('Esta campaña ya fue procesada.'))
            cfg=self.env['credit.whatsapp.configuration'].sudo().search([('company_id','=',c.company_id.id)],limit=1)
            if not cfg or not cfg.enabled:
                raise UserError(_('Active WhatsApp para la empresa antes de crear una campaña.'))
            applications=self.env['conedera.credit.application'].search(c._target_domain(),order='id asc',limit=c.max_recipients+1)
            if len(applications)>c.max_recipients:
                raise UserError(_('Existen más destinatarios que el límite configurado. Amplíe el límite conscientemente.'))
            for a in applications:
                a._whatsapp_queue(event=c.event,origin='campaign',template=c.template_id,
                                  unique_key='campaign:%s:application:%s' % (c.id,a.id),campaign=c)
            c.write({'status':'queued'})
        return True

    def action_cancel(self):
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            raise AccessError(_('Solo el administrador puede cancelar campañas.'))
        for c in self:
            if c.company_id not in self.env.companies:
                raise AccessError(_('No tiene acceso a la empresa de esta campaña.'))
            if c.status=='cancelled':continue
            c.log_ids.filtered(lambda x:x.status in ('pending','failed')).sudo().write({'status':'skipped','error_message':_('Campaña cancelada')})
            c.write({'status':'cancelled'})
        return True

    @api.model
    def _cron_finish_campaigns(self):
        for c in self.sudo().search([('status','=','queued')]):
            if not c.log_ids or not c.log_ids.filtered(lambda x:x.status in ('pending','processing') or (x.status=='failed' and x.next_retry)):
                # Mensajes fallidos con reintentos permanecen registrados en los logs.
                c.write({'status':'done'})
        return True
