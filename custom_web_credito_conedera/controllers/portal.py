import base64
import hmac
import logging
import math
import re
import secrets
import time
from urllib.parse import quote

from markupsafe import escape

from odoo import http, fields, _
from odoo.addons.custom_web_hr_datos_candidatos.controllers.portal_signup import AuthSignupHomeOTP
from odoo.exceptions import ValidationError
from ..models.credit_identity import (
    valid_ecuador_mobile, valid_credit_identity, valid_ecuador_or_foreign_document, valid_ruc_length,
)
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.utils import secure_filename

_logger = logging.getLogger(__name__)
OTP_TTL_SECONDS = 3 * 60
OTP_MAX_ATTEMPTS = 5
MAX_FILE_SIZE = 12 * 1024 * 1024
MAX_VEHICLES = 30
MAX_REFERENCES = 30

APPLICATION_FIELDS = [
    'identification', 'identification_type', 'business_latitude', 'business_longitude', 'application_place', 'application_date', 'applicant_name', 'applicant_email',
    'phone_fixed', 'mobile', 'profession', 'foreign_residence_time',
    'foreign_work_visa', 'spouse_name', 'spouse_identification', 'spouse_profession',
    'dependents_count', 'home_address', 'business_name', 'legal_representative', 'business_ruc', 'province',
    'canton', 'city', 'business_address', 'business_phone', 'representative_email',
    'activity_start_date', 'business_local_type', 'monthly_sales', 'social_capital', 'invoice_email',
    'assets_amount', 'monthly_income', 'liabilities_amount', 'monthly_expenses',
    'authorized_buyer_name', 'authorized_buyer_identification', 'authorized_buyer_email',
    'authorized_pickup_name', 'authorized_pickup_identification', 'employment_company',
    'employment_activity', 'employment_address', 'employment_phone', 'employment_start_date',
    'employment_position', 'employment_salary',
]
DATE_FIELDS = {'application_date', 'activity_start_date', 'employment_start_date'}
INTEGER_FIELDS = {'dependents_count'}
FLOAT_FIELDS = {
    'business_latitude', 'business_longitude', 'monthly_sales', 'social_capital', 'assets_amount',
    'monthly_income', 'liabilities_amount', 'monthly_expenses', 'employment_salary',
}

def _clean(value):
    return str(value or '').strip()


def _parse_date(value):
    value = _clean(value)
    return value or False


def _parse_number(value, label, errors, integer=False):
    value = _clean(value)
    if not value:
        return 0 if integer else 0.0
    try:
        number = int(value) if integer else float(value.replace(',', '.'))
        if not integer and not math.isfinite(number):
            raise ValueError('non-finite number')
        return number
    except (TypeError, ValueError):
        errors.append(_('El campo \"%s\" debe contener un número válido.') % label)
        return 0 if integer else 0.0


def _send_otp_email(email, code):
    # El portal de crédito utiliza únicamente el servidor marcado como
    # "Correo de crédito". No usa ni modifica el servidor marcado para RR. HH.
    mail_server = request.env['ir.mail_server'].sudo().get_conedera_credit_mail_server()
    email_from = (mail_server.smtp_user or '').strip()
    values = {
        'subject': _('Código de verificación para el portal de crédito CONEDERA'),
        'body_html': (
            '<div style=\"font-family:Arial,sans-serif;max-width:560px;margin:auto\">'
            '<h2 style=\"color:#8f2f2f\">Verificación de correo CONEDERA</h2>'
            '<p>Use el siguiente código para verificar su correo y activar su cuenta:</p>'
            '<p style=\"font-size:30px;font-weight:bold;letter-spacing:6px\">%s</p>'
            '<p>El código vence en 3 minutos. Si no lo ingresa a tiempo, podrá solicitar uno nuevo desde el portal. Si usted no inició este registro, puede ignorar el mensaje.</p>'
            '</div>' % code
        ),
        'email_to': email,
        'email_from': email_from,
        'mail_server_id': mail_server.id,
    }
    mail = request.env['mail.mail'].sudo().create(values)
    mail.send()
    mail.invalidate_recordset(['state'])
    if mail.state == 'exception':
        raise RuntimeError(_('No se pudo enviar el correo de verificación. Revise el servidor saliente de correo de Odoo.'))


