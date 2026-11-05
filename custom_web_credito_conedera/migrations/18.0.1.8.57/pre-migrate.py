"""Desactivar el permiso duplicado y la ACL de administrador de versiones anteriores.

Antes de cargar las vistas nuevas, retirar la vista heredada que referenciaba
el campo Boolean obsoleto; no alterar los grupos de ningún usuario ni las
solicitudes con permisos ya concedidos.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_ui_view AS view
           SET active = FALSE
          FROM ir_model_data AS xmlid
         WHERE xmlid.module = 'custom_web_credito_conedera'
           AND xmlid.name = 'view_users_credit_correction_inherit'
           AND xmlid.model = 'ir.ui.view'
           AND xmlid.res_id = view.id
    """)
    cr.execute("""
        UPDATE ir_model_access AS access
           SET perm_read = FALSE,
               perm_write = FALSE,
               perm_create = FALSE,
               perm_unlink = FALSE
          FROM ir_model_data AS xmlid
         WHERE xmlid.module = 'custom_web_credito_conedera'
           AND xmlid.name = 'access_conedera_credit_access_wizard_administrator'
           AND xmlid.model = 'ir.model.access'
           AND xmlid.res_id = access.id
    """)
