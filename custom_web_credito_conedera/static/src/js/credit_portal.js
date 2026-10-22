/** Small progressive enhancements for the CONEDERA credit portal. */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        // Reuse the single terms checkbox supplied by custom_web_hr_datos_candidatos.
        // The controller also validates it server-side, so this is UX reinforcement only.
        var termsCheckbox = document.querySelector('form.oe_signup_form input#accept_terms[name="accept_terms"]');
        if (termsCheckbox) {
            termsCheckbox.required = true;
        }

        // Keep the native signup page in the background while the OTP modal is open.
        var signupOtpModal = document.getElementById('creditSignupOtpModal');
        if (signupOtpModal) {
            document.body.classList.add('modal-open');
            var otpInput = document.getElementById('verify_code');
            if (otpInput) {
                window.setTimeout(function () { otpInput.focus(); }, 50);
            }
        }

        // Countdown driven by the server-provided remaining lifetime of the current OTP.
        var countdown = document.getElementById('credit-otp-countdown');
        if (countdown) {
            var expiresAt = parseInt(countdown.getAttribute('data-expires-at') || '0', 10);
            var remaining = expiresAt > 0
                ? Math.max(0, Math.ceil(expiresAt - Date.now() / 1000))
                : Math.max(0, parseInt(countdown.getAttribute('data-remaining-seconds') || '0', 10));
            var timeLabel = document.getElementById('credit-otp-time');
            var waiting = document.getElementById('credit-otp-waiting');
            var expired = document.getElementById('credit-otp-expired');
            var resendForm = document.getElementById('credit-otp-resend-form');
            function paintCountdown() {
                if (remaining <= 0) {
                    if (timeLabel) { timeLabel.textContent = '00:00'; }
                    if (waiting) { waiting.classList.add('d-none'); }
                    if (expired) { expired.classList.remove('d-none'); }
                    if (resendForm) { resendForm.classList.remove('d-none'); }
                    return false;
                }
                var minutes = Math.floor(remaining / 60);
                var seconds = remaining % 60;
                if (timeLabel) {
                    timeLabel.textContent = String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
                }
                return true;
            }
            if (paintCountdown()) {
                var timer = window.setInterval(function () {
                    remaining -= 1;
                    if (!paintCountdown()) {
                        window.clearInterval(timer);
                    }
                }, 1000);
            }
        }
        document.querySelectorAll('.credit-form input[type="file"]').forEach(function (input) {
            input.addEventListener('change', function () {
                if (input.files && input.files.length && input.files[0].size > 12 * 1024 * 1024) {
                    window.alert('El archivo supera el límite de 12 MB. Seleccione un archivo más pequeño.');
                    input.value = '';
                }
            });
        });
    });
}());
