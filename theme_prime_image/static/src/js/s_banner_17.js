odoo.define('theme_prime_image.s_banner_17', function (require) {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        if (window.innerWidth <= 768) {
            new Swiper('.swiper-container', {
                slidesPerView: 5,
                spaceBetween: 10,
                loop: true,
                pagination: {
                    el: '.swiper-pagination',
                    clickable: true,
                },
                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },
            });
        }
    });
});
