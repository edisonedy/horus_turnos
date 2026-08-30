/* Daya Facial Care — interacciones de la landing.
   Sin librerías externas: todo nativo para que la página cargue rápido. */
(() => {
    'use strict';

    const menosMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => Array.from(document.querySelectorAll(sel));

    // ---------- Nav: sombra al bajar + barra de progreso ----------
    const nav = $('#dayaNav');
    const barra = $('#scrollProgress');
    const cta = $('#mobileCta');

    const alScrollear = () => {
        const y = window.scrollY;
        if (nav) nav.classList.toggle('scrolled', y > 40);
        if (barra) {
            const alto = document.documentElement.scrollHeight - window.innerHeight;
            barra.style.width = alto > 0 ? (y / alto * 100) + '%' : '0%';
        }
        // La barra inferior aparece cuando ya pasaste el hero (si no, estorba).
        if (cta) cta.classList.toggle('visible', y > window.innerHeight * 0.75);
    };
    window.addEventListener('scroll', alScrollear, { passive: true });
    alScrollear();

    // ---------- Menú móvil ----------
    const burger = $('#burger');
    const links = $('#navLinks');
    if (burger && links) {
        burger.addEventListener('click', () => {
            const abierto = links.classList.toggle('open');
            burger.setAttribute('aria-expanded', abierto ? 'true' : 'false');
            burger.innerHTML = abierto ? '<i class="bi bi-x-lg"></i>' : '<i class="bi bi-list"></i>';
        });
        links.querySelectorAll('a').forEach((a) => a.addEventListener('click', () => {
            links.classList.remove('open');
            burger.setAttribute('aria-expanded', 'false');
            burger.innerHTML = '<i class="bi bi-list"></i>';
        }));
    }

    // ---------- Apariciones al hacer scroll ----------
    const reveals = $$('.reveal');
    if (menosMovimiento) {
        reveals.forEach((el) => el.classList.add('in'));
    } else if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entradas) => {
            entradas.forEach((e) => {
                if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
            });
        }, { threshold: 0.12 });
        reveals.forEach((el) => io.observe(el));
    } else {
        reveals.forEach((el) => el.classList.add('in'));
    }

    // ---------- Sección activa en el menú ----------
    const secciones = $$('section[id], header[id]');
    const enlacesNav = $$('#navLinks a[href^="#"]');
    if (secciones.length && enlacesNav.length && 'IntersectionObserver' in window) {
        const spy = new IntersectionObserver((entradas) => {
            entradas.forEach((e) => {
                if (!e.isIntersecting) return;
                enlacesNav.forEach((a) => a.classList.toggle(
                    'activo', a.getAttribute('href') === '#' + e.target.id));
            });
        }, { rootMargin: '-45% 0px -50% 0px' });
        secciones.forEach((s) => spy.observe(s));
    }

    // ---------- Números que suben ----------
    const contadores = $$('[data-cuenta]');
    if (contadores.length && !menosMovimiento && 'IntersectionObserver' in window) {
        const formatea = (valor, formato) => (
            formato === 'mil' && valor >= 1000
                ? (valor / 1000).toFixed(1).replace('.0', '') + 'k'
                : String(valor)
        );
        const io = new IntersectionObserver((entradas) => {
            entradas.forEach((e) => {
                if (!e.isIntersecting) return;
                const el = e.target;
                io.unobserve(el);
                const destino = parseFloat(el.dataset.cuenta) || 0;
                const sufijo = el.dataset.sufijo || '';
                const formato = el.dataset.formato || '';
                const inicio = performance.now();
                const duracion = 1400;
                const paso = (ahora) => {
                    const t = Math.min((ahora - inicio) / duracion, 1);
                    const suave = 1 - Math.pow(1 - t, 3);
                    el.textContent = formatea(Math.round(destino * suave), formato) + sufijo;
                    if (t < 1) requestAnimationFrame(paso);
                };
                requestAnimationFrame(paso);
            });
        }, { threshold: 0.6 });
        contadores.forEach((el) => io.observe(el));
    }

    // ---------- Parallax suave del retrato ----------
    const conParallax = $$('[data-parallax]');
    if (conParallax.length && !menosMovimiento) {
        let pendiente = false;
        const mover = () => {
            pendiente = false;
            conParallax.forEach((el) => {
                const factor = parseFloat(el.dataset.parallax) || 0.05;
                const caja = el.getBoundingClientRect();
                const centro = caja.top + caja.height / 2 - window.innerHeight / 2;
                el.style.transform = 'translate3d(0,' + (-centro * factor).toFixed(1) + 'px,0)';
            });
        };
        window.addEventListener('scroll', () => {
            if (!pendiente) { pendiente = true; requestAnimationFrame(mover); }
        }, { passive: true });
        mover();
    }

    // ---------- Visor de galería ----------
    const visor = $('#lightbox');
    const visorImg = $('#lbImg');
    const fotos = $$('.gallery-item');
    if (visor && visorImg && fotos.length) {
        let indice = 0;
        const abrir = (i) => {
            indice = (i + fotos.length) % fotos.length;
            visorImg.src = fotos[indice].dataset.full;
            visor.classList.add('abierto');
            document.body.style.overflow = 'hidden';
        };
        const cerrar = () => {
            visor.classList.remove('abierto');
            document.body.style.overflow = '';
        };
        fotos.forEach((boton, i) => boton.addEventListener('click', () => abrir(i)));
        $('#lbCerrar').addEventListener('click', cerrar);
        $('#lbPrev').addEventListener('click', () => abrir(indice - 1));
        $('#lbNext').addEventListener('click', () => abrir(indice + 1));
        visor.addEventListener('click', (e) => { if (e.target === visor) cerrar(); });
        document.addEventListener('keydown', (e) => {
            if (!visor.classList.contains('abierto')) return;
            if (e.key === 'Escape') cerrar();
            if (e.key === 'ArrowRight') abrir(indice + 1);
            if (e.key === 'ArrowLeft') abrir(indice - 1);
        });
    }
})();
