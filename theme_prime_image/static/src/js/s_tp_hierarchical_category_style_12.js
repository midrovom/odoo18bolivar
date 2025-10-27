/** @odoo-module **/

function scrollSlider(direction) {
    const slider = document.getElementById('tpCategorySlider');
    const scrollAmount = 220;
    if (slider) {
        slider.scrollBy({
            left: direction * scrollAmount,
            behavior: 'smooth'
        });
    }
}

// Ejecutar solo cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', () => {
    const leftBtn = document.querySelector('.tp-slider-left');
    const rightBtn = document.querySelector('.tp-slider-right');

    if (leftBtn) {
        leftBtn.addEventListener('click', () => scrollSlider(-1));
    }
    if (rightBtn) {
        rightBtn.addEventListener('click', () => scrollSlider(1));
    }
});
