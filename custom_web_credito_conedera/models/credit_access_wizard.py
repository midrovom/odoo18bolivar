from odoo import fields, models, _
from odoo.exceptions import AccessError, UserError


class ConederaCreditAccessWizard(models.TransientModel):
    _name = 'conedera.credit.access.wizard'
    _description = 'Acceso especial a la solicitud de crédito'

    application_id = fields.Many2one('conedera.credit.application', required=True, readonly=True)
    destination = fields.Selection([
        ('application', 'Actualizar datos de la solicitud'),
        ('history', 'Historial de la solicitud'),
        ('documents', 'Ingreso de documentos del crédito'),
    ], string='Abrir', required=True, default='application')
    document_access_allowed = fields.Boolean(related='application_id.document_access_allowed', readonly=True)

    def action_open(self):
        self.ensure_one()
        if not (self.env.user.has_group('custom_web_credito_conedera.group_credit_manager')
                and self.env.user.has_group('custom_web_credito_conedera.group_credit_portal_correction')):
            raise AccessError(_('Se requiere el permiso especial de acceso a solicitudes de crédito.'))
        application = self.application_id.exists()
        if not application:
            raise UserError(_('No existe la solicitud seleccionada.'))
        if self.destination == 'documents':
            if not application.document_access_allowed:
                raise UserError(_('El ingreso de documentos solo se habilita después de aprobar la solicitud.'))
            return {
                'type': 'ir.actions.act_window', 'name': _('Documentos de %s') % application.name,
                'res_model': 'conedera.credit.documents', 'view_mode': 'list,form',
                'domain': [('application_id', '=', application.id)],
                'context': {'default_application_id': application.id}, 'target': 'current',
            }
        if self.destination == 'history':
            return {
                'type': 'ir.actions.act_window', 'name': _('Historial de %s') % application.name,
                'res_model': 'conedera.credit.stage.history', 'view_mode': 'list,form',
                'domain': [('application_id', '=', application.id)],
                'context': {'default_application_id': application.id, 'create': False, 'edit': False},
                'target': 'current',
            }
        if application.stage_id.is_approved or application.stage_id.is_rejected or application.stage_id.is_documents_received:
            raise UserError(_('La solicitud ya tiene una decisión y no permite corregir los datos iniciales.'))
        return {
            'type': 'ir.actions.act_window', 'name': _('Actualizar solicitud %s') % application.name,
            'res_model': 'conedera.credit.application', 'res_id': application.id,
            'view_mode': 'form', 'target': 'current',
            'context': {'form_view_initial_mode': 'edit'},
        }
