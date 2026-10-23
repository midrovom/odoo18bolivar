from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    credit_portal_correction_enabled = fields.Boolean(
        string='Puede actualizar solicitudes de crédito',
        compute='_compute_credit_portal_correction_enabled',
        inverse='_inverse_credit_portal_correction_enabled',
        help='Permiso especial: muestra Actualizar en historial y acceso rápido en el portal. '
             'En el backend permite utilizar el botón inteligente a los gestores de crédito.')

    @api.depends('groups_id')
    def _compute_credit_portal_correction_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_correction', raise_if_not_found=False)
        for user in self:
            user.credit_portal_correction_enabled = bool(group and group in user.groups_id)

    def _inverse_credit_portal_correction_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_correction', raise_if_not_found=False)
        if not group:
            return
        for user in self:
            command = (4, group.id) if user.credit_portal_correction_enabled else (3, group.id)
            user.write({'groups_id': [command]})
