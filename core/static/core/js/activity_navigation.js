/* Preserve the origin URL and scroll position when consulting activity. */
(function () {
    'use strict';
    const key = 'sonrisarActivityReturnPosition';
    const currentURL = () => location.pathname + location.search + location.hash;
    document.addEventListener('click', function (event) {
        if (!(event.target instanceof Element)) return;
        const open = event.target.closest('.js-activity-open');
        if (open && !location.pathname.startsWith('/actividad/')) {
            const url = new URL(open.href, location.origin);
            url.searchParams.set('volver', currentURL());
            open.href = url.href;
            const header = document.querySelector('.header-fijo-sonrisar');
            const edge = header ? header.getBoundingClientRect().bottom : 0;
            const anchor = Array.from(document.querySelectorAll('[id^="cita-"], [id^="hora-"], .deudor-card[id]')).find(element => {
                const bounds = element.getBoundingClientRect();
                return bounds.bottom > edge && bounds.top < window.innerHeight;
            });
            try {
                sessionStorage.setItem(key, JSON.stringify({url:currentURL(), x:window.scrollX, y:window.scrollY,
                    target:anchor ? anchor.id : '', offset:anchor ? anchor.getBoundingClientRect().top : 0,
                    saved:Date.now(), ready:false}));
            } catch (_) {}
        }
        const back = event.target.closest('.js-activity-return');
        if (back) {
            try {
                const saved = JSON.parse(sessionStorage.getItem(key));
                const destination = new URL(back.href, location.origin);
                if (saved && saved.url === destination.pathname + destination.search + destination.hash) {
                    saved.ready = true;
                    sessionStorage.setItem(key, JSON.stringify(saved));
                }
            } catch (_) {}
        }
    });
    function restore() {
        let saved;
        try { saved = JSON.parse(sessionStorage.getItem(key)); } catch (_) { return; }
        if (!saved || !saved.ready || saved.url !== currentURL()) return;
        try { sessionStorage.removeItem(key); } catch (_) {}
        if (!Number.isFinite(saved.saved) || Date.now() - saved.saved > 7200000) return;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            const target = saved.target ? document.getElementById(saved.target) : null;
            const y = target && Number.isFinite(saved.offset)
                ? window.scrollY + target.getBoundingClientRect().top - saved.offset : saved.y;
            window.scrollTo(Number.isFinite(saved.x) ? saved.x : 0, Number.isFinite(y) ? Math.max(0,y) : 0);
        }));
    }
    if (document.readyState === 'complete') restore();
    else window.addEventListener('load', restore, {once:true});
    window.addEventListener('pageshow', restore);
})();
