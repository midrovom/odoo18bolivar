import logging
from markupsafe import escape

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError, UserError

from .credit_identity import valid_ecuador_mobile, valid_credit_identity, valid_ecuador_or_foreign_document, valid_ruc_length

_logger = logging.getLogger(__name__)


class ConederaCreditApplication(models.Model):
    _name = 'conedera.credit.application'
    _description = 'Solicitud de crédito CONEDERA S.A.'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string='Número de solicitud', required=True, copy=False, readonly=True, default='Nuevo', tracking=True, index=True)
    active = fields.Boolean(default=True)
    portal_user_id = fields.Many2one('res.users', string='Usuario del portal', required=True, readonly=True, index=True, ondelete='restrict')
    # Campo antiguo conservado exclusivamente para migrar solicitudes históricas.
    # No participa en las nuevas solicitudes ni condiciona los documentos.
    person_type = fields.Selection([
        ('natural', 'Persona natural'), ('juridical', 'Persona jurídica'),
    ], string='Tipo anterior (histórico)', readonly=True, copy=False)
    applicant_type_id = fields.Many2one(
        'conedera.credit.applicant.type', string='Tipo de solicitante',
        tracking=True, index=True, ondelete='restrict',
        help='Catálogo editable en Crédito CONEDERA > Tipos de solicitante.')
    application_place = fields.Char(string='Lugar de solicitud')
    identification = fields.Char(string='Documento del solicitante', required=True, tracking=True, index=True)
    identification_type = fields.Selection([('cedula', 'Cédula ecuatoriana'), ('ruc', 'RUC'), ('foreign', 'Cédula extranjera')], string='Tipo de documento', default='cedula', required=True, tracking=True)
    application_date = fields.Date(string='Lugar y fecha de solicitud', required=True, default=fields.Date.context_today)
    applicant_name = fields.Char(string='Nombres y apellidos del propietario o representante', required=True, tracking=True)
    applicant_email = fields.Char(string='Correo electrónico del propietario o representante', required=True)
    phone_fixed = fields.Char(string='Teléfono fijo')
    mobile = fields.Char(string='Celular', required=True)
    profession = fields.Char(string='Profesión')
    # Conservado como dato histórico; los nuevos registros utilizan el catálogo editable.
    marital_status = fields.Selection([
        ('single', 'Soltero/a'), ('married', 'Casado/a'), ('divorced', 'Divorciado/a'),
        ('widowed', 'Viudo/a'), ('free_union', 'Unión de hecho'), ('other', 'Otro'),
    ], string='Estado civil (anterior)', copy=False, readonly=True)
    marital_status_id = fields.Many2one(
        'conedera.credit.marital.status', string='Estado civil', ondelete='restrict', index=True,
        help='Estados civiles configurables en Crédito CONEDERA > Estados civiles.')
    foreign_residence_time = fields.Char(string='Tiempo de residencia (extranjero)')
    foreign_work_visa = fields.Selection([('yes', 'Sí'), ('no', 'No')], string='Visa de trabajo (extranjero)')
    spouse_name = fields.Char(string='Nombres y apellidos del cónyuge')
    spouse_identification = fields.Char(string='Cédula del cónyuge')
    spouse_profession = fields.Char(string='Profesión del cónyuge')
    dependents_count = fields.Integer(string='Número de cargas')
    home_address = fields.Char(string='Dirección domiciliaria')
    # Compatibilidad con las solicitudes anteriores. Nuevas solicitudes usan el catálogo.
    housing_type = fields.Selection([
        ('own', 'Propia'), ('rented', 'Alquilada'), ('family', 'Familiares'), ('mortgaged', 'Hipotecada'),
    ], string='Vivienda (anterior)', readonly=True, copy=False)
    housing_type_id = fields.Many2one(
        'conedera.credit.housing.type', string='Vivienda', index=True, ondelete='restrict',
        help='Opciones configurables desde Crédito CONEDERA > Tipos de vivienda.')
    vehicle_ids = fields.One2many('conedera.credit.vehicle', 'application_id', string='Vehículos del solicitante')
    legacy_vehicle_migrated = fields.Boolean(string='Vehículos históricos migrados', default=False, copy=False)

    vehicle1_brand = fields.Char(string='Vehículo 1 - marca')
    vehicle1_model = fields.Char(string='Vehículo 1 - modelo')
    vehicle1_year = fields.Char(string='Vehículo 1 - año')
    vehicle1_value = fields.Monetary(string='Vehículo 1 - avalúo comercial', currency_field='currency_id')
    vehicle2_brand = fields.Char(string='Vehículo 2 - marca')
    vehicle2_model = fields.Char(string='Vehículo 2 - modelo')
    vehicle2_year = fields.Char(string='Vehículo 2 - año')
    vehicle2_value = fields.Monetary(string='Vehículo 2 - avalúo comercial', currency_field='currency_id')

    business_name = fields.Char(string='Nombre o razón social', required=True, tracking=True)
    legal_representative = fields.Char(string='Nombre del representante legal')
    business_ruc = fields.Char(string='RUC del negocio', required=True, index=True)
    province = fields.Char(string='Provincia')
    canton = fields.Char(string='Cantón')
    city = fields.Char(string='Ciudad')
    business_address = fields.Char(string='Dirección de la empresa', required=True)
    business_phone = fields.Char(string='Teléfono de la empresa')
    representative_email = fields.Char(string='Correo del representante legal')
    activity_start_date = fields.Date(string='Fecha de inicio de actividades')
    business_local_type = fields.Selection([
        ('own', 'Propio'), ('rented', 'Alquilado'), ('family', 'Familiar'), ('mortgaged', 'Hipotecado'),
    ], string='Local')
    monthly_sales = fields.Monetary(string='Promedio de ventas mensuales', currency_field='currency_id')
    social_capital = fields.Monetary(string='Capital social', currency_field='currency_id')
    invoice_email = fields.Char(string='Correo para facturas')
    assets_amount = fields.Monetary(string='Activos (monto aproximado)', currency_field='currency_id')
    monthly_income = fields.Monetary(string='Ingresos mensuales', currency_field='currency_id')
    liabilities_amount = fields.Monetary(string='Pasivos (monto aproximado)', currency_field='currency_id')
    monthly_expenses = fields.Monetary(string='Gastos mensuales', currency_field='currency_id')
    authorized_buyer_name = fields.Char(string='Persona autorizada a comprar')
    authorized_buyer_identification = fields.Char(string='Cédula de persona autorizada a comprar')
    authorized_buyer_email = fields.Char(string='Correo de persona autorizada a comprar')
    authorized_pickup_name = fields.Char(string='Persona autorizada a retirar mercadería')
    authorized_pickup_identification = fields.Char(string='Cédula de persona autorizada a retirar mercadería')
    business_latitude = fields.Float(string='Latitud del negocio', digits=(10, 7))
    business_longitude = fields.Float(string='Longitud del negocio', digits=(10, 7))
    # Compatibilidad temporal con vistas almacenadas de versiones anteriores.
    # No se muestra en el portal, no se solicita y no se utiliza para ubicación.
    maps_url = fields.Char(string='Enlace histórico de ubicación (en desuso)', readonly=True, copy=False)


    employment_company = fields.Char(string='Empresa donde trabaja (relación de dependencia)')
    employment_activity = fields.Char(string='Actividad de la empresa')
    employment_address = fields.Char(string='Dirección de la empresa donde trabaja')
    employment_phone = fields.Char(string='Teléfono de empresa donde trabaja')
    employment_start_date = fields.Date(string='Fecha de ingreso al empleo')
    employment_position = fields.Char(string='Cargo')
    employment_salary = fields.Monetary(string='Sueldo', currency_field='currency_id')

    reference_ids = fields.One2many('conedera.credit.reference', 'application_id', string='Referencias')
    history_ids = fields.One2many('conedera.credit.stage.history', 'application_id', string='Historial de etapas', readonly=True)
    document_ids = fields.One2many('conedera.credit.documents', 'application_id', string='Documentos solicitados', copy=False)
    document_complete = fields.Boolean(string='Documentación completa', compute='_compute_document_complete')

    stage_id = fields.Many2one(
        'conedera.credit.stage', string='Etapa', tracking=True, index=True,
        group_expand='_read_group_stage_ids', ondelete='restrict',
        default=lambda self: self.env['conedera.credit.stage'].search([('is_initial', '=', True)], order='sequence,id', limit=1),
    )
    verification_status = fields.Selection([('pending', 'Pendiente'), ('in_progress', 'En verificación'), ('verified', 'Verificado'), ('failed', 'No conforme')], string='Estado de verificación del negocio', default='pending', required=True, tracking=True, copy=False, index=True, help='Se gestiona en paralelo con la etapa de revisión del crédito.')
    verification_completed_at = fields.Datetime(string='Fecha de verificación', readonly=True, copy=False)
    documents_unlocked = fields.Boolean(string='Ingreso documental habilitado', default=False, copy=False, readonly=True, tracking=True)
    document_access_allowed = fields.Boolean(
        string='Puede ingresar documentos', compute='_compute_document_access_allowed',
        help='Solo está disponible tras aprobar la solicitud, mientras siga aprobada o esté en la fase de recepción documental.')
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self: self.env.company.currency_id, required=True)
    declaration_accepted = fields.Boolean(string='Declaración y autorización general aceptada', required=True, default=False, tracking=True)
    prior_commercial_relationship_accepted = fields.Boolean(string='Acepta cláusula de relación comercial previa', default=False, tracking=True)
    electronic_service_accepted = fields.Boolean(string='Acepta citación telemática (Art. 55.1 COGEP)', default=False, tracking=True)
    credit_bureau_authorized = fields.Boolean(string='Autoriza consulta de score en cualquier buró/plataforma autorizada', default=False, tracking=True)
    company_signature_stamp_acknowledged = fields.Boolean(string='Conoce requisito de firma y sello de CONEDERA', default=False, tracking=True)
    additional_financial_documents_accepted = fields.Boolean(string='Acepta entregar declaraciones IVA/renta y certificado bancario', default=False, tracking=True)
    declaration_date = fields.Datetime(string='Fecha de aceptación', readonly=True, copy=False)

    # Verificación interna de ubicación y negocio: estos campos solo se completan en Odoo.
    verification_province = fields.Char(string='Provincia de verificación')
    verification_city_canton_parish = fields.Char(string='Ciudad / cantón / parroquia (histórico)')
    verification_city = fields.Char(string='Ciudad verificada')
    verification_canton = fields.Char(string='Cantón verificado')
    verification_parish = fields.Char(string='Parroquia verificada')
    verification_neighborhood = fields.Char(string='Barrio')
    verification_address = fields.Char(string='Dirección verificada')
    verification_house_number = fields.Char(string='Número de casa')
    verification_reference = fields.Char(string='Referencia de ubicación')
    verification_sketch = fields.Binary(string='Croquis del cliente', attachment=True)
    verification_sketch_filename = fields.Char(string='Archivo del croquis')
    verification_zone = fields.Selection([('urban', 'Urbana'), ('peripheral', 'Periférica'), ('rural', 'Rural')], string='Zona')
    verification_local_state = fields.Selection([('very_good', 'Muy bueno'), ('good', 'Bueno'), ('regular', 'Regular'), ('bad', 'Malo')], string='Estado del local')
    interviewed_person = fields.Char(string='Persona entrevistada')
    interviewed_relationship = fields.Char(string='Relación / parentesco')
    inspection_done = fields.Selection([('yes', 'Sí'), ('no', 'No')], string='Se realizó la inspección')
    address_found = fields.Selection([('yes', 'Sí'), ('no', 'No')], string='Se encontró la dirección')
    client_lives_there = fields.Selection([('yes', 'Sí'), ('no', 'No')], string='El cliente vive en esa dirección')
    sketch_needed = fields.Selection([('yes', 'Sí'), ('no', 'No')], string='Necesita croquis')
    verifier_name = fields.Char(string='Nombre del verificador')
    verifier_signature = fields.Binary(string='Firma del verificador', attachment=True)
    verifier_signature_filename = fields.Char(string='Archivo de firma')

    _sql_constraints = [
        ('conedera_credit_application_name_uniq', 'unique(name)', 'El número de solicitud debe ser único.'),
    ]

    def action_print_credit_application(self):
        """Descarga de solicitud y verificación siguiendo el formato CONEDERA."""
        self.ensure_one()
        return self.env.ref('custom_web_credito_conedera.action_report_credit_application').report_action(self)

    credit_is_admin = fields.Boolean(compute='_compute_credit_is_admin', string='Edición completa habilitada')

    @api.depends_context('uid')
    def _compute_credit_is_admin(self):
        permitted = self.env.su or self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator')
        for application in self:
            application.credit_is_admin = bool(permitted)

    # El usuario de crédito SOLO puede cambiar la etapa y los campos de verificación
    # del negocio. Protegido en ORM además de en las vistas (RPC/importaciones).
    _credit_reviewer_writable = frozenset({
        'stage_id', 'verification_status', 'verification_completed_at',
        'verification_province', 'verification_city_canton_parish',
        'verification_city', 'verification_canton', 'verification_parish',
        'verification_neighborhood', 'verification_address',
        'verification_house_number', 'verification_reference',
        'verification_sketch', 'verification_sketch_filename',
        'verification_zone', 'verification_local_state',
        'interviewed_person', 'interviewed_relationship',
        'inspection_done', 'address_found', 'client_lives_there',
        'sketch_needed', 'verifier_name', 'verifier_signature',
        'verifier_signature_filename',
    })

    def _check_reviewer_values(self, values):
        if self.env.su or self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            return
        if self.env.user.has_group('custom_web_credito_conedera.group_credit_manager'):
            forbidden = set(values).difference(self._credit_reviewer_writable)
            if forbidden:
                raise AccessError(_('El usuario de crédito solo puede cambiar la etapa y completar la verificación del negocio. Campos no autorizados: %s') % ', '.join(sorted(forbidden)))

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return self.env['conedera.credit.stage'].search([('active', '=', True)], order=order or 'sequence, id')

    @api.depends('document_ids.is_complete', 'document_ids.document_line_ids.file')
    def _compute_document_complete(self):
        for record in self:
            docs = record.document_ids[:1]
            record.document_complete = bool(docs and docs.is_complete)

    # Permiso POR SOLICITUD como custom_web_hr_historial_postulaciones.
    # El grupo del usuario no autoriza a modificar expedientes ajenos o sin habilitar.
    portal_history_consumed_at = fields.Datetime(string='Última corrección autorizada del portal', readonly=True, copy=False)
    portal_update_scope = fields.Selection([
        ('none', 'Ninguna sección'),
        ('history', 'Historial de solicitudes (actualizar formulario)'),
        ('documentation', 'Ingreso de documentos (actualizar archivos)'),
        ('both', 'Historial + documentación'),
    ], string='Sección habilitada para actualizar desde el portal',
       required=True, default='none', copy=False, tracking=True, index=True)
    portal_update_allowed = fields.Boolean(
        string='Actualización desde portal habilitada', compute='_compute_portal_update_allowed',
        store=True, copy=False)
    portal_update_allowed_at = fields.Datetime(
        string='Permiso actualizado el', copy=False, readonly=True)
    portal_update_allowed_by = fields.Many2one(
        'res.users', string='Permiso actualizado por', readonly=True, copy=False)

    @api.depends('portal_update_scope')
    def _compute_portal_update_allowed(self):
        for record in self:
            record.portal_update_allowed = record.portal_update_scope not in (False, 'none')

    def portal_can_update_history(self):
        self.ensure_one()
        return self.portal_update_scope in ('history', 'both')

    def portal_can_update_documentation(self):
        self.ensure_one()
        return self.portal_update_scope in ('documentation', 'both')

    credit_access_button_visible = fields.Boolean(
        string='Puede conceder permisos del portal', compute='_compute_credit_access_button_visible'
    )

    @api.depends('portal_user_id')
    @api.depends_context('uid')
    def _compute_credit_access_button_visible(self):
        authorized = self.env.user.has_group(
            'custom_web_credito_conedera.group_credit_portal_update_manager')
        for record in self:
            record.credit_access_button_visible = bool(authorized and record.portal_user_id)

    @api.depends('documents_unlocked', 'stage_id.is_approved', 'stage_id.is_documents_received', 'history_ids.stage_id.is_approved')
    def _compute_document_access_allowed(self):
        for record in self:
            approval_recorded = bool(record.history_ids.filtered(lambda h: h.stage_id.is_approved))
            record.document_access_allowed = bool(
                record.documents_unlocked and record.stage_id and
                (record.stage_id.is_approved or
                 (record.stage_id.is_documents_received and approval_recorded))
            )

    @api.model
    def _blocking_application(self, user_id, exclude_id=False):
        domain = [('portal_user_id', '=', user_id),
                  ('stage_id.is_approved', '=', False), ('stage_id.is_rejected', '=', False),
                  ('documents_unlocked', '=', False)]
        if exclude_id:
            domain.append(('id', '!=', exclude_id))
        return self.with_context(active_test=False).sudo().search(domain, limit=1)

    @api.constrains('verification_status', 'stage_id', 'inspection_done', 'address_found', 'verifier_name')
    def _check_credit_decision(self):
        for record in self:
            if record.stage_id.is_approved and (record.verification_status != 'verified' or
                    record.inspection_done != 'yes' or record.address_found != 'yes' or
                    not record.verifier_name or not record.verification_address):
                raise ValidationError(_('Antes de aprobar debe completar la verificación del negocio: resultado Verificado, inspección realizada, dirección localizada, dirección verificada y nombre del verificador.'))
            if record.stage_id.is_rejected and record.verification_status not in ('verified', 'failed'):
                raise ValidationError(_('Antes de rechazar debe finalizar la verificación del negocio como Verificado o No conforme.'))

    @api.model_create_multi
    def create(self, vals_list):
        Stage = self.env['conedera.credit.stage']
        required_consents = (
            'declaration_accepted', 'prior_commercial_relationship_accepted',
            'electronic_service_accepted', 'credit_bureau_authorized',
            'company_signature_stamp_acknowledged', 'additional_financial_documents_accepted',
        )
        # Serializar por usuario para evitar dos solicitudes simultáneas desde dos pestañas.
        for user_id in sorted({v.get('portal_user_id') for v in vals_list if v.get('portal_user_id')}):
            self.env.cr.execute('SELECT id FROM res_users WHERE id = %s FOR UPDATE', (user_id,))
            if self._blocking_application(user_id):
                raise ValidationError(_('Ya tiene una solicitud en trámite. Solo podrá registrar otra cuando la anterior esté aprobada o rechazada.'))
        seen_users = set()
        for vals in vals_list:
            user_id = vals.get('portal_user_id')
            if user_id in seen_users:
                raise ValidationError(_('Solo puede crear una solicitud en trámite por usuario.'))
            seen_users.add(user_id)
            if not all(vals.get(field) for field in required_consents):
                raise ValidationError(_('Para guardar una nueva solicitud debe aceptar la declaración general y todas las condiciones adicionales.'))
            if not vals.get('applicant_type_id'):
                raise ValidationError(_('Seleccione un tipo de solicitante configurado.'))
            if vals.get('name', 'Nuevo') == 'Nuevo':
                vals['name'] = self.env['ir.sequence'].next_by_code('conedera.credit.application') or _('Nuevo')
            if not vals.get('stage_id'):
                initial = Stage.search([('is_initial', '=', True), ('active', '=', True)], order='sequence,id', limit=1)
                if not initial:
                    initial = Stage.search([('active', '=', True)], order='sequence,id', limit=1)
                if initial:
                    vals['stage_id'] = initial.id
            stage = Stage.browse(vals.get('stage_id')) if vals.get('stage_id') else Stage
            if stage and stage.is_documents_received:
                raise ValidationError(_('La recepción de documentos solo puede ocurrir después de aprobar una solicitud existente.'))
            # El campo no puede habilitarse manualmente desde create/ORM.
            vals['documents_unlocked'] = bool(stage and stage.is_approved)
            if vals.get('declaration_accepted'):
                vals['declaration_date'] = fields.Datetime.now()
        records = super().create(vals_list)
        for record in records:
            if record.stage_id:
                self.env['conedera.credit.stage.history'].sudo().create({
                    'application_id': record.id,
                    'stage_id': record.stage_id.id,
                    'user_id': self.env.user.id,
                    'notes': _('Solicitud registrada desde el portal'),
                    'visible_to_portal': True,
                })
            record.message_post(body=_('Solicitud registrada. Etapa inicial: %s') % escape(record.stage_id.name or ''))
        return records

    def write(self, vals):
        self._check_reviewer_values(vals)
        protected_consents = (
            'declaration_accepted', 'prior_commercial_relationship_accepted',
            'electronic_service_accepted', 'credit_bureau_authorized',
            'company_signature_stamp_acknowledged', 'additional_financial_documents_accepted',
        )
        if any(field in vals and not vals[field] for field in protected_consents):
            raise ValidationError(_('No es posible quitar una aceptación registrada en una solicitud de crédito.'))
        if 'verification_status' in vals and vals['verification_status'] in ('verified', 'failed'):
            vals = dict(vals, verification_completed_at=fields.Datetime.now())
        if 'applicant_type_id' in vals and not vals['applicant_type_id']:
            raise ValidationError(_('El tipo de solicitante es obligatorio.'))
        if 'applicant_type_id' in vals:
            for record in self:
                if record.document_ids and record.applicant_type_id and record.applicant_type_id.id != vals['applicant_type_id']:
                    raise ValidationError(_('No cambie el tipo de solicitante de una solicitud que ya contiene documentación.'))
        previous_stages = {record.id: record.stage_id for record in self} if 'stage_id' in vals else {}
        values = dict(vals)
        if 'stage_id' in values:
            new_stage = self.env['conedera.credit.stage'].browse(values.get('stage_id'))
            if new_stage.is_documents_received:
                for record in self:
                    approved_before = bool(record.stage_id.is_approved or (
                        record.documents_unlocked and record.stage_id.is_documents_received and
                        any(h.stage_id.is_approved for h in record.history_ids)
                    ))
                    if not approved_before:
                        raise ValidationError(_('No puede ingresar documentación sin la aprobación previa de la solicitud.'))
                values['documents_unlocked'] = True
            else:
                # Impedir que un estado 'En revisión' conserve el indicador de
                # documentos habilitados cuando se revierte una aprobación.
                values['documents_unlocked'] = bool(new_stage.is_approved)
        elif 'documents_unlocked' in values:
            # Nadie debe habilitar documentos manualmente antes de la aprobación.
            for record in self:
                if values['documents_unlocked'] and not (
                    record.stage_id.is_approved or record.stage_id.is_documents_received
                ):
                    raise ValidationError(_('Solo la etapa Aprobada puede habilitar el ingreso de documentos.'))
        if values.get('declaration_accepted'):
            values.setdefault('declaration_date', fields.Datetime.now())
        result = super().write(values)
        if 'stage_id' in vals:
            for record in self:
                old_stage = previous_stages.get(record.id)
                if old_stage.id == record.stage_id.id:
                    continue
                self.env['conedera.credit.stage.history'].sudo().create({
                    'application_id': record.id,
                    'stage_id': record.stage_id.id,
                    'user_id': self.env.user.id,
                    'notes': _('Etapa actualizada de "%s" a "%s"') % (old_stage.name or '-', record.stage_id.name or '-'),
                    'visible_to_portal': True,
                })
                record.message_post(body=_('La solicitud cambió de etapa: <b>%s</b> → <b>%s</b>.') % (escape(old_stage.name or '-'), escape(record.stage_id.name or '-')))
                record._send_stage_notification(old_stage, record.stage_id)
        return result

    def _send_stage_notification(self, old_stage, new_stage):
        self.ensure_one()
        email = self.portal_user_id.email or self.portal_user_id.login
        if not email:
            return
        try:
            body = _(
                '<p>Estimado/a %(name)s:</p>'
                '<p>La solicitud de crédito <b>%(number)s</b> registra un cambio de etapa.</p>'
                '<p>Estado anterior: %(old)s<br/>Estado actual: <b>%(new)s</b></p>'
                '<p>Puede consultar el historial ingresando al portal de CONEDERA.</p>'
            ) % {
                'name': escape(self.applicant_name or self.portal_user_id.name or ''),
                'number': escape(self.name or ''),
                'old': escape(old_stage.name or '-'),
                'new': escape(new_stage.name or '-'),
            }
            # Usar el SMTP independiente del módulo de crédito y su smtp_user
            # como remitente. No reutilizar ni alterar la configuración de RR. HH.
            credit_mail_server = self.env['ir.mail_server'].sudo().get_conedera_credit_mail_server()
            mail = self.env['mail.mail'].sudo().create({
                'subject': _('Actualización de solicitud de crédito %s') % self.name,
                'body_html': body,
                'email_to': email,
                'email_from': (credit_mail_server.smtp_user or '').strip(),
                'mail_server_id': credit_mail_server.id,
            })
            mail.send()
        except Exception:
            _logger.exception('No se pudo notificar por correo la etapa de solicitud %s', self.name)

    def action_mark_documentation_received(self):
        if not self.env.su and not self.env.user.has_group('custom_web_credito_conedera.group_credit_administrator'):
            raise AccessError(_('Solo el administrador de crédito puede marcar la documentación como recibida.'))
        for record in self:
            if not record.document_access_allowed or not record.document_complete:
                raise UserError(_('La solicitud debe estar aprobada y tener completa la documentación antes de registrarla como recibida.'))
        stage = self.env['conedera.credit.stage'].search([
            ('is_documents_received', '=', True), ('active', '=', True),
        ], order='sequence, id', limit=1)
        if not stage:
            raise ValidationError(_('Configure una etapa marcada como «Documentación recibida» antes de continuar.'))
        for record in self:
            record.stage_id = stage

    def action_open_portal_update_wizard(self):
        """Botón inteligente y de cabecera, igual al permiso de postulaciones."""
        self.ensure_one()
        if not self.env.user.has_group(
                'custom_web_credito_conedera.group_credit_portal_update_manager'):
            raise AccessError(_('No puede gestionar permisos de actualización del portal de crédito.'))
        if not self.portal_user_id:
            raise UserError(_('Esta solicitud no tiene un usuario de portal asociado.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Habilitar permiso del portal'),
            'res_model': 'conedera.credit.access.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_application_id': self.id,
                'default_portal_update_scope': self.portal_update_scope or 'none',
            },
        }

    # Mantiene compatible la acción del botón de versiones anteriores.
    def action_open_access_wizard(self):
        return self.action_open_portal_update_wizard()

    def action_open_portal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/my/credito/%s' % self.id,
            'target': 'new',
        }

    @api.constrains('identification', 'identification_type', 'spouse_identification', 'authorized_buyer_identification', 'authorized_pickup_identification', 'mobile', 'business_ruc', 'marital_status_id', 'spouse_name', 'spouse_profession', 'business_latitude', 'business_longitude')
    def _check_ecuador_contact_fields(self):
        # No bloquear actualizaciones de catálogos para expedientes históricos
        # incompletos que ya existían antes de introducir estos requisitos.
        if self.env.context.get('credit_catalog_migration'):
            return
        for record in self:
            if record.identification and not valid_credit_identity(record.identification.strip(), record.identification_type):
                raise ValidationError(_('El documento del solicitante no cumple la validación del tipo seleccionado.'))
            if record.business_ruc and not valid_ruc_length(record.business_ruc.strip()):
                raise ValidationError(_('El RUC del negocio debe tener exactamente 13 dígitos numéricos.'))
            if record.mobile and not valid_ecuador_mobile(record.mobile.strip()):
                raise ValidationError(_('El celular debe tener exactamente 10 dígitos numéricos.'))
            if record.spouse_identification and not valid_ecuador_or_foreign_document(record.spouse_identification.strip()):
                raise ValidationError(_('El documento del cónyuge debe contener exactamente 10 dígitos; se admite cédula ecuatoriana o documento extranjero numérico.'))
            for field_name, label in (
                ('authorized_buyer_identification', _('persona autorizada a comprar')),
                ('authorized_pickup_identification', _('persona autorizada a retirar mercadería')),
            ):
                document = (record[field_name] or '').strip()
                if document and not valid_ecuador_or_foreign_document(document):
                    raise ValidationError(_(
                        'El documento de %(person)s debe tener 10 dígitos numéricos; '
                        'se valida primero como cédula ecuatoriana y, si no corresponde, como documento extranjero.'
                    ) % {'person': label})
            needs_spouse = record.marital_status_id.requires_spouse
            if needs_spouse and not all((record.spouse_name, record.spouse_identification, record.spouse_profession)):
                raise ValidationError(_('Para casado/a o unión de hecho complete nombres, documento y profesión del cónyuge.'))
            if (record.business_latitude or record.business_longitude) and not (-90 <= record.business_latitude <= 90 and -180 <= record.business_longitude <= 180):
                raise ValidationError(_('La latitud debe estar entre -90 y 90, y la longitud entre -180 y 180.'))

    @api.constrains('dependents_count', 'monthly_sales', 'social_capital', 'assets_amount', 'monthly_income', 'liabilities_amount', 'monthly_expenses', 'vehicle1_value', 'vehicle2_value', 'employment_salary')
    def _check_non_negative_amounts(self):
        for record in self:
            if record.dependents_count < 0:
                raise ValidationError(_('El número de cargas no puede ser negativo.'))
            for field_name in ('monthly_sales', 'social_capital', 'assets_amount', 'monthly_income', 'liabilities_amount', 'monthly_expenses', 'vehicle1_value', 'vehicle2_value', 'employment_salary'):
                if record[field_name] < 0:
                    raise ValidationError(_('Los montos de la solicitud no pueden ser negativos.'))

    @api.model
    def _migrate_credit_configuration(self):
        """Migración repetible al actualizar: enlaza solicitudes y conserva archivos antiguos."""
        Type = self.env['conedera.credit.applicant.type'].sudo()
        mapping = {
            'natural': Type.search([('code', '=', 'natural')], limit=1),
            'juridical': Type.search([('code', '=', 'juridical')], limit=1),
        }
        for old_code, applicant_type in mapping.items():
            if not applicant_type:
                continue
            applications = self.sudo().search([
                ('applicant_type_id', '=', False), ('person_type', '=', old_code),
            ])
            if applications:
                applications.write({'applicant_type_id': applicant_type.id})

        # Migración de identificaciones históricas: antes se aceptaba cédula o RUC.
        self.env.cr.execute("""UPDATE conedera_credit_application
            SET identification_type = CASE WHEN length(identification) = 13 THEN 'ruc' ELSE 'cedula' END
            WHERE identification_type IS NULL
               OR (identification_type = 'cedula' AND length(identification) = 13)""")
        # La etapa de verificación antigua deja de ser una fase obligatoria
        # del kanban: ahora tiene estado independiente en cada solicitud.
        old_verification_stage = self.env.ref('custom_web_credito_conedera.stage_credit_verification', raise_if_not_found=False)
        review_stage = self.env.ref('custom_web_credito_conedera.stage_credit_review', raise_if_not_found=False)
        if old_verification_stage and review_stage:
            # La antigua etapa era secuencial. Volver a revisión preservando
            # una marca independiente para los expedientes que ya la utilizaban.
            self.env.cr.execute("""UPDATE conedera_credit_application
                SET stage_id = %s, verification_status = 'in_progress'
                WHERE stage_id = %s RETURNING id""", (review_stage.id, old_verification_stage.id))
            migrated_ids = [row[0] for row in self.env.cr.fetchall()]
            if migrated_ids:
                self.invalidate_model(['stage_id', 'verification_status'])
                for application_id in migrated_ids:
                    self.env['conedera.credit.stage.history'].sudo().create({
                        'application_id': application_id, 'stage_id': review_stage.id,
                        'user_id': self.env.user.id,
                        'notes': _('Migración: revisión y verificación del negocio funcionan en paralelo.'),
                        'visible_to_portal': True,
                    })
        if old_verification_stage and old_verification_stage.active:
            old_verification_stage.active = False
        
        # Una sola inicialización para instalaciones que ya tenían el catálogo.
        # Luego el administrador puede personalizar requiere_cónyuge sin que
        # actualizaciones futuras sobrescriban su elección.
        Params = self.env['ir.config_parameter'].sudo()
        if not Params.get_param('conedera.credit.spouse_rules_initialized'):
            for code in ('married', 'free_union'):
                rule = self.env['conedera.credit.marital.status'].sudo().search([('code', '=', code)], limit=1)
                if rule and not rule.requires_spouse:
                    rule.requires_spouse = True
            Params.set_param('conedera.credit.spouse_rules_initialized', '1')

        # Los antiguos valores Selection permanecen disponibles; una sola
        # migración idempotente los relaciona con el nuevo catálogo de estados civiles.
        MaritalStatus = self.env['conedera.credit.marital.status'].sudo()
        for code in ('single', 'married', 'divorced', 'widowed', 'free_union', 'other'):
            status = MaritalStatus.search([('code', '=', code)], limit=1)
            if status:
                legacy_records = self.sudo().search([
                    ('marital_status_id', '=', False), ('marital_status', '=', code),
                ])
                if legacy_records:
                    legacy_records.with_context(credit_catalog_migration=True).write({'marital_status_id': status.id})
        # Catálogo nuevo de vivienda; se preservan los valores históricos.
        Housing = self.env['conedera.credit.housing.type'].sudo()
        for old_code in ('own', 'rented', 'family', 'mortgaged'):
            housing = Housing.search([('code', '=', old_code)], limit=1)
            if housing:
                old_requests = self.sudo().search([
                    ('housing_type_id', '=', False), ('housing_type', '=', old_code),
                ])
                if old_requests:
                    old_requests.write({'housing_type_id': housing.id})
        # Migrar ambos vehículos antiguos una sola vez, sin duplicarlos en actualizaciones.
        Vehicle = self.env['conedera.credit.vehicle'].sudo()
        legacy_fields = [
            'vehicle1_brand', 'vehicle1_model', 'vehicle1_year', 'vehicle1_value',
            'vehicle2_brand', 'vehicle2_model', 'vehicle2_year', 'vehicle2_value',
        ]
        conditions = [(field, '!=', 0 if field.endswith('_value') else False)
                      for field in legacy_fields]
        applications_with_legacy = self.sudo().search(
            [('legacy_vehicle_migrated', '=', False)] + ['|'] * (len(conditions) - 1) + conditions)
        for application in applications_with_legacy:
            for slot in (1, 2):
                item = {
                    'brand': application['vehicle%s_brand' % slot],
                    'model': application['vehicle%s_model' % slot],
                    'year': application['vehicle%s_year' % slot],
                    'value': application['vehicle%s_value' % slot],
                }
                if not any(item.values()):
                    continue
                if Vehicle.search_count([('application_id', '=', application.id), ('legacy_slot', '=', slot)]):
                    continue
                Vehicle.create(dict(item, application_id=application.id,
                                    sequence=slot * 10, legacy_slot=slot))
            application.write({'legacy_vehicle_migrated': True})
        # Los tipos creados anteriormente sin código adquieren un ID estable.
        for record in Type.search([('code', '=', False)]):
            new_code = self.env['ir.sequence'].next_by_code('conedera.credit.applicant.type')
            if not new_code:
                raise ValidationError(_('No se pudo generar el ID de un tipo de solicitante antiguo.'))
            record.with_context(credit_identifier_migration=True).write({'code': new_code})
        # La etapa para registrar documentación se identifica por un indicador,
        # nunca por su nombre: los administradores pueden renombrarla.
        docs_stage = self.env.ref('custom_web_credito_conedera.stage_credit_documents_received', raise_if_not_found=False)
        if docs_stage and not docs_stage.is_documents_received:
            docs_stage.is_documents_received = True
        # Una versión anterior conservaba documents_unlocked al volver a En revisión.
        # Corregirlo de manera idempotente sin borrar documentos ni el historial.
        self.env.cr.execute("""UPDATE conedera_credit_application AS app
            SET documents_unlocked = FALSE
            FROM conedera_credit_stage AS stage
            WHERE app.stage_id = stage.id AND app.documents_unlocked = TRUE
                AND NOT (stage.is_approved OR stage.is_documents_received)
        """)
        self.invalidate_model(['documents_unlocked'])

        # El almacenamiento binario original permanece intacto; las líneas nuevas
        # reciben una copia cuando el requisito inicial coincide con el campo viejo.
        Docs = self.env['conedera.credit.documents'].sudo()
        Line = self.env['conedera.credit.document.line'].sudo()
        Requirement = self.env['conedera.credit.document.requirement'].sudo()
        legacy_reqs = Requirement.search([('legacy_field', '!=', False)])
        for requirement in legacy_reqs:
            old_field = requirement.legacy_field
            if old_field not in Docs._fields:
                continue
            for doc in Docs.search([('application_id.applicant_type_id', '=', requirement.applicant_type_id.id)]):
                if Line.search_count([('document_id', '=', doc.id), ('requirement_id', '=', requirement.id)]):
                    continue
                # En Odoo, los binarios con attachment=True no siempre son
                # buscables por dominio: inspeccionamos el valor directamente.
                content = doc[old_field]
                if not content:
                    continue
                filename = doc[old_field + '_filename']
                if not filename:
                    # Se omite el archivo sin extensión verificable, pero se conserva
                    # siempre en su campo histórico para no perder información.
                    continue
                try:
                    with self.env.cr.savepoint():
                        Line.create({
                            'document_id': doc.id, 'requirement_id': requirement.id,
                            'file': content, 'filename': filename,
                        })
                except Exception:
                    _logger.exception('No se pudo trasladar archivo histórico %s del expediente %s; original conservado.', old_field, doc.id)
        return True
