(() => {
    'use strict';

    const CLAVE_SCROLL = 'daya:menu-scroll';

    // --- Restaurar el scroll del menu ANTES de pintar -------------------------
    // El panel navega con recargas normales; sin esto el menu volvia arriba
    // en cada click y se perdia el sitio donde estabas.
    const restaurarScroll = () => {
        const menu = document.getElementById('appSidebar');
        if (!menu) return null;
        try {
            const guardado = sessionStorage.getItem(CLAVE_SCROLL);
            if (guardado) menu.scrollTop = parseInt(guardado, 10) || 0;
        } catch (e) { /* sessionStorage bloqueado: seguimos igual */ }
        return menu;
    };

    // El script va al final del <body>, asi que el menu ya existe aqui.
    const menuTemprano = restaurarScroll();

    const guardarScroll = (menu) => {
        try { sessionStorage.setItem(CLAVE_SCROLL, String(menu.scrollTop)); } catch (e) { /* noop */ }
    };

    document.addEventListener('DOMContentLoaded', () => {
        const menu = menuTemprano || document.getElementById('appSidebar');
        const links = Array.from(document.querySelectorAll('.app-sidebar .sidebar-link'));

        // Marca activo el enlace cuya ruta calza mejor con la URL actual
        // (asi /panel/turnos/12/ tambien ilumina "Turnos").
        let activo = null;
        if (links.length) {
            const path = window.location.pathname;
            let mejorLargo = 0;
            links.forEach((link) => {
                const href = link.getAttribute('href') || '';
                if (!href.startsWith('/')) return;
                if ((path === href || path.startsWith(href)) && href.length > mejorLargo) {
                    activo = link;
                    mejorLargo = href.length;
                }
            });
            if (activo) {
                activo.classList.add('is-active');
                activo.setAttribute('aria-current', 'page');
            }
        }

        if (menu) {
            // Guardar la posicion al salir y al hacer scroll, para que la
            // siguiente pagina abra el menu exactamente igual.
            menu.addEventListener('scroll', () => guardarScroll(menu), { passive: true });
            window.addEventListener('pagehide', () => guardarScroll(menu));
            links.forEach((link) => link.addEventListener('click', () => guardarScroll(menu)));

            // Solo la primera vez (sin posicion guardada) acercamos el activo.
            let sinGuardar = true;
            try { sinGuardar = sessionStorage.getItem(CLAVE_SCROLL) === null; } catch (e) { /* noop */ }
            if (sinGuardar && activo) {
                window.addEventListener('load', () => {
                    const fuera = activo.offsetTop + activo.offsetHeight > menu.scrollTop + menu.clientHeight
                        || activo.offsetTop < menu.scrollTop;
                    if (fuera) activo.scrollIntoView({ block: 'nearest' });
                });
            }
        }

        // Menu lateral en movil
        const toggle = document.getElementById('sidebarToggle');
        const scrim = document.getElementById('sidebarScrim');
        const cerrarMenu = () => {
            if (!menu) return;
            menu.classList.remove('is-open');
            if (scrim) scrim.classList.remove('is-open');
            if (toggle) toggle.setAttribute('aria-expanded', 'false');
        };
        if (toggle && menu) {
            toggle.addEventListener('click', () => {
                const abierto = menu.classList.toggle('is-open');
                if (scrim) scrim.classList.toggle('is-open', abierto);
                toggle.setAttribute('aria-expanded', abierto ? 'true' : 'false');
            });
        }
        if (scrim) scrim.addEventListener('click', cerrarMenu);
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') cerrarMenu();
        });

        // Filtro rapido del menu (ignora acentos)
        const filtro = document.getElementById('sidebarFilter');
        const vacio = document.getElementById('sidebarEmpty');
        if (filtro && links.length) {
            const normaliza = (texto) => texto
                .toLowerCase()
                .normalize('NFD')
                .replace(/[̀-ͯ]/g, '');

            filtro.addEventListener('input', () => {
                const termino = normaliza(filtro.value.trim());
                let visibles = 0;
                links.forEach((link) => {
                    const coincide = !termino || normaliza(link.textContent).includes(termino);
                    link.classList.toggle('is-hidden', !coincide);
                    if (coincide) visibles += 1;
                });
                document.querySelectorAll('.app-sidebar .sb-label').forEach((label) => {
                    label.style.display = label.parentElement.querySelector('.sidebar-link:not(.is-hidden)') ? '' : 'none';
                });
                if (vacio) vacio.style.display = visibles ? 'none' : 'block';
            });
        }

        // Ir al buscador del menu con "/" (como en las apps modernas)
        document.addEventListener('keydown', (event) => {
            const enCampo = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName)
                || document.activeElement.isContentEditable;
            if (event.key === '/' && !enCampo && filtro) {
                event.preventDefault();
                filtro.focus();
                filtro.select();
            }
        });
    });
})();
