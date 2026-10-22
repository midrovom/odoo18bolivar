from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ConederaCreditApplicantType(models.Model):
    _name = 'conedera.credit.applicant.type'
    _description = 'Tipo de solicitante de crédito'
    _order = 'sequence, name, id'

    name = fields.Char(string='Tipo de solicitante', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(
        string='ID único del tipo', copy=False, readonly=True, index=True,
        help='Identificador permanente (por ejemplo, natural, juridical, TC-000001). '
             'Puede utilizarse en integraciones y para localizar sus requisitos documentales.')
    note = fields.Text(string='Indicaciones para el solicitante')
    requirement_ids = fields.One2many('conedera.credit.document.requirement', 'applicant_type_id', string='Documentos exigidos')
    application_count = fields.Integer(compute='_compute_application_count', string='Solicitudes')

    _sql_constraints = [
        ('conedera_type_code_unique', 'unique(code)', 'Este código de tipo de solicitante ya está utilizado.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self.env['ir.sequence'].next_by_code('conedera.credit.applicant.type')
                if not vals['code']:
                    raise ValidationError(_('No se pudo generar el identificador del tipo de solicitante.'))
        return super().create(vals_list)

    def write(self, vals):
        if 'code' in vals and not self.env.context.get('credit_identifier_migration'):
            raise ValidationError(_('El ID único del tipo de solicitante es permanente y no puede modificarse.'))
        return super().write(vals)

    def _compute_application_count(self):
        for rec in self:
            rec.application_count = self.env['conedera.credit.application'].search_count([('applicant_type_id', '=', rec.id)])


class ConederaCreditDocumentRequirement(models.Model):
    _name = 'conedera.credit.document.requirement'
    _description = 'Documento configurable por tipo de solicitante'
    _order = 'sequence, id'

    name = fields.Char(string='Documento solicitado', required=True, translate=True)
    applicant_type_id = fields.Many2one('conedera.credit.applicant.type', required=True, ondelete='cascade', index=True, string='Tipo de solicitante')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    required = fields.Boolean(string='Obligatorio', default=True)
    only_if_spouse = fields.Boolean(string='Solo cuando se declara cónyuge', help='Mostrar y exigir el documento únicamente si la solicitud indica cónyuge.')
    image_only = fields.Boolean(string='Solo fotografía (JPG/PNG)', default=False)
    description = fields.Text(string='Instrucciones para cargar el archivo')
    legacy_field = fields.Char(string='Campo anterior (migración)', readonly=True, copy=False,
        help='Se utiliza para conservar archivos cargados en versiones anteriores.')

