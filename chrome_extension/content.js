// Coffee & Axl - Content Script
// Widget timer pentru site-uri cu limita

(function() {
    'use strict';

    const domain = window.location.hostname
        .replace('www.', '');

    // Verifica regulile si afiseaza widget
    // Trimite mesajul dupa ce DOM-ul e gata
    function init() {
        chrome.runtime.sendMessage({
            type:   'get_site_status',
            domain: domain,
        }, (response) => {
            if (!response) return;

            if (response.status === 'blocked' ||
                    response.status === 'limit_exceeded') {
                showBlockedPage(
                    response.status === 'limit_exceeded');
            } else if (response.status === 'limited') {
                showTimerWidget(
                    response.limit_minutes,
                    response.used_seconds);
            }
        });
    }

    // Asteapta body-ul — run_at: document_start
    // inseamna ca body poate sa nu existe inca
    if (document.body) {
        init();
    } else {
        document.addEventListener(
            'DOMContentLoaded', init);
    }

    // ── Pagina blocata ──────────────────────────

    function showBlockedPage(limitat) {
        window.stop();

        const domain    = window.location.hostname.replace('www.', '');
        const icon      = limitat ? '⏱' : '🚫';
        const titlu     = limitat ? 'Timp epuizat' : 'Site blocat';
        const accentClr = limitat ? '#E65100' : '#E53935';
        const msg       = limitat
            ? 'Ai folosit tot timpul alocat pentru acest site astazi.<br>Limita se reseteaza automat la miezul noptii.'
            : 'Acest site este blocat de Coffee & Axl<br>pentru bunastarea ta digitala.';

        // Info reset apare DOAR la site-uri limitate, NU la blocate
        const resetInfo = limitat
            ? `<div class="reset-info">
                Acces disponibil din nou la <span>00:00</span>
               </div>`
            : '';

        document.documentElement.innerHTML = `
        <html>
        <head>
            <meta charset="UTF-8">
            <title>${titlu} - Coffee & Axl</title>
            <style>
                * { margin:0; padding:0; box-sizing:border-box; }
                body {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    background: #1A1A1A;
                    color: white;
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 24px;
                }
                .icon { font-size: 72px; margin-bottom: 16px; }
                h1 { color: ${accentClr}; font-size: 28px; margin-bottom: 8px; }
                .domain {
                    color: #AAAAAA; font-size: 18px;
                    margin-bottom: 24px; font-family: monospace;
                    background: #222; padding: 4px 16px;
                    border-radius: 6px;
                }
                .msg {
                    color: #888; font-size: 14px;
                    max-width: 420px; line-height: 1.8;
                    margin-bottom: 24px;
                }
                .reset-info {
                    background: #2A2A2A; border: 1px solid #333;
                    border-radius: 8px; padding: 10px 24px;
                    font-size: 12px; color: #666; margin-bottom: 20px;
                }
                .reset-info span { color: #F9A825; font-weight: bold; }
                .brand { color: #F9A825; font-size: 12px; margin-top: 24px; opacity: 0.7; }
                .back-btn {
                    background: #2A2A2A; color: #AAAAAA;
                    border: 1px solid #444; border-radius: 6px;
                    padding: 10px 28px; font-size: 13px; cursor: pointer;
                }
                .back-btn:hover { background: #333; }
            </style>
        </head>
        <body>
            <div class="icon">${icon}</div>
            <h1>${titlu}</h1>
            <div class="domain">${domain}</div>
            <div class="msg">${msg}</div>
            ${resetInfo}
            <button class="back-btn" onclick="history.back()">Inapoi</button>
            <div class="brand">Coffee & Axl Wellness</div>
        </body>
        </html>`;
    }

        // ── Widget timer ─────────────────────────────

    function showTimerWidget(limitMinutes,
                              usedSeconds) {
        const limitSeconds  = limitMinutes * 60;
        let   remaining     = limitSeconds - usedSeconds;
        const sessionStart  = Date.now();
        let   timerInterval = null;
        let   minimized     = false;

        // Creeaza widget
        const widget = document.createElement('div');
        widget.id = 'ca-timer-widget';
        widget.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 2147483647;
            background: rgba(26, 26, 26, 0.95);
            color: white;
            border-radius: 12px;
            padding: 10px 14px;
            font-family: Arial, sans-serif;
            font-size: 13px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.5);
            border: 2px solid #F57F17;
            min-width: 180px;
            cursor: move;
            user-select: none;
            transition: border-color 0.3s, opacity 0.3s;
            backdrop-filter: blur(4px);
        `;

        widget.innerHTML = `
            <div id="ca-header" style="
                display:flex;
                align-items:center;
                justify-content:space-between;
                margin-bottom:8px;
                cursor:move;">
                <span style="
                    color:#F9A825;
                    font-weight:bold;
                    font-size:11px;
                    letter-spacing:0.5px;">
                    Coffee & Axl
                </span>
                <span id="ca-minimize-btn" style="
                    cursor:pointer;
                    color:#555;
                    font-size:18px;
                    line-height:1;
                    padding: 0 2px;
                    transition: color 0.2s;">
                    &#8212;
                </span>
            </div>
            <div id="ca-widget-body">
                <div style="
                    color:#888;
                    font-size:10px;
                    margin-bottom:4px;
                    text-overflow:ellipsis;
                    overflow:hidden;
                    white-space:nowrap;">
                    ${domain}
                </div>
                <div id="ca-timer-display" style="
                    font-size:26px;
                    font-weight:bold;
                    font-family:monospace;
                    text-align:center;
                    color:white;
                    margin:4px 0;
                    letter-spacing:2px;">
                    ${formatTime(remaining)}
                </div>
                <div id="ca-progress-bar" style="
                    height:4px;
                    background:#333;
                    border-radius:2px;
                    margin-top:8px;
                    overflow:hidden;">
                    <div id="ca-progress-fill" style="
                        height:100%;
                        border-radius:2px;
                        background:#F57F17;
                        transition:width 1s linear;
                        width:${pct(remaining, limitSeconds)}%;">
                    </div>
                </div>
                <div style="
                    color:#555;
                    font-size:10px;
                    text-align:center;
                    margin-top:5px;">
                    din ${limitMinutes} min/zi
                </div>
            </div>
        `;

        // Adauga pe pagina dupa ce body e gata
        document.body.appendChild(widget);

        // Minimizare
        document.getElementById('ca-minimize-btn')
            .addEventListener('click', (e) => {
            e.stopPropagation();
            const body = document.getElementById(
                'ca-widget-body');
            minimized = !minimized;
            body.style.display =
                minimized ? 'none' : 'block';
            document.getElementById(
                'ca-minimize-btn').innerHTML =
                minimized ? '&#43;' : '&#8212;';
            widget.style.minWidth =
                minimized ? 'auto' : '180px';
        });

        makeDraggable(widget);
        startTimer();

        // Raporteaza imediat cand utilizatorul
        // paraseste pagina (inchide, refresh, alt tab)
        function reportNow(elapsed) {
            if (elapsed <= 0) return;
            chrome.runtime.sendMessage({
                type:         'update_time_used',
                domain:       domain,
                used_seconds: usedSeconds + elapsed,
            });
        }

        window.addEventListener('beforeunload', () => {
            const elapsed = Math.floor(
                (Date.now() - sessionStart) / 1000);
            reportNow(elapsed);
        });

        // Raporteaza si cand tab-ul devine invizibil
        // (utilizatorul trece pe alt tab)
        document.addEventListener(
                'visibilitychange', () => {
            if (document.hidden) {
                const elapsed = Math.floor(
                    (Date.now() - sessionStart) / 1000);
                reportNow(elapsed);
            }
        });

        function startTimer() {
            timerInterval = setInterval(() => {
                const elapsed = Math.floor(
                    (Date.now() - sessionStart) / 1000);
                remaining = limitSeconds
                            - usedSeconds
                            - elapsed;

                const display = document.getElementById(
                    'ca-timer-display');
                const fill = document.getElementById(
                    'ca-progress-fill');

                if (!display || !fill) {
                    clearInterval(timerInterval);
                    return;
                }

                if (remaining <= 0) {
                    clearInterval(timerInterval);

                    // Raporteaza tot timpul folosit
                    reportNow(elapsed);

                    // Raporteaza la background
                    chrome.runtime.sendMessage({
                        type:   'limit_reached',
                        domain: domain,
                    });

                    // Arata pagina blocata
                    showBlockedPage(true);
                    return;
                }

                display.textContent = formatTime(remaining);
                fill.style.width = pct(remaining, limitSeconds) + '%';

                // Schimba culoarea in functie de timp ramas
                const p = remaining / limitSeconds;
                let color;
                if (p < 0.1) {
                    color = '#E53935'; // rosu
                } else if (p < 0.25) {
                    color = '#FF9800'; // portocaliu
                } else {
                    color = '#F57F17'; // normal
                }
                display.style.color = p < 0.1 ? '#E53935' : 'white';
                widget.style.borderColor = color;
                fill.style.background = color;

                // Sincronizeaza cu background la fiecare 5s
                if (elapsed > 0 && elapsed % 5 === 0) {
                    reportNow(elapsed);
                }
            }, 1000);
        }
    }

    // ── Helpers ──────────────────────────────────

    function pct(remaining, total) {
        return Math.max(0,
            Math.min(100,
                (remaining / total) * 100))
            .toFixed(1);
    }

    function formatTime(seconds) {
        if (seconds <= 0) return '00:00';
        const m = Math.floor(seconds / 60);
        const s = Math.floor(seconds % 60);
        return String(m).padStart(2, '0')
             + ':' + String(s).padStart(2, '0');
    }

    function makeDraggable(el) {
        let ox = 0, oy = 0, mx = 0, my = 0;
        let dragging = false;

        el.addEventListener('mousedown', (e) => {
            if (e.target.id === 'ca-minimize-btn')
                return;
            dragging = true;
            mx = e.clientX;
            my = e.clientY;
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            ox = e.clientX - mx;
            oy = e.clientY - my;
            mx = e.clientX;
            my = e.clientY;
            el.style.bottom = 'auto';
            el.style.right  = 'auto';
            el.style.top  = (el.offsetTop  + oy) + 'px';
            el.style.left = (el.offsetLeft + ox) + 'px';
        });

        document.addEventListener('mouseup', () => {
            dragging = false;
        });
    }

})();