from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ConederaCreditApplicantType(models.Model):
    _name = 'conedera.credit.applicant.type'
    _description = 'Tipo de solicitante de crédito'
    _order = 'sequence, name, id'

    name = fields.Char(string='Tipo de solicitante', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    code = fields.Char(string='Código interno', copy=False, help='Identificador opcional para migrar registros históricos. No determina la documentación.')
    note = fields.Text(string='Indicaciones para el solicitante')
    requirement_ids = fields.One2many('conedera.credit.document.requirement', 'applicant_type_id', string='Documentos exigidos')
    application_count = fields.Integer(compute='_compute_application_count', string='Solicitudes')

    _sql_constraints = [
        ('conedera_type_code_unique', 'unique(code)', 'Este código de tipo de solicitante ya está utilizado.'),
    ]

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

