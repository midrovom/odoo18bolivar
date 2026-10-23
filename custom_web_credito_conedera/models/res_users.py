from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # Compatibilidad: el grupo legado no autoriza por sí solo actualizaciones del portal.
    credit_portal_correction_enabled = fields.Boolean(
        string='Permiso global anterior (sin efecto)',
        compute='_compute_credit_portal_correction_enabled',
        inverse='_inverse_credit_portal_correction_enabled',
    )
    credit_portal_permission_manager_enabled = fields.Boolean(
        string='Puede habilitar permisos del portal de crédito',
        compute='_compute_credit_portal_permission_manager_enabled',
        inverse='_inverse_credit_portal_permission_manager_enabled',
        help='Solo para usuarios internos que autorizan actualizaciones POR SOLICITUD.'
    )

    @api.depends('groups_id')
    def _compute_credit_portal_correction_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_correction', raise_if_not_found=False)
        for user in self:
            user.credit_portal_correction_enabled = bool(group and group in user.groups_id)

    def _inverse_credit_portal_correction_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_correction', raise_if_not_found=False)
        if group:
            for user in self:
                user.write({'groups_id': [(4 if user.credit_portal_correction_enabled else 3, group.id)]})

    @api.depends('groups_id')
    def _compute_credit_portal_permission_manager_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_update_manager', raise_if_not_found=False)
        for user in self:
            user.credit_portal_permission_manager_enabled = bool(group and group in user.groups_id)

    def _inverse_credit_portal_permission_manager_enabled(self):
        group = self.env.ref('custom_web_credito_conedera.group_credit_portal_update_manager', raise_if_not_found=False)
        if group:
            for user in self:
                # No permitir asignar privilegios internos a un usuario del portal.
                if user.credit_portal_permission_manager_enabled and user.share:
                    from odoo.exceptions import UserError
                    from odoo import _
                    raise UserError(_('Este permiso de administración solo es para usuarios internos.'))
                user.write({'groups_id': [(4 if user.credit_portal_permission_manager_enabled else 3, group.id)]})
