import re
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class ConederaCreditThemeWizard(models.TransientModel):
    _name = 'conedera.credit.theme.wizard'
    _description = 'Configuración de colores del portal de crédito'

    color_primary = fields.Char(string='Color principal (botones y encabezados)', required=True, default='#8F2F2F')
    color_hover = fields.Char(string='Color al pasar el cursor', required=True, default='#702121')
    color_soft = fields.Char(string='Fondo suave', required=True, default='#F8EDED')
    color_border = fields.Char(string='Color de los bordes', required=True, default='#E7E1DF')
    color_text = fields.Char(string='Color de los títulos', required=True, default='#702121')

    _theme_defaults = {
        'color_primary': '#8F2F2F',
        'color_hover': '#702121',
        'color_soft': '#F8EDED',
        'color_border': '#E7E1DF',
        'color_text': '#702121',
    }

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        params = self.env['ir.config_parameter'].sudo()
        for name, default in self._theme_defaults.items():
            if name in fields_list:
                result[name] = params.get_param('custom_web_credito_conedera.theme_' + name, default)
        return result

    @api.model
    def credit_css_variables(self):
        # No interpolar valores arbitrarios de configuración en HTML/CSS.
        params = self.env['ir.config_parameter'].sudo()
        css_names = {
            'color_primary': '--credit-red',
            'color_hover': '--credit-red-dark',
            'color_soft': '--credit-red-soft',
            'color_border': '--credit-border',
            'color_text': '--credit-heading',
        }
        variables = []
        for name, css_name in css_names.items():
            default = self._theme_defaults[name]
            value = params.get_param('custom_web_credito_conedera.theme_' + name, default) or default
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                value = default
            variables.append('%s: %s' % (css_name, value))
        return 'html:root { ' + '; '.join(variables) + '; }'

    def action_save(self):
        self.ensure_one()
        if not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            raise AccessError(_('Solo el administrador de crédito puede configurar los colores.'))
        params = self.env['ir.config_parameter'].sudo()
        for name in self._theme_defaults:
            value = (self[name] or '').strip()
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                raise ValidationError(_('Introduzca un color hexadecimal válido para %s (ejemplo: #8F2F2F).') % self._fields[name].string)
            params.set_param('custom_web_credito_conedera.theme_' + name, value.upper())
        return {'type': 'ir.actions.act_window_close'}
