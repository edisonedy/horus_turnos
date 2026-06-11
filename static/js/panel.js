document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('input[type="checkbox"].form-control').forEach((input) => {
        input.classList.remove('form-control');
        input.classList.add('form-check-input');
    });
});
