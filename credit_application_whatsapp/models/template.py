import re
import string
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

EVENTS = [('received', 'Recibida'), ('approved','Aprobada'), ('rejected','Rechazada')]
ALLOWED = {'first_name', 'full_name', 'code', 'state', 'company', 'consult_url', 'date'}
TEXTS = {
 'received': 'Hola, {first_name}. Hemos recibido tu solicitud de crédito *{code}*. Nuestro equipo revisará la información. Consulta el seguimiento en: {consult_url}\n\n*{company}*',
 'approved': 'Hola, {first_name}. Tu solicitud de crédito *{code}* ha sido *APROBADA*. Revisa los próximos pasos en: {consult_url}\n\n*{company}*',
 'rejected': 'Hola, {first_name}. Te informamos que la solicitud de crédito *{code}* no fue aprobada en esta evaluación. Puedes consultar tu historial en: {consult_url}\n\n*{company}*',
}

class CreditWhatsappTemplate(models.Model):
    _name = 'credit.whatsapp.template'
    _description = 'WhatsApp - plantilla de crédito'
    _order = 'company_id, event, sequence, id'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade', default=lambda self: self.env.company, index=True)
    event = fields.Selection(EVENTS, string='Etapa', required=True)
    active = fields.Boolean(default=True)
    automatic = fields.Boolean(string='Plantilla automática', default=True)
    sequence = fields.Integer(default=10)
    body = fields.Text(string='Mensaje', required=True)
    notes = fields.Text(string='Notas')

    @api.constrains('body')
    def _validate_placeholders(self):
        formatter = string.Formatter()
        for rec in self:
            try:
                names = [n for _,n,_,_ in formatter.parse(rec.body or '') if n is not None]
            except ValueError as exc:
                raise ValidationError(_('Formato de variables inválido: %s') % exc)
            if any(n not in ALLOWED for n in names):
                raise ValidationError(_('Solo se admiten: %s') % ', '.join(sorted(ALLOWED)))

    @api.constrains('event','company_id','active','automatic')
    def _validate_one_automatic(self):
        for r in self:
            if r.active and r.automatic and self.sudo().search_count([
                ('id','!=',r.id),('company_id','=',r.company_id.id),('event','=',r.event),
                ('active','=',True),('automatic','=',True)
            ]):
                raise ValidationError(_('Solo puede existir una plantilla automática por etapa y empresa.'))

    @api.model
    def _ensure_default_templates(self, company):
        for event,label in EVENTS:
            if not self.search_count([('company_id','=',company.id),('event','=',event)]):
                self.create({'company_id':company.id,'event':event,'name':label,
                             'body':TEXTS[event], 'automatic':True})

    def _values(self, application):
        application.ensure_one()
        name = application.applicant_name or application.portal_user_id.name or _('Cliente')
        website = application.website_id
        base = (website.domain or '').strip() if website else ''
        if base and not base.startswith(('https://','http://')):
            base = 'https://' + base
        if not base:
            base = (self.env['ir.config_parameter'].sudo().get_param('web.base.url') or '').rstrip('/')
        # Enlace sin token: el portal exige autenticación para consultar el expediente.
        return {'first_name':name.split()[0], 'full_name':name,
                'code':application.name or '', 'state':dict(EVENTS).get(self.event,self.event),
                'company':application.company_id.name or '',
                'consult_url':base.rstrip('/') + '/my/credito/historial',
                'date':fields.Date.context_today(application).strftime('%d/%m/%Y')}

    def render_message(self, application):
        self.ensure_one()
        if application.company_id != self.company_id:
            raise ValidationError(_('La plantilla no pertenece a la empresa de la solicitud.'))
        return (self.body or '').format_map(self._values(application))