class CreditPortalLogin(AuthSignupHomeOTP):
    def _render_native_signup(self, values=None):
        context = self.get_auth_signup_qcontext()
        pending = request.session.get('conedera_credit_signup') or {}
        context.update({
            'name': pending.get('name') or context.get('name') or '',
            'login': pending.get('email') or context.get('login') or '',
            'error': False,
            'message': False,
            'token': False,
            'redirect': '/my/credito/nueva',
            'signup_enabled': True,
            'signup_email': pending.get('email') or '',
        })
        context.update(values or {})
        # El registro usa la pantalla nativa, pero no crea el usuario hasta validar el OTP.
        context['signup_enabled'] = True
        context['token'] = False
        context['redirect'] = '/my/credito/nueva'
        return request.render('auth_signup.signup', context)

    @http.route()
    def web_auth_signup(self, *args, **kw):
        # Los enlaces nativos de invitación de Odoo (con token) conservan su flujo original.
        # El registro público sin token pasa por la verificación OTP de CONEDERA.
        if request.params.get('token'):
            # Saltar la verificación OTP propia del módulo de RR. HH. para preservar
            # el flujo nativo de invitaciones/token de Odoo.
            return super(AuthSignupHomeOTP, self).web_auth_signup(*args, **kw)

        current_user = request.env.user
        if (not current_user._is_public()
                and current_user.has_group('base.group_portal')
                and not current_user.has_group('base.group_user')):
            return request.redirect('/my/credito/nueva')

        if request.httprequest.method == 'GET':
            return self._render_native_signup()

        qcontext = self.get_auth_signup_qcontext()
        name = _clean(qcontext.get('name'))
        email = _clean(qcontext.get('login') or qcontext.get('email')).lower()
        password = qcontext.get('password') or ''
        confirm_password = qcontext.get('confirm_password') or ''
        errors = []
        if not name:
            errors.append(_('Ingrese sus nombres y apellidos.'))
        if not email or not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors.append(_('Ingrese un correo electrónico válido.'))
        if len(password) < 8:
            errors.append(_('La contraseña debe tener al menos 8 caracteres.'))
        if password != confirm_password:
            errors.append(_('Las contraseñas no coinciden.'))
        # Leer la casilla exclusivamente del cuerpo del formulario. No aceptar un
        # accept_terms=on agregado a la URL ni confiar solo en la validación JavaScript.
        accept_terms = request.httprequest.form.get('accept_terms')
        if str(accept_terms or '').strip().lower() not in ('on', '1', 'true', 'yes'):
            errors.append(_('Debe aceptar los términos y condiciones para registrarse.'))

        # Las validaciones del formulario (en especial términos y condiciones) van
        # antes de informar que un correo ya existe. Si falta la aceptación, el usuario
        # permanece en el registro y no se crea una sesión OTP ni una cuenta.
        if errors:
            # No reutilizar un OTP pendiente tras reenviar el formulario con datos
            # inválidos o sin aceptar términos; deberá corregirlo antes de continuar.
            request.session.pop('conedera_credit_signup', None)
            return self._render_native_signup({
                'name': name,
                'login': email,
                'error': '; '.join(errors),
            })

        User = request.env['res.users'].sudo()
        existing = User.search(['|', ('login', '=ilike', email), ('email', '=ilike', email)], limit=1) if email else User.browse()
        if existing:
            return request.redirect('/web/login?account_exists=1&redirect=%s' % quote('/my/credito/nueva', safe=''))

        previous_signup = request.session.get('conedera_credit_signup') or {}
        if previous_signup.get('email') == email:
            remaining = max(0, int(math.ceil(previous_signup.get('expires', 0) - time.time())))
            return self._render_native_signup({
                'name': previous_signup.get('name', name),
                'login': email,
                'signup_email': email,
            })

        code = str(secrets.randbelow(900000) + 100000)
        request.session['conedera_credit_signup'] = {
            'name': name,
            'email': email,
            'password': password,
            'code': code,
            'expires': time.time() + OTP_TTL_SECONDS,
            'attempts': 0,
            'accept_terms': True,
        }
        try:
            _send_otp_email(email, code)
        except Exception:
            _logger.exception('No se pudo enviar el código OTP de registro CONEDERA')
            request.session.pop('conedera_credit_signup', None)
            return self._render_native_signup({
                'name': name,
                'login': email,
                'error': _('No se pudo enviar el código. Verifique que exista un servidor saliente marcado como "Correo de crédito" y que tenga configurado smtp_user.'),
            })
        return self._render_native_signup({
            'name': name,
            'login': email,
            'signup_email': email,
            'error': False,
        })

    @http.route()
    def web_login(self, redirect=None, **kw):
        # Solo redirigir por defecto a clientes del portal; los usuarios internos
        # deben conservar el flujo de acceso normal al backend de Odoo.
        explicit_redirect = redirect or request.params.get('redirect')
        response = super().web_login(redirect=explicit_redirect, **kw)
        if not explicit_redirect and request.httprequest.method == 'POST' and request.session.uid:
            user = request.env['res.users'].sudo().browse(request.session.uid).exists()
            if user and user.has_group('base.group_portal') and not user.has_group('base.group_user'):
                return request.redirect('/my/credito/nueva')
        return response


