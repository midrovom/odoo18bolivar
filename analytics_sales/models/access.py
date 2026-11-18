# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError

ROLE_GROUPS = {
    'tienda': 'analytics_sales.group_analytics_sales_tienda',
    'supervisor': 'analytics_sales.group_analytics_sales_supervisor',
    'administrador': 'analytics_sales.group_analytics_sales_admin',
}


class AnalyticsSalesUserAccess(models.Model):
    _name = 'analytics.sales.user.access'
    _description = 'Acceso a locales por usuario (Analytics Sales)'
    _order = 'company_id, user_id'

    user_id = fields.Many2one('res.users', string='Usuario Odoo', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company, index=True)
    role = fields.Selection([('tienda', 'Tienda'), ('supervisor', 'Supervisor'), ('administrador', 'Administrador')],
                            required=True, default='tienda')
    local_ids = fields.Many2many('analytics.sales.local', 'analytics_sales_access_local_rel', 'access_id', 'local_id',
                                 string='Locales autorizados', domain="[('company_id', '=', company_id)]")
    notes = fields.Char(string='Observación')

    _sql_constraints = [
        ('analytics_sales_access_unique', 'unique(user_id, company_id)',
         'El usuario ya tiene un perfil Analytics Sales en esta compañía.'),
    ]

    @api.constrains('local_ids', 'role', 'company_id', 'user_id')
    def _check_access_scope(self):
        for rec in self:
            if rec.company_id not in rec.user_id.company_ids:
                raise ValidationError(_('El usuario no tiene acceso a esta compañía.'))
            if rec.local_ids.filtered(lambda local: local.company_id != rec.company_id):
                raise ValidationError(_('Los nlocal deben pertenecer a la compañía del perfil.'))
            if rec.role != 'administrador' and not rec.local_ids:
                raise ValidationError(_('Tienda y supervisor requieren al menos un nlocal autorizado.'))

    def _check_profile_admin(self):
        self.env['analytics.sales.security'].check_admin()
        if self.filtered(lambda rec: rec.company_id != self.env.company):
            raise AccessError(_('Cambie a la compañía del perfil para gestionarlo.'))

    def _refresh_user_groups(self, users):
        for user in users.sudo():
            remaining_roles = set(self.sudo().search([('user_id', '=', user.id)]).mapped('role'))
            commands = []
            for role, xmlid in ROLE_GROUPS.items():
                grp = self.env.ref(xmlid)
                commands.append((4 if role in remaining_roles else 3, grp.id))
            user.write({'groups_id': commands})

    @api.model_create_multi
    def create(self, vals_list):
        self.env['analytics.sales.security'].check_admin()
        for vals in vals_list:
            if vals.get('company_id') and vals['company_id'] != self.env.company.id:
                raise AccessError(_('No puede asignar permisos en otra compañía.'))
        created = super().create(vals_list)
        created._refresh_user_groups(created.mapped('user_id'))
        return created

    def write(self, vals):
        self._check_profile_admin()
        if 'company_id' in vals and vals['company_id'] != self.env.company.id:
            raise AccessError(_('El perfil debe permanecer en la compañía actual.'))
        previous_users = self.mapped('user_id')
        result = super().write(vals)
        if {'user_id', 'role', 'company_id'} & set(vals):
            self._refresh_user_groups(previous_users | self.mapped('user_id'))
        return result

    def unlink(self):
        self._check_profile_admin()
        affected = self.mapped('user_id')
        result = super().unlink()
        self._refresh_user_groups(affected)
        return result


class AnalyticsSalesSecurity(models.AbstractModel):
    _name = 'analytics.sales.security'
    _description = 'Autorización central Analytics Sales'

    @api.model
    def _revoke_legacy_system_acl(self):
        """Clean permissions granted to Settings users by versions <= 1.1.14.

        ACLs loaded by a previous module version remain in ir.model.access
        even when their CSV rows are removed.  Called by data XML on every
        install and upgrade, after ir.model.access.csv has been processed.
        """
        legacy_ids = (
            'access_sales_local_system',
            'access_sales_assignment_system',
            'access_sales_move_system',
            'access_sales_settings_system',
            'access_sales_log_system',
            'access_sales_excel_import_system',
        )
        for xmlid in legacy_ids:
            record = self.env.ref('analytics_sales.%s' % xmlid, raise_if_not_found=False)
            if record and record._name == 'ir.model.access':
                record.sudo().unlink()
        return True

    @api.model
    def get_role_and_scope(self):
        """Authorize strictly by Analytics Sales groups + company profile.

        Having Odoo's technical Settings permissions never grants access.
        The company-specific profile takes precedence when a user has
        multiple Analytics roles across different companies.  Administrators
        explicitly assigned their Analytics group can bootstrap a new
        installation without having to create their own profile first.
        """
        user, company = self.env.user, self.env.company
        # Check actual group membership, not sudo-mode `has_group()`;
        # some service/superuser contexts bypass ordinary group checks.
        assigned_groups = set(user.sudo().groups_id.ids)
        if self.env.ref('base.group_user').id not in assigned_groups:
            raise AccessError(_('Analytics Sales está disponible únicamente para usuarios internos con uno de sus tres permisos.'))
        groups = {role: self.env.ref(xmlid).id for role, xmlid in ROLE_GROUPS.items()}
        if not any(group_id in assigned_groups for group_id in groups.values()):
            raise AccessError(_('No tiene permisos de Analytics Sales. Un administrador debe activar Administrador, Supervisor o Tienda en su usuario.'))

        profile_model = self.env['analytics.sales.user.access'].sudo()
        profile = profile_model.search([
            ('user_id', '=', user.id), ('company_id', '=', company.id)], limit=1)
        if profile:
            if groups[profile.role] not in assigned_groups:
                raise AccessError(_('El perfil Analytics Sales de esta compañía no coincide con los permisos del usuario.'))
            if profile.role != 'administrador' and not profile.local_ids:
                raise AccessError(_('Asigne al menos un local nlocal al perfil de Tienda o Supervisor.'))
            return (profile.role,
                    profile.local_ids.ids if profile.role != 'administrador' else None)

        # An explicit Analytics Administrator group (not base.group_system)
        # may configure Analytics Sales on first installation. A user with a
        # profile in another company MUST be assigned a profile here too:
        # otherwise a company-B admin could gain unscoped company-A access.
        if groups['administrador'] in assigned_groups and not profile_model.search_count([
            ('user_id', '=', user.id)]):
            return 'administrador', None

        raise AccessError(_('No tiene un perfil Analytics Sales para la compañía %s. '
                            'Solicite al Administrador que configure su perfil y locales autorizados.') % company.display_name)

    @api.model
    def check_admin(self):
        role, _ = self.get_role_and_scope()
        if role != 'administrador':
            raise AccessError(_('Solo el administrador Analytics Sales de esta compañía puede realizar esta acción.'))
        return True
