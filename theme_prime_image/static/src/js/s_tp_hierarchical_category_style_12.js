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

window.scrollSlider = scrollSlider;