class ConederaCreditPortal(http.Controller):

    def _render_verify(self, error=None, remaining_seconds=None):
        signup = request.session.get('conedera_credit_signup') or {}
        if not signup:
            return request.redirect('/web/login?redirect=%2Fmy%2Fcredito%2Fnueva')
        signup['otp_error'] = str(error) if error else False
        request.session['conedera_credit_signup'] = signup
        return request.render('auth_signup.signup', self._signup_qcontext_for_modal(signup))

    def _signup_qcontext_for_modal(self, signup):
        # Keep the native signup template and the checkbox supplied by the HR module.
        return {
            'name': signup.get('name', ''),
            'login': signup.get('email', ''),
            'email': signup.get('email', ''),
            'redirect': '/my/credito/nueva',
            'signup_enabled': True,
            'token': False,
            'error': False,
            'message': False,
        }

    @http.route('/credito/registro', type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def credit_signup(self, **post):
        # Compatibilidad con enlaces antiguos: la entrada de Solicitar crédito debe ir primero al login.
        if (not request.env.user._is_public()
                and request.env.user.has_group('base.group_portal')
                and not request.env.user.has_group('base.group_user')):
            return request.redirect('/my/credito/nueva')
        return request.redirect('/web/login?redirect=%2Fmy%2Fcredito%2Fnueva')

    @http.route('/credito/registro/cancelar', type='http', auth='public', website=True, methods=['POST'], sitemap=False)
    def credit_signup_cancel(self, **post):
        # Cerrar el modal cancela el registro pendiente y descarta el OTP de esta sesión.
        # Así no vuelve a aparecer al regresar al formulario nativo de registro.
        request.session.pop('conedera_credit_signup', None)
        return request.redirect('/web/signup?redirect=%2Fmy%2Fcredito%2Fnueva&verification_cancelled=1')

    @http.route('/credito/registro/verificar', type='http', auth='public', website=True, methods=['GET', 'POST'], sitemap=False)
    def credit_signup_verify(self, **post):
        signup = request.session.get('conedera_credit_signup')
        if not signup:
            return request.redirect('/web/login?redirect=%2Fmy%2Fcredito%2Fnueva')
        if signup.get('accept_terms', True) is not True:
            request.session.pop('conedera_credit_signup', None)
            return request.redirect('/web/signup?redirect=%2Fmy%2Fcredito%2Fnueva&terms_required=1')

        now = time.time()
        expires_at = signup.get('expires', 0)

        # El botón de reenvío solo es aceptado por el servidor una vez vencidos los 3 minutos.
        if request.httprequest.method == 'POST' and post.get('action') == 'resend':
            remaining = max(0, int(math.ceil(expires_at - now)))
            if remaining > 0:
                return self._render_verify(
                    _('Podrá solicitar un código nuevo cuando termine el contador.'),
                    remaining_seconds=remaining,
                )

            code = str(secrets.randbelow(900000) + 100000)
            signup.update({
                'code': code,
                'expires': now + OTP_TTL_SECONDS,
                'attempts': 0,
                'otp_error': False,
            })
            request.session['conedera_credit_signup'] = signup
            try:
                _send_otp_email(signup['email'], code)
            except Exception:
                _logger.exception('No se pudo reenviar el código OTP de registro CONEDERA')
                # Mantener el registro en sesión y dejar disponible el reenvío si el SMTP falla.
                signup['expires'] = time.time()
                request.session['conedera_credit_signup'] = signup
                return self._render_verify(
                    _('No se pudo enviar el código. Revise el servidor SMTP marcado como "Correo de crédito" e inténtelo nuevamente.'),
                    remaining_seconds=0,
                )
            return self._render_verify(remaining_seconds=OTP_TTL_SECONDS)

        if request.httprequest.method == 'POST':
            if time.time() > signup.get('expires', 0):
                return self._render_verify(
                    _('El código venció. Use el botón «Reenviar código» para recibir otro.'),
                    remaining_seconds=0,
                )
            if signup.get('attempts', 0) >= OTP_MAX_ATTEMPTS:
                return self._render_verify(
                    _('Se alcanzó el máximo de intentos para este código. Espere a que termine el contador y reenvíe el código.'),
                    remaining_seconds=max(0, int(math.ceil(signup.get('expires', 0) - time.time()))),
                )

            user_code = _clean(post.get('code'))
            signup['attempts'] = signup.get('attempts', 0) + 1
            request.session['conedera_credit_signup'] = signup
            if not hmac.compare_digest(user_code, signup.get('code', '')):
                error = _('El código ingresado no es correcto.')
                return self._render_verify(error)

            existing = request.env['res.users'].sudo().search([
                '|', ('login', '=ilike', signup['email']), ('email', '=ilike', signup['email']),
            ], limit=1)
            if existing:
                request.session.pop('conedera_credit_signup', None)
                return request.redirect('/web/login?account_exists=1&redirect=%s' % quote('/my/credito/nueva', safe=''))
            try:
                # Crear la cuenta con el flujo nativo de auth_signup de Odoo.
                # El partner se crea solo después de validar el OTP y se vincula
                # a un único res.users mediante el token nativo de registro.
                with request.env.cr.savepoint():
                    partner = request.env['res.partner'].sudo().create({
                        'name': signup['name'],
                        'email': signup['email'],
                    })
                    # Odoo 18 ya no almacena signup_token en res.partner.
                    # signup_prepare() activa el tipo de registro y
                    # _generate_signup_token() produce el token firmado válido.
                    partner.signup_prepare(signup_type='signup')
                    signup_token = partner._generate_signup_token()
                    signup_values = {
                        'name': signup['name'],
                        'login': signup['email'],
                        'email': signup['email'],
                        'password': signup['password'],
                    }
                    request.env['res.users'].sudo().signup(
                        signup_values,
                        token=signup_token,
                    )
                request.session.pop('conedera_credit_signup', None)
                return request.redirect('/web/login?account_created=1&redirect=%s' % quote('/my/credito/nueva', safe=''))
            except Exception:
                _logger.exception('No se pudo crear la cuenta nativa del portal de crédito CONEDERA')
                return self._render_verify(_('El código se validó, pero no fue posible crear su cuenta. Inténtelo nuevamente o comuníquese con soporte.'))

        return self._render_verify()

    def _get_owned_application(self, application_id):
        application = request.env['conedera.credit.application'].sudo().browse(application_id).exists()
        if not application or application.portal_user_id.id != request.env.user.id:
            raise NotFound()
        return application

    def _portal_applications(self, domain=None):
        domain = list(domain or [])
        domain.append(('portal_user_id', '=', request.env.user.id))
        return request.env['conedera.credit.application'].sudo().search(domain, order='create_date desc, id desc')

    def _has_portal_update_scope(self):
        return bool(self._portal_applications([('portal_update_scope', 'in', ['history', 'documentation', 'both'])]))

    def _can_correct(self, application=None):
        # Igual que historial_postulaciones: autorización por solicitud.
        if not application:
            return self._has_portal_update_scope()
        return bool(application.portal_user_id.id == request.env.user.id and
            application.portal_can_update_history() and
            not application.stage_id.is_approved and
            not application.stage_id.is_rejected and
            not application.stage_id.is_documents_received)

    def _can_update_credit_documents(self, application, document=None):
        if not application.document_access_allowed or application.portal_user_id.id != request.env.user.id:
            return False
        # Como en postulaciones: primer ingreso tras la aprobación libre;
        # la corrección de documentos ya ingresados sí exige permiso de esa solicitud.
        return not document or application.portal_can_update_documentation()

    def _pending_application(self):
        return request.env['conedera.credit.application'].sudo()._blocking_application(request.env.user.id)

    def _render_application_form(self, form_values=None, errors=None, start_step=1, application=None):
        defaults = {'application_date': fields.Date.context_today(request.env.user).strftime('%Y-%m-%d'),
                    'applicant_name': '', 'identification_type': 'cedula',
                    'applicant_email': request.env.user.email or request.env.user.login}
        defaults.update(form_values or {})
        count = _clean(defaults.get('vehicle_count'))
        vehicle_count = min(MAX_VEHICLES, max(1, int(count))) if count.isdecimal() else 1
        reference_rows = {}
        for typ in ('commercial', 'personal', 'bank'):
            raw = _clean(defaults.get('%s_count' % typ))
            reference_rows[typ] = range(1, min(MAX_REFERENCES, max(3, int(raw))) + 1) if raw.isdecimal() else range(1, 4)
        return request.render('custom_web_credito_conedera.portal_credit_application_form', {
            'form_values': defaults,
            'errors': errors or [],
            'application': application,
            'marital_statuses': request.env['conedera.credit.marital.status'].sudo().search([('active', '=', True)], order='sequence,name,id'),
            'start_step': max(1, min(5, int(start_step or 1))),
            'housing_types': request.env['conedera.credit.housing.type'].sudo().search([('active', '=', True)], order='sequence,name,id'),
            'vehicle_rows': range(1, vehicle_count + 1),
            'reference_rows': reference_rows,
            'local_types': [('own', 'Propio'), ('rented', 'Alquilado'), ('family', 'Familiar'), ('mortgaged', 'Hipotecado')],
            'applicant_types': request.env['conedera.credit.applicant.type'].sudo().search([('active', '=', True)], order='sequence, name, id'),
        })

    @http.route('/my/credito/nueva', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def new_credit_application(self, **kwargs):
        existing = self._pending_application()
        if existing:
            return request.redirect('/my/credito/%s?pending=1' % existing.id)
        return self._render_application_form({'applicant_name': '', 'applicant_email': request.env.user.email or request.env.user.login})

    def _reference_commands(self, post, errors):
        commands = []
        for typ in ('commercial', 'personal', 'bank'):
            raw_count = _clean(post.get('%s_count' % typ))
            if not raw_count.isdecimal() or not 3 <= int(raw_count) <= MAX_REFERENCES:
                errors.append(_('La cantidad de referencias %(tipo)s no es válida.') % {'tipo': typ})
                continue
            for number in range(1, int(raw_count) + 1):
                if typ == 'commercial':
                    values = {
                        'reference_type': typ, 'sequence': number * 10,
                        'provider': _clean(post.get('commercial_provider_%s' % number)),
                        'customer_since': _clean(post.get('commercial_since_%s' % number)),
                        'credit_limit': _parse_number(post.get('commercial_limit_%s' % number), _('Cupo de referencia comercial %s') % number, errors),
                        'term': _clean(post.get('commercial_term_%s' % number)),
                        'phone': _clean(post.get('commercial_phone_%s' % number)),
                        'contact': _clean(post.get('commercial_contact_%s' % number)),
                    }
                    relevant = ('provider', 'customer_since', 'credit_limit', 'term', 'phone', 'contact')
                elif typ == 'personal':
                    values = {
                        'reference_type': typ, 'sequence': number * 10,
                        'person_name': _clean(post.get('personal_name_%s' % number)),
                        'address': _clean(post.get('personal_address_%s' % number)),
                        'home_phone': _clean(post.get('personal_phone_%s' % number)),
                        'relationship': _clean(post.get('personal_relationship_%s' % number)),
                    }
                    relevant = ('person_name', 'address', 'home_phone', 'relationship')
                else:
                    values = {
                        'reference_type': typ, 'sequence': number * 10,
                        'bank_name': _clean(post.get('bank_name_%s' % number)),
                        'account_number': _clean(post.get('bank_account_%s' % number)),
                        'opening_date': _parse_date(post.get('bank_opening_%s' % number)),
                        'account_type': _clean(post.get('bank_type_%s' % number)) or False,
                    }
                    relevant = ('bank_name', 'account_number', 'opening_date', 'account_type')
                if any(values[key] not in ('', 0, 0.0, False) for key in relevant):
                    commands.append((0, 0, values))
        return commands

    def _vehicle_commands(self, post, errors):
        """Guarda vehículos opcionales y conserva el primero por defecto en pantalla."""
        raw_count = _clean(post.get('vehicle_count'))
        if not raw_count.isdecimal() or not 1 <= int(raw_count) <= MAX_VEHICLES:
            errors.append(_('La cantidad de vehículos indicada no es válida.'))
            return []
        commands = []
        for number in range(1, int(raw_count) + 1):
            values = {
                'sequence': number * 10,
                'brand': _clean(post.get('vehicle%s_brand' % number)),
                'model': _clean(post.get('vehicle%s_model' % number)),
                'year': _clean(post.get('vehicle%s_year' % number)),
                'value': _parse_number(post.get('vehicle%s_value' % number),
                                       _('Avalúo del vehículo %s') % number, errors),
            }
            if values['value'] < 0:
                errors.append(_('El avalúo del vehículo %s no puede ser negativo.') % number)
            if any(values[key] for key in ('brand', 'model', 'year', 'value')):
                commands.append((0, 0, values))
        return commands

    @http.route('/my/credito/solicitud/enviar', type='http', auth='user', website=True, methods=['POST'], sitemap=False)
    def submit_credit_application(self, **post):
        return self._process_application(post)

    def _application_to_form(self, application):
        values = {}
        for name in APPLICATION_FIELDS:
            field_value = application[name]
            if name in DATE_FIELDS and field_value:
                values[name] = str(field_value)
            elif name in FLOAT_FIELDS or name in INTEGER_FIELDS:
                values[name] = str(field_value) if field_value else ''
            else:
                values[name] = field_value or ''
        values['applicant_type_id'] = str(application.applicant_type_id.id or '')
        values['marital_status_id'] = str(application.marital_status_id.id or '')
        values['housing_type_id'] = str(application.housing_type_id.id or '')
        vehicles = application.vehicle_ids.sorted(key=lambda v: (v.sequence, v.id))
        values['vehicle_count'] = str(max(1, len(vehicles)))
        for number, vehicle in enumerate(vehicles, 1):
            for suffix, field_name in (('brand', 'brand'), ('model', 'model'), ('year', 'year'), ('value', 'value')):
                value = vehicle[field_name]
                values['vehicle%s_%s' % (number, suffix)] = str(value) if value else ''
        for typ in ('commercial', 'personal', 'bank'):
            refs = application.reference_ids.filtered(lambda r: r.reference_type == typ).sorted(key=lambda r: (r.sequence, r.id))
            values['%s_count' % typ] = str(max(3, len(refs)))
            fields_map = {
                'commercial': [('provider', 'provider'), ('since', 'customer_since'), ('limit', 'credit_limit'), ('term', 'term'), ('phone', 'phone'), ('contact', 'contact')],
                'personal': [('name', 'person_name'), ('address', 'address'), ('phone', 'home_phone'), ('relationship', 'relationship')],
                'bank': [('name', 'bank_name'), ('account', 'account_number'), ('opening', 'opening_date'), ('type', 'account_type')],
            }[typ]
            for number, ref in enumerate(refs, 1):
                for suffix, field_name in fields_map:
                    value = ref[field_name]
                    values['%s_%s_%s' % (typ, suffix, number)] = str(value) if value else ''
        for term in ('declaration_accepted', 'prior_commercial_relationship_accepted',
                     'electronic_service_accepted', 'credit_bureau_authorized',
                     'company_signature_stamp_acknowledged', 'additional_financial_documents_accepted'):
            values[term] = 'on' if application[term] else ''
        return values

    @http.route('/my/credito/acciones', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def credit_quick_actions(self, **kw):
        if not self._can_correct():
            raise Forbidden(_('No dispone del permiso especial de acceso rápido.'))
        applications = self._portal_applications()
        return request.render('custom_web_credito_conedera.portal_credit_quick_actions', {
            'applications': applications,
            'editable_ids': applications.filtered(lambda a: self._can_correct(a)).ids,
            'has_documents_enabled': bool(applications.filtered('document_access_allowed')),
            'documentation_editable_ids': applications.filtered(lambda a: a.document_access_allowed and a.portal_can_update_documentation()).ids,
        })

    @http.route('/my/credito/<int:application_id>/editar', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def edit_credit_application(self, application_id, **kw):
        application = self._get_owned_application(application_id)
        if not self._can_correct(application):
            raise Forbidden(_('No tiene permiso para modificar esta solicitud o ya tiene una decisión registrada.'))
        return self._render_application_form(self._application_to_form(application), application=application)

    @http.route('/my/credito/<int:application_id>/actualizar', type='http', auth='user', website=True, methods=['POST'], sitemap=False)
    def update_credit_application(self, application_id, **post):
        application = self._get_owned_application(application_id)
        if not self._can_correct(application):
            raise Forbidden(_('No tiene permiso para modificar esta solicitud o ya tiene una decisión registrada.'))
        return self._process_application(post, application=application)

    def _process_application(self, post, application=None):
        if not application:
            existing = self._pending_application()
            if existing:
                return request.redirect('/my/credito/%s?pending=1' % existing.id)
        elif not self._can_correct(application):
            raise Forbidden()
        errors = []
        values = {}
        for field_name in APPLICATION_FIELDS:
            value = post.get(field_name)
            if field_name in DATE_FIELDS:
                values[field_name] = _parse_date(value)
            elif field_name in INTEGER_FIELDS:
                values[field_name] = _parse_number(value, field_name, errors, integer=True)
            elif field_name in FLOAT_FIELDS:
                values[field_name] = _parse_number(value, field_name, errors)
            else:
                values[field_name] = _clean(value) or False
        latitude_raw = _clean(post.get('business_latitude'))
        longitude_raw = _clean(post.get('business_longitude'))
        if bool(latitude_raw) != bool(longitude_raw):
            errors.append(_('Ingrese ambos valores: latitud y longitud.'))
        if latitude_raw and not -90 <= values['business_latitude'] <= 90:
            errors.append(_('La latitud debe estar entre -90 y 90.'))
        if longitude_raw and not -180 <= values['business_longitude'] <= 180:
            errors.append(_('La longitud debe estar entre -180 y 180.'))
        values['application_date'] = values.get('application_date') or fields.Date.context_today(request.env.user).strftime('%Y-%m-%d')
        values['portal_user_id'] = request.env.user.id
        selected_type = _clean(post.get('applicant_type_id'))
        applicant_type = request.env['conedera.credit.applicant.type'].sudo()
        if selected_type.isdecimal():
            applicant_type = applicant_type.search([('id', '=', int(selected_type)), ('active', '=', True)], limit=1)
        values['applicant_type_id'] = applicant_type.id or False
        marital_code = _clean(post.get('marital_status_id'))
        marital_record = request.env['conedera.credit.marital.status'].sudo()
        if marital_code.isdecimal():
            marital_record = marital_record.search([('id', '=', int(marital_code)), ('active', '=', True)], limit=1)
        if marital_code and not marital_record:
            errors.append(_('Seleccione un estado civil válido.'))
        values['marital_status_id'] = marital_record.id or False
        spouse_required = bool(marital_record and marital_record.requires_spouse)
        if spouse_required:
            for field_name, label in (('spouse_name', _('nombres del cónyuge')),
                                      ('spouse_identification', _('cédula del cónyuge')),
                                      ('spouse_profession', _('profesión del cónyuge'))):
                if not values.get(field_name):
                    errors.append(_('El campo %(field)s es obligatorio para casados o unión de hecho.') % {'field': label})
        else:
            values.update({'spouse_name': False, 'spouse_identification': False, 'spouse_profession': False})
        housing_code = _clean(post.get('housing_type_id'))
        housing_record = request.env['conedera.credit.housing.type'].sudo()
        if housing_code.isdecimal():
            housing_record = housing_record.search([('id', '=', int(housing_code)), ('active', '=', True)], limit=1)
        if housing_code and not housing_record:
            errors.append(_('Seleccione un tipo de vivienda válido.'))
        values['housing_type_id'] = housing_record.id or False
        values['vehicle_ids'] = self._vehicle_commands(post, errors)
        values['declaration_accepted'] = post.get('declaration_accepted') in ('on', '1', 'true', 'yes')
        consent_fields = [
            ('prior_commercial_relationship_accepted', _('Debe aceptar la cláusula sobre la relación comercial previa y su valor probatorio.')),
            ('electronic_service_accepted', _('Debe aceptar la cláusula de citación telemática propuesta conforme al Art. 55.1 del COGEP.')),
            ('credit_bureau_authorized', _('Debe autorizar por separado la consulta de su score e historial crediticio.')),
            ('company_signature_stamp_acknowledged', _('Debe confirmar que conoce el requisito de firma y sello del representante legal de CONEDERA S.A.')),
            ('additional_financial_documents_accepted', _('Debe aceptar la entrega de los documentos financieros adicionales solicitados.')),
        ]
        for field_name, _message in consent_fields:
            values[field_name] = post.get(field_name) in ('on', '1', 'true', 'yes')
        values['reference_ids'] = self._reference_commands(post, errors)

        for field_name, label in [
            ('applicant_type_id', _('tipo de solicitante')),
            ('identification', _('documento del solicitante')),
            ('identification_type', _('tipo de documento')),
            ('applicant_name', _('nombres y apellidos')),
            ('applicant_email', _('correo electrónico')),
            ('mobile', _('celular')),
            ('business_name', _('nombre o razón social')),
            ('business_ruc', _('RUC del negocio')),
            ('business_address', _('dirección de la empresa')),
        ]:
            if not values.get(field_name):
                errors.append(_('El campo %(field)s es obligatorio.') % {'field': label})
        if values.get('identification') and not valid_credit_identity(values['identification'], values.get('identification_type')):
            errors.append(_('El documento del solicitante no corresponde al tipo elegido: cédula ecuatoriana válida (10), RUC numérico (13) o cédula extranjera numérica (10).'))
        if values.get('spouse_identification') and not valid_ecuador_or_foreign_document(values['spouse_identification']):
            errors.append(_('La identificación del cónyuge debe tener 10 dígitos numéricos.'))
        for field_name, label in (
            ('authorized_buyer_identification', _('persona autorizada a comprar')),
            ('authorized_pickup_identification', _('persona autorizada a retirar mercadería')),
        ):
            document = values.get(field_name)
            if document and not valid_ecuador_or_foreign_document(document):
                errors.append(_(
                    'El documento de %(person)s debe tener exactamente 10 dígitos numéricos '
                    '(cédula ecuatoriana o documento extranjero).'
                ) % {'person': label})
        if values.get('business_ruc') and not valid_ruc_length(values['business_ruc']):
            errors.append(_('El RUC del negocio debe tener exactamente 13 dígitos numéricos.'))
        if values.get('mobile') and not valid_ecuador_mobile(values['mobile']):
            errors.append(_('El celular debe contener exactamente 10 dígitos numéricos.'))
        if values.get('applicant_email') and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', values['applicant_email']):
            errors.append(_('Ingrese un correo válido para el propietario o representante.'))
        if not values['declaration_accepted']:
            errors.append(_('Debe aceptar la declaración y autorización general para enviar la solicitud.'))
        for field_name, message in consent_fields:
            if not values[field_name]:
                errors.append(message)
        if errors:
            required_person = ('applicant_type_id', 'identification', 'applicant_name', 'applicant_email', 'mobile')
            required_business = ('business_name', 'business_ruc', 'business_address')
            invalid_terms = not values['declaration_accepted'] or any(not values[key] for key, _message in consent_fields)
            step = (1 if any(not values.get(key) for key in required_person) else
                    2 if any(not values.get(key) for key in required_business) else
                    5 if invalid_terms else 1)
            return self._render_application_form(post, errors, start_step=step, application=application)

        try:
            with request.env.cr.savepoint():
                if application:
                    # Un permiso de formulario es de un solo uso; impedir dos guardados
                    # simultáneos desde pestañas abiertas antes de su consumo.
                    request.env.cr.execute(
                        'SELECT id FROM conedera_credit_application WHERE id = %s FOR UPDATE',
                        (application.id,))
                    application.invalidate_recordset(['portal_update_scope'])
                    if not self._can_correct(application):
                        raise Forbidden(_('El permiso de actualización ya fue utilizado o revocado.'))
                    # Reemplazar SOLO los vehículos/referencias, de manera atómica.
                    # No tocar historial, documentos, aprobación o verificación interna.
                    values['vehicle_ids'] = [(5, 0, 0)] + values['vehicle_ids']
                    values['legacy_vehicle_migrated'] = True
                    values['reference_ids'] = [(5, 0, 0)] + values['reference_ids']
                    application.sudo().write(values)
                    # La autorización de corrección es para un único guardado.
                    # Si también se autorizó documentos, conservar SOLO ese acceso.
                    # Tras guardar, Historial vuelve a mostrar «Ver detalle».
                    remaining_scope = 'documentation' if application.portal_update_scope == 'both' else 'none'
                    application.sudo().write({
                        'portal_update_scope': remaining_scope,
                        'portal_history_consumed_at': fields.Datetime.now(),
                    })
                    application.message_post(body=_('El solicitante actualizó sus datos mediante el permiso especial del portal. La autorización de edición del formulario fue consumida.'))
                else:
                    application = request.env['conedera.credit.application'].sudo().create(values)
        except (ValidationError, ValueError) as exc:
            return self._render_application_form(post, [str(exc)], application=application)
        except Exception:
            _logger.exception('Error registrando o actualizando la solicitud de crédito desde el portal')
            return self._render_application_form(post, [_('No se pudo guardar la solicitud. Revise los datos e inténtelo nuevamente.')], application=application)

        # Conservar el aviso a cobranzas, pero incluir únicamente las coordenadas
        # declaradas por el solicitante, sin generar ni almacenar enlaces externos.
        if latitude_raw and longitude_raw and not post.get('credit_edit_mode'):
            try:
                credit_mail_server = request.env['ir.mail_server'].sudo().get_conedera_credit_mail_server()
                email_from = (credit_mail_server.smtp_user or '').strip()
                mail_vals = {
                    'subject': _('Ubicación de negocio - Solicitud de crédito %s') % application.name,
                    'body_html': (
                        '<p>Se registró una solicitud de crédito CONEDERA.</p>'
                        '<p><b>Solicitud:</b> %s<br/><b>Solicitante:</b> %s<br/>'
                        '<b>Negocio:</b> %s<br/><b>Identificación:</b> %s</p>'
                        '<p><b>Latitud del negocio:</b> %s<br/><b>Longitud del negocio:</b> %s</p>'
                    ) % tuple(escape(str(value or '')) for value in (
                        application.name, application.applicant_name,
                        application.business_name, application.identification,
                        latitude_raw, longitude_raw,
                    )),
                    'email_to': 'cobranzas@viteltek.com',
                    'email_from': email_from,
                    'mail_server_id': credit_mail_server.id,
                }
                request.env['mail.mail'].sudo().create(mail_vals).send()
            except Exception:
                _logger.exception('No se pudo enviar la ubicación del negocio al buzón de cobranzas CONEDERA')
        return request.redirect('/my/credito/%s?%s=1' % (application.id, 'updated' if post.get('credit_edit_mode') else 'sent'))

    @http.route('/my/credito/historial', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def credit_history(self, **kwargs):
        return request.render('custom_web_credito_conedera.portal_credit_history', {
            'applications': self._portal_applications(),
            'can_correct_ids': self._portal_applications().filtered(lambda a: self._can_correct(a)).ids,
        })

    @http.route('/my/credito/<int:application_id>', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def credit_application_detail(self, application_id, **kwargs):
        application = self._get_owned_application(application_id)
        history = application.history_ids.filtered(lambda row: row.visible_to_portal).sorted(key=lambda row: (row.date or fields.Datetime.now(), row.id))
        documents = application.document_ids[:1]
        return request.render('custom_web_credito_conedera.portal_credit_detail', {
            'application': application,
            'history': history,
            'documents': documents,
            'verification_label': dict(application._fields['verification_status']._description_selection(request.env)).get(application.verification_status, '-'),
            'can_correct': self._can_correct(application),
        })

    @http.route('/my/credito/documentos', type='http', auth='user', website=True, methods=['GET'], sitemap=False)
    def credit_documents_index(self, **kwargs):
        applications = self._portal_applications([('documents_unlocked', '=', True)])
        applications = applications.filtered(lambda app: app.document_access_allowed)
        return request.render('custom_web_credito_conedera.portal_credit_documents_index', {'applications': applications})

    def _credit_document_errors(self, doc):
        missing = []
        if doc:
            uploaded = set(doc.document_line_ids.filtered(lambda line: bool(line.file)).mapped('requirement_id').ids)
            for requirement in doc._required_fields():
                if requirement.id not in uploaded:
                    missing.append(requirement.name)
        return missing

    def _render_credit_documents_form(self, application, document=None, errors=None):
        requirements = application.applicant_type_id.requirement_ids.filtered('active')
        if not application.spouse_name:
            requirements = requirements.filtered(lambda r: not r.only_if_spouse)
        requirements = requirements.sorted(key=lambda r: (r.sequence, r.id))
        files_by_requirement = {}
        if document:
            files_by_requirement = {line.requirement_id.id: line for line in document.document_line_ids if line.file}
        return request.render('custom_web_credito_conedera.portal_credit_documents_form', {
            'application': application,
            'document': document,
            'errors': errors or [],
            'requirements': requirements,
            'files_by_requirement': files_by_requirement,
            'can_update_documents': self._can_update_credit_documents(application, document),
        })

    @http.route('/my/credito/<int:application_id>/documentos', type='http', auth='user', website=True, methods=['GET', 'POST'], sitemap=False)
    def credit_documents_form(self, application_id, **post):
        application = self._get_owned_application(application_id)
        if not application.document_access_allowed:
            raise Forbidden(_('El ingreso de documentos se habilita cuando la solicitud está aprobada.'))
        Documents = request.env['conedera.credit.documents'].sudo()
        document = Documents.search([('application_id', '=', application.id)], limit=1)
        if request.httprequest.method == 'GET':
            return self._render_credit_documents_form(application, document)
        if not self._can_update_credit_documents(application, document):
            raise Forbidden(_('Necesita que CONEDERA habilite la actualización de la documentación de esta solicitud.'))

        errors = []
        uploads = []
        requirements = application.applicant_type_id.requirement_ids.filtered('active')
        if not application.spouse_name:
            requirements = requirements.filtered(lambda r: not r.only_if_spouse)
        Line = request.env['conedera.credit.document.line'].sudo()
        for requirement in requirements:
            file_obj = request.httprequest.files.get('doc_req_%s' % requirement.id)
            if not file_obj or not file_obj.filename:
                continue
            filename = secure_filename(file_obj.filename) or 'documento'
            content = file_obj.read(MAX_FILE_SIZE + 1)
            if not content:
                continue
            if len(content) > MAX_FILE_SIZE:
                errors.append(_('El archivo "%s" supera el límite de 12 MB.') % requirement.name)
                continue
            encoded = base64.b64encode(content).decode('ascii')
            try:
                Line._validate_file(requirement, filename, encoded)
            except ValidationError as exc:
                errors.append(str(exc))
                continue
            uploads.append((requirement, filename, encoded))

        if not requirements:
            errors.append(_('No hay documentos configurados para este tipo de solicitante. Contacte a CONEDERA.'))
        if errors:
            return self._render_credit_documents_form(application, document, errors)
        try:
            with request.env.cr.savepoint():
                if not document:
                    document = Documents.create({'application_id': application.id})
                for requirement, filename, content in uploads:
                    vals = {'filename': filename, 'file': content}
                    existing = Line.search([('document_id', '=', document.id), ('requirement_id', '=', requirement.id)], limit=1)
                    if existing:
                        existing.write(vals)
                    else:
                        Line.create(dict(vals, document_id=document.id, requirement_id=requirement.id))
                if uploads:
                    document.write({'last_portal_upload': fields.Datetime.now(), 'state': 'pending'})
        except (ValidationError, ValueError) as exc:
            return self._render_credit_documents_form(application, document, [str(exc)])
        except Exception:
            _logger.exception('Error al cargar documentos en solicitud %s', application.name)
            return self._render_credit_documents_form(application, document, [_('No se pudo guardar la documentación. Inténtelo nuevamente.')])

        missing = self._credit_document_errors(document)
        if not missing:
            document.action_mark_submitted()
            return request.redirect('/my/credito/documentos?uploaded=1')
        return self._render_credit_documents_form(application, document,
            [_('Documentación guardada, pero aún faltan: %s.') % ', '.join(missing)])
