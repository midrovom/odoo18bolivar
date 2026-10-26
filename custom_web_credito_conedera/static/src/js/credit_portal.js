/** Progressive enhancements for the CONEDERA credit portal. */
(function () {
    'use strict';

    function initCreditPortal() {
        // The checkbox is supplied by custom_web_hr_datos_candidatos.
        // The credit controller validates it server-side as well.
        var termsCheckbox = document.querySelector('form.oe_signup_form input#accept_terms[name="accept_terms"]');
        if (termsCheckbox) {
            termsCheckbox.required = true;
        }

        // Keep the native signup page behind the OTP modal while it is rendered.
        var signupOtpModal = document.getElementById('creditSignupOtpModal');
        if (signupOtpModal) {
            document.body.classList.add('modal-open');
            var otpInput = document.getElementById('verify_code');
            if (otpInput) {
                window.setTimeout(function () { otpInput.focus(); }, 50);
            }
        }

        // Recalculate from the server expiration timestamp on every tick. This avoids
        // a frozen or drifting countdown if the page loads late or an interval is delayed.
        var countdown = document.getElementById('credit-otp-countdown');
        if (countdown) {
            var expiresAtSeconds = Number(countdown.getAttribute('data-expires-at') || 0);
            var fallbackSeconds = Number(countdown.getAttribute('data-remaining-seconds') || 0);
            var expiresAtMs = expiresAtSeconds > 0
                ? expiresAtSeconds * 1000
                : Date.now() + Math.max(0, fallbackSeconds) * 1000;
            var timeLabel = document.getElementById('credit-otp-time');
            var waiting = document.getElementById('credit-otp-waiting');
            var expired = document.getElementById('credit-otp-expired');
            var resendForm = document.getElementById('credit-otp-resend-form');
            var timer = null;

            function paintCountdown() {
                var remaining = Math.max(0, Math.ceil((expiresAtMs - Date.now()) / 1000));
                if (remaining <= 0) {
                    if (timeLabel) { timeLabel.textContent = '00:00'; }
                    if (waiting) { waiting.classList.add('d-none'); }
                    if (expired) { expired.classList.remove('d-none'); }
                    if (resendForm) { resendForm.classList.remove('d-none'); }
                    if (timer !== null) {
                        window.clearInterval(timer);
                        timer = null;
                    }
                    return false;
                }

                var minutes = Math.floor(remaining / 60);
                var seconds = remaining % 60;
                if (timeLabel) {
                    timeLabel.textContent = String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
                }
                if (waiting) { waiting.classList.remove('d-none'); }
                if (expired) { expired.classList.add('d-none'); }
                if (resendForm) { resendForm.classList.add('d-none'); }
                return true;
            }

            // Paint immediately, then re-check often against the absolute deadline.
            // The visible label changes once a second, and expiration is not delayed.
            if (paintCountdown()) {
                timer = window.setInterval(paintCountdown, 250);
            }
        }

        // Validar también el dígito verificador de las cédulas (sin llamadas de red).
        function validCedula(value) {
            if (!/^[0-9]{10}$/.test(value)) { return false; }
            var province = Number(value.slice(0, 2));
            if (!((province >= 1 && province <= 24) || province === 30) || Number(value[2]) > 5) {
                return false;
            }
            var weights = [2, 1, 2, 1, 2, 1, 2, 1, 2];
            var total = 0;
            for (var j = 0; j < 9; j++) {
                var product = Number(value[j]) * weights[j];
                total += product > 9 ? product - 9 : product;
            }
            return (10 - total % 10) % 10 === Number(value[9]);
        }

        function validCedulaOrRuc(value) {
            if (value.length === 10) { return validCedula(value); }
            if (!/^[0-9]{13}$/.test(value)) { return false; }
            var province = Number(value.slice(0, 2));
            if (!((province >= 1 && province <= 24) || province === 30)) { return false; }
            var kind = Number(value[2]);
            if (kind <= 5) { return validCedula(value.slice(0, 10)) && Number(value.slice(10)) > 0; }
            if (kind === 6) { return Number(value.slice(9)) > 0; }
            if (kind === 9) { return Number(value.slice(10)) > 0; }
            return false;
        }

        var identityType = document.getElementById('credit-identification-type');
        var creditForm = document.querySelector('form.credit-form[data-credit-wizard="1"]');
        function identityValidation(input) {
            var value = input.value.trim();
            var kind = input.dataset.creditId;
            var type = identityType ? identityType.value : 'cedula';
            var valid = !value;
            var message = '';
            if (kind === 'applicant') {
                valid = valid || (type === 'cedula' ? validCedula(value) :
                    type === 'ruc' ? /^[0-9]{13}$/.test(value) :
                    type === 'foreign' ? /^[0-9]{10}$/.test(value) : false);
                message = 'Documento inválido. Cédula ecuatoriana: 10 dígitos y verificador; RUC: 13 dígitos; extranjera: 10 dígitos numéricos.';
                input.maxLength = type === 'ruc' ? 13 : 10;
                input.pattern = type === 'ruc' ? '[0-9]{13}' : '[0-9]{10}';
            } else if (kind === 'spouse' || kind === 'authorized_buyer' || kind === 'authorized_pickup') {
                // La cédula ecuatoriana se comprueba primero y, si no es válida,
                // se acepta un documento extranjero de 10 dígitos numéricos.
                valid = valid || validCedula(value) || /^[0-9]{10}$/.test(value);
                message = kind === 'spouse'
                    ? 'El documento del cónyuge debe tener 10 dígitos numéricos.'
                    : 'El documento de la persona autorizada debe tener exactamente 10 dígitos numéricos (cédula ecuatoriana o documento extranjero).';
            } else if (kind === 'business_ruc') {
                valid = valid || /^[0-9]{13}$/.test(value);
                message = 'El RUC del negocio debe contener exactamente 13 dígitos.';
            } else if (kind === 'mobile') {
                valid = valid || /^[0-9]{10}$/.test(value);
                message = 'El celular debe tener exactamente 10 dígitos numéricos.';
            }
            input.setCustomValidity(valid ? '' : message);
        }
        document.querySelectorAll('form.credit-form [data-credit-id]').forEach(function (input) {
            var validate = function () { identityValidation(input); };
            input.addEventListener('input', validate);
            input.addEventListener('change', validate);
            validate();
        });
        if (identityType && creditForm) {
            identityType.addEventListener('change', function () {
                var input = creditForm.querySelector('[data-credit-id="applicant"]');
                if (input) { identityValidation(input); }
            });
        }

        // Estado civil configurable: decidir por código estable, nunca por el texto.
        var maritalSelect = creditForm && creditForm.querySelector('[name="marital_status_id"]');
        if (maritalSelect) {
            function adjustSpouse() {
                var option = maritalSelect.options[maritalSelect.selectedIndex];
                var needsSpouse = Boolean(option && option.dataset.requiresSpouse === '1');
                creditForm.querySelectorAll('.credit-spouse-field').forEach(function (wrap) {
                    wrap.hidden = !needsSpouse;
                    wrap.querySelectorAll('input').forEach(function (input) {
                        input.disabled = !needsSpouse;
                        input.required = needsSpouse;
                        if (!needsSpouse) { input.value = ''; input.setCustomValidity(''); }
                    });
                });
            }
            maritalSelect.addEventListener('change', adjustSpouse);
            adjustSpouse();
        }

        // Añadir referencias sin un límite fijo de tres (límite técnico 30 por sección).
        document.querySelectorAll('[data-credit-reference-body]').forEach(function (body) {
            var typ = body.dataset.creditReferenceBody;
            var add = document.querySelector('[data-credit-add-reference="' + typ + '"]');
            var countInput = creditForm && creditForm.querySelector('[name="' + typ + '_count"]');
            var maxRows = Number(body.dataset.maxReferences || 30);
            if (!add || !countInput) { return; }
            function renumber() {
                var rows = body.querySelectorAll('.credit-reference-row');
                rows.forEach(function (row, index) {
                    var n = index + 1;
                    row.querySelectorAll('[name]').forEach(function (field) {
                        field.name = field.name.replace(/_[0-9]+$/, '_' + n);
                    });
                });
                countInput.value = String(rows.length);
                add.disabled = rows.length >= maxRows;
            }
            add.addEventListener('click', function () {
                var rows = body.querySelectorAll('.credit-reference-row');
                if (!rows.length || rows.length >= maxRows) { return; }
                var clone = rows[0].cloneNode(true);
                clone.querySelectorAll('input').forEach(function (field) { field.value = ''; });
                clone.querySelectorAll('select').forEach(function (field) { field.selectedIndex = 0; });
                var actionCell = clone.querySelector('td:last-child');
                if (actionCell) {
                    actionCell.innerHTML = '';
                    var remove = document.createElement('button');
                    remove.type = 'button';
                    remove.className = 'btn btn-outline-danger btn-sm';
                    remove.dataset.creditRemoveReference = '1';
                    remove.textContent = 'Quitar';
                    actionCell.appendChild(remove);
                }
                body.appendChild(clone);
                renumber();
                var first = clone.querySelector('input');
                if (first) { first.focus(); }
            });
            body.addEventListener('click', function (event) {
                var remove = event.target.closest('[data-credit-remove-reference]');
                if (remove && body.querySelectorAll('.credit-reference-row').length > 3) {
                    remove.closest('.credit-reference-row').remove();
                    renumber();
                }
            });
            renumber();
        });

        // Vista previa inmediata del croquis en el formulario del historial.
        // El archivo se muestra localmente; solo se guarda al pulsar "Guardar croquis".
        var historySketchFile = document.getElementById('credit-review-sketch-file');
        var historySketchPreview = document.getElementById('credit-review-sketch-preview');
        if (historySketchFile && historySketchPreview) {
            var activeObjectUrl = null;
            var maxSize = 12 * 1024 * 1024;
            var showWarning = document.getElementById('credit-review-sketch-warning');
            var setWarning = function (message) {
                if (showWarning) {
                    showWarning.textContent = message || '';
                    showWarning.hidden = !message;
                }
            };
            historySketchFile.addEventListener('change', function () {
                if (activeObjectUrl) { URL.revokeObjectURL(activeObjectUrl); activeObjectUrl = null; }
                historySketchPreview.replaceChildren();
                var file = historySketchFile.files && historySketchFile.files[0];
                if (!file) { return; }
                var ext = file.name.split('.').pop().toLowerCase();
                var isPdf = ext === 'pdf' && (file.type === 'application/pdf' || !file.type);
                var isImage = ['png','jpg','jpeg','webp'].includes(ext) && (!file.type || file.type.startsWith('image/'));
                if ((!isPdf && !isImage) || file.size > maxSize || !file.size) {
                    setWarning('Adjunte una imagen PNG, JPG, WEBP o un PDF de hasta 12 MB.');
                    historySketchFile.value = '';
                    return;
                }
                setWarning('');
                activeObjectUrl = URL.createObjectURL(file);
                var preview = document.createElement(isPdf ? 'iframe' : 'img');
                preview.className = isPdf ? 'credit-sketch-review-pdf' : 'credit-sketch-review-image';
                preview.title = 'Vista previa del croquis seleccionado';
                if (!isPdf) { preview.alt = 'Croquis seleccionado para adjuntar'; }
                preview.src = activeObjectUrl;
                historySketchPreview.appendChild(preview);
                var description = document.createElement('small');
                description.className = 'd-block text-muted mt-2';
                description.textContent = file.name + ' · ' + (file.size / 1024 / 1024).toFixed(2) + ' MB';
                historySketchPreview.appendChild(description);
            });
            window.addEventListener('pagehide', function () {
                if (activeObjectUrl) { URL.revokeObjectURL(activeObjectUrl); }
            }, { once: true });
        }

        // Geolocalización del navegador: exige HTTPS (salvo localhost) y permiso del usuario.
        // Se informa la causa real del error sin sustituir la seguridad del navegador.
        var locateButton = document.getElementById('credit-get-location');
        if (locateButton) {
            locateButton.addEventListener('click', function () {
                if (window.isSecureContext === false) {
                    window.alert('La ubicación automática requiere abrir el portal con HTTPS y un certificado válido. Está usando una conexión no segura (HTTP). Abra el portal con https:// y vuelva a intentarlo; mientras tanto puede escribir latitud y longitud manualmente.');
                    return;
                }
                if (!navigator.geolocation) {
                    window.alert('La geolocalización no está disponible en este navegador o está bloqueada. Revise que el portal utilice HTTPS y que el navegador permita la ubicación. También puede introducir las coordenadas manualmente.');
                    return;
                }
                var latitudeInput = document.getElementById('credit-business-latitude');
                var longitudeInput = document.getElementById('credit-business-longitude');
                if (!latitudeInput || !longitudeInput) { return; }
                var initialText = locateButton.textContent;
                locateButton.disabled = true;
                locateButton.textContent = 'Obteniendo ubicación...';
                function finish() {
                    locateButton.disabled = false;
                    locateButton.textContent = initialText;
                }
                navigator.geolocation.getCurrentPosition(function (position) {
                    latitudeInput.value = position.coords.latitude.toFixed(7);
                    longitudeInput.value = position.coords.longitude.toFixed(7);
                    latitudeInput.dispatchEvent(new Event('input', { bubbles: true }));
                    longitudeInput.dispatchEvent(new Event('input', { bubbles: true }));
                    finish();
                }, function (error) {
                    finish();
                    var message;
                    if (error.code === 1) {
                        message = 'El navegador denegó el permiso para acceder a su ubicación. Abra los permisos del sitio en la barra de direcciones, permita Ubicación y vuelva a intentarlo. Si utiliza HTTPS, compruebe también los permisos de ubicación del dispositivo.';
                    } else if (error.code === 2) {
                        message = 'El dispositivo no pudo determinar su ubicación. Active la ubicación/GPS del dispositivo, compruebe la conexión y vuelva a intentarlo.';
                    } else if (error.code === 3) {
                        message = 'Se agotó el tiempo para obtener la ubicación. Pruebe en un lugar con mejor señal GPS o escriba las coordenadas manualmente.';
                    } else {
                        message = 'No fue posible obtener su ubicación. Compruebe los permisos del navegador o escriba las coordenadas manualmente.';
                    }
                    window.alert(message);
                }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 });
            });
        }
        if (creditForm) {
            var latitude = creditForm.querySelector('[name="business_latitude"]');
            var longitude = creditForm.querySelector('[name="business_longitude"]');
            if (latitude && longitude) {
                function validateCoordinates() {
                    var missingPair = Boolean(latitude.value.trim()) !== Boolean(longitude.value.trim());
                    latitude.setCustomValidity(missingPair ? 'Debe ingresar latitud y longitud juntas.' : '');
                    longitude.setCustomValidity(missingPair ? 'Debe ingresar latitud y longitud juntas.' : '');
                }
                latitude.addEventListener('input', validateCoordinates);
                longitude.addEventListener('input', validateCoordinates);
                validateCoordinates();
            }
        }

        // Se muestra un solo vehículo por defecto. Cada clic agrega otro
        // vehículo opcional y se manda al servidor en vehicle_ids (One2many).
        var vehiclesContainer = document.getElementById('credit-vehicles');
        var addVehicleButton = document.getElementById('credit-add-vehicle');
        var vehicleCountInput = document.getElementById('credit-vehicle-count');
        if (vehiclesContainer && addVehicleButton && vehicleCountInput) {
            var maxVehicles = Number(vehiclesContainer.dataset.maxVehicles || 30);
            function renumberVehicles() {
                var rows = vehiclesContainer.querySelectorAll('.credit-vehicle-row');
                rows.forEach(function (row, index) {
                    var n = index + 1;
                    row.dataset.vehicleIndex = String(n);
                    var heading = row.querySelector('h3');
                    if (heading) { heading.textContent = 'Vehículo ' + n; }
                    row.querySelectorAll('[name]').forEach(function (input) {
                        input.name = input.name.replace(/^vehicle[0-9]+_/, 'vehicle' + n + '_');
                    });
                });
                vehicleCountInput.value = String(rows.length);
                addVehicleButton.disabled = rows.length >= maxVehicles;
            }
            addVehicleButton.addEventListener('click', function () {
                var rows = vehiclesContainer.querySelectorAll('.credit-vehicle-row');
                if (rows.length >= maxVehicles) { return; }
                var clone = rows[0].cloneNode(true);
                clone.querySelectorAll('input').forEach(function (input) { input.value = ''; });
                var headingWrap = clone.querySelector('.d-flex');
                if (headingWrap && !clone.querySelector('[data-credit-remove-vehicle]')) {
                    var remove = document.createElement('button');
                    remove.type = 'button';
                    remove.className = 'btn btn-outline-danger btn-sm';
                    remove.dataset.creditRemoveVehicle = '1';
                    remove.textContent = 'Quitar';
                    headingWrap.appendChild(remove);
                }
                vehiclesContainer.appendChild(clone);
                renumberVehicles();
                var firstField = clone.querySelector('input');
                if (firstField) { firstField.focus(); }
            });
            vehiclesContainer.addEventListener('click', function (event) {
                var remove = event.target.closest('[data-credit-remove-vehicle]');
                if (!remove) { return; }
                var row = remove.closest('.credit-vehicle-row');
                if (row && Number(row.dataset.vehicleIndex) > 1) {
                    row.remove();
                    renumberVehicles();
                }
            });
            renumberVehicles();
        }

        // Cinco pantallas de la solicitud. Los datos permanecen en el mismo form
        // mientras se avanza o retrocede. El servidor valida todas las aceptaciones.
        var wizard = document.querySelector('form.credit-form[data-credit-wizard="1"]');
        if (wizard && !wizard.dataset.creditWizardInitialized) {
            wizard.dataset.creditWizardInitialized = '1';
            var panels = Array.from(wizard.querySelectorAll('.credit-step-panel[data-credit-step]'));
            var indicators = Array.from(wizard.querySelectorAll('[data-credit-step-indicator]'));
            var backButton = wizard.querySelector('[data-credit-prev]');
            var nextButton = wizard.querySelector('[data-credit-next]');
            var submitButton = wizard.querySelector('[data-credit-submit]');
            var progress = wizard.querySelector('.credit-wizard-progress');
            var currentStep = Math.min(5, Math.max(1, parseInt(wizard.dataset.startStep || '1', 10) || 1));

            function showStep(step, fromClick) {
                currentStep = Math.min(panels.length, Math.max(1, step));
                panels.forEach(function (panel, index) {
                    var active = (index + 1 === currentStep);
                    panel.classList.toggle('is-active', active);
                    panel.setAttribute('aria-hidden', String(!active));
                });
                indicators.forEach(function (indicator, index) {
                    var active = (index + 1 === currentStep);
                    indicator.classList.toggle('is-active', active);
                    indicator.classList.toggle('is-complete', index + 1 < currentStep);
                    if (active) {
                        indicator.setAttribute('aria-current', 'step');
                    } else {
                        indicator.removeAttribute('aria-current');
                    }
                });
                if (backButton) { backButton.hidden = currentStep === 1; }
                if (nextButton) { nextButton.hidden = currentStep === panels.length; }
                if (submitButton) { submitButton.hidden = currentStep !== panels.length; }
                if (fromClick && progress) {
                    progress.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }

            function validateStep(step) {
                var panel = panels[step - 1];
                if (!panel) { return true; }
                var fields = panel.querySelectorAll('input, select, textarea');
                for (var i = 0; i < fields.length; i++) {
                    var field = fields[i];
                    if (!field.disabled && !field.checkValidity()) {
                        showStep(step, true);
                        field.reportValidity();
                        field.focus();
                        return false;
                    }
                }
                return true;
            }

            // Use JS client-side validation because hidden HTML5 controls in other
            // steps cannot be focused by the browser's native submit validator.
            // Hidden steps are validated in validateStep(), so disable native
            // submit validation, which cannot focus fields in hidden panels.
            wizard.noValidate = true;
            wizard.classList.add('credit-wizard-ready');
            showStep(currentStep, false);
            if (backButton) {
                backButton.addEventListener('click', function () {
                    showStep(currentStep - 1, true);
                });
            }
            if (nextButton) {
                nextButton.addEventListener('click', function () {
                    if (validateStep(currentStep)) { showStep(currentStep + 1, true); }
                });
            }
            wizard.addEventListener('submit', function (event) {
                // Check all pages, including the declaration and ALL the
                // additional consent checkboxes on the final page.
                for (var step = 1; step <= panels.length; step++) {
                    if (!validateStep(step)) {
                        event.preventDefault();
                        event.stopPropagation();
                        return;
                    }
                }
                showStep(panels.length, false);
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.textContent = creditForm && creditForm.querySelector('[name="credit_edit_mode"]') ? 'Guardando cambios...' : 'Enviando solicitud...';
                }
            });
        }

        document.querySelectorAll('.credit-form input[type="file"]').forEach(function (input) {
            input.addEventListener('change', function () {
                if (input.files && input.files.length && input.files[0].size > 12 * 1024 * 1024) {
                    window.alert('El archivo supera el límite de 12 MB. Seleccione un archivo más pequeño.');
                    input.value = '';
                }
            });
        });
    }

    // Odoo can load frontend assets after DOMContentLoaded in some navigation flows.
    // Initialize in either case so the countdown never relies on a missed event.
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCreditPortal, { once: true });
    } else {
        initCreditPortal();
    }
}());
