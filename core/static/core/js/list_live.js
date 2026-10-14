/* Shared lists: poll a small revision, preserve filters and position. */
(function () {
    'use strict';
    const status = document.querySelector('.sonrisar-list-live-status');
    if (!status) return;
    const message = status.querySelector('[data-live-message]');
    const refresh = status.querySelector('[data-live-refresh]');
    const root = document.querySelector(status.dataset.root);
    if (!root) return;
    const baseline = status.dataset.revision;
    const positionKey = 'sonrisarLiveListPosition';
    const interval = 8000;
    let lastInteraction = Date.now();
    let writes = 0;
    let dragging = false;
    let pending = false;
    let stopped = false;
    let reloading = false;
    let inFlight = false;
    let timer;

    window.sonrisarListLive = {
        beginWrite() { writes += 1; },
        endWrite() { writes = Math.max(0, writes - 1); lastInteraction = Date.now(); }
    };
    const touch = () => { lastInteraction = Date.now(); };
    ['pointerdown', 'keydown', 'input', 'change', 'touchstart', 'scroll'].forEach(event => {
        document.addEventListener(event, touch, {capture: true, passive: true});
    });
    document.addEventListener('dragstart', () => { dragging = true; touch(); }, true);
    document.addEventListener('dragend', () => { dragging = false; touch(); }, true);
    document.addEventListener('drop', () => { dragging = false; touch(); }, true);

    function editing() {
        const active = document.activeElement;
        if (active && active.matches('input, textarea, select, [contenteditable="true"]')) return true;
        // Preserve search text/results even after moving focus to another control.
        const query = document.getElementById('agendaPatientQuery');
        if (query && query.value.trim() !== query.defaultValue.trim()) return true;
        if (query && query.getAttribute('aria-expanded') === 'true') return true;
        return Boolean(document.querySelector('.modal.show, .offcanvas.show, .dropdown-menu.show'));
    }
    function blocked() {
        return writes > 0 || dragging || editing() || Boolean(root.querySelector('button:disabled, .dragging'));
    }
    function say(text, showButton = false) {
        message.textContent = text;
        refresh.hidden = !showButton;
        refresh.disabled = blocked();
        window.dispatchEvent?.(new Event("resize"));
    }
    function savePosition() {
        const navigation = document.querySelector('.header-fijo-sonrisar');
        const edge = navigation ? navigation.getBoundingClientRect().bottom : 0;
        const anchor = Array.from(root.querySelectorAll(status.dataset.anchors)).find(element => {
            const bounds = element.getBoundingClientRect();
            return bounds.bottom > edge && bounds.top < window.innerHeight;
        });
        try {
            sessionStorage.setItem(positionKey, JSON.stringify({
                url: location.pathname + location.search,
                x: window.scrollX, y: window.scrollY,
                target: anchor ? anchor.id : '',
                offset: anchor ? anchor.getBoundingClientRect().top : 0,
                tables: Array.from(root.querySelectorAll('.table-responsive')).map(el => el.scrollLeft),
                guardadoEn: Date.now()
            }));
            return true;
        } catch (_) {
            return false;
        }
    }
    function apply(manual = false) {
        if (reloading || stopped || !pending || blocked()) return false;
        if (!manual && Date.now() - lastInteraction < 4000) return false;
        // Avoid scroll jumps if the browser has disabled session storage.
        if (!savePosition() && !manual) {
            say('Hay cambios nuevos. Pulsá Actualizar ahora para verlos.', true);
            return false;
        }
        reloading = true;
        say('Actualizando lista…');
        location.reload();
        return true;
    }
    function restorePosition() {
        let saved;
        try { saved = JSON.parse(sessionStorage.getItem(positionKey)); } catch (_) { return; }
        if (!saved || saved.url !== location.pathname + location.search) return;
        try { sessionStorage.removeItem(positionKey); } catch (_) {}
        if (!Number.isFinite(saved.guardadoEn) || Date.now() - saved.guardadoEn > 120000) return;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const anchor = saved.target ? document.getElementById(saved.target) : null;
            const y = anchor && Number.isFinite(saved.offset)
                ? window.scrollY + anchor.getBoundingClientRect().top - saved.offset : saved.y;
            window.scrollTo(Number.isFinite(saved.x) ? saved.x : 0, Number.isFinite(y) ? Math.max(0,y) : 0);
            root.querySelectorAll('.table-responsive').forEach((el,i) => {
                if (saved.tables && Number.isFinite(saved.tables[i])) el.scrollLeft = saved.tables[i];
            });
        }));
    }
    if (document.readyState === 'complete') restorePosition();
    else window.addEventListener('load', restorePosition, {once:true});
    document.addEventListener('submit', event => {
        if (event.target.id !== 'agendaPatientSearch') { stopped = true; clearTimeout(timer); }
    }, true);
    function schedule() {
        clearTimeout(timer);
        if (!stopped && !reloading) timer = setTimeout(check, interval);
    }
    async function check() {
        if (stopped || reloading || inFlight) return;
        if (document.hidden || !navigator.onLine) {
            if (!navigator.onLine) say('Sin conexión. La lista se actualizará al reconectar.');
            schedule();
            return;
        }
        inFlight = true;
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 10000);
        try {
            const response = await fetch(status.dataset.url, {
                credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
                headers: {'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}
            });
            if (response.redirected || response.status === 401 || response.status === 403) {
                stopped = true;
                say('Tu sesión terminó. Ingresá nuevamente.', true);
                refresh.disabled = false;
                refresh.textContent = 'Ingresar';
                return;
            }
            if (!response.ok) throw new Error('No se pudo comprobar la lista');
            const data = await response.json();
            if (typeof data.revision !== 'string') throw new Error('Respuesta inválida');
            // Do not acknowledge a newer revision until its page has been loaded.
            pending = data.revision !== baseline;
            if (pending) {
                say('Hay cambios nuevos. La lista se actualizará cuando termines.', true);
                apply();
            } else {
                say('Actualización automática activa');
            }
        } catch (_) {
            say('No se pudo comprobar la lista. Se reintentará automáticamente.', pending);
        } finally {
            clearTimeout(timeout);
            inFlight = false;
            schedule();
        }
    }
    refresh.addEventListener('click', () => {
        if (stopped) {
            const url = new URL(status.dataset.loginUrl, location.origin);
            url.searchParams.set('next', location.pathname + location.search);
            location.assign(url.href);
        } else {
            apply(true);
        }
    });
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) { clearTimeout(timer); check(); }
    });
    window.addEventListener('online', () => { clearTimeout(timer); check(); });
    window.addEventListener('pagehide', () => { clearTimeout(timer); });
    window.addEventListener('pageshow', event => {
        if (event.persisted) { lastInteraction = Date.now(); check(); }
    });
    schedule();
})();
