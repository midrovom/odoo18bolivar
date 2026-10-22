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
                    submitButton.textContent = 'Enviando solicitud...';
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
