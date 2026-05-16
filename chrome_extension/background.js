let blockedDomains = new Set();
let limitedDomains = {};
let currentUserId  = null;
let currentToken   = null;
let timeUsed = {};

// Returneaza data de azi ca string YYYY-MM-DD
function today() {
    return new Date().toISOString().slice(0, 10);
}

// Reseteaza timeUsed daca a trecut ziua
function checkDayReset(storedDate) {
    if (storedDate !== today()) {
        console.log('[CA] Zi noua — resetez timeUsed');
        timeUsed = {};
        chrome.storage.local.set({
            ca_time_used: {},
            ca_time_date: today(),
        });
    }
}

// Reincarca starea la fiecare pornire
// (service worker-ul se poate opri/reporni)
function restoreState() {
    chrome.storage.local.get(
        ['ca_auth', 'ca_rules',
         'ca_time_used', 'ca_time_date'],
        (result) => {
        if (result.ca_auth) {
            currentUserId =
                result.ca_auth.user_id;
            currentToken =
                result.ca_auth.token;
            console.log('[CA] Stare restaurata '
                      + 'pentru user:',
                        currentUserId);
        }
        if (result.ca_rules) {
            applyRules(result.ca_rules);
            console.log('[CA] Reguli restaurate:',
                [...blockedDomains]);
        }

        // Verifica daca e o zi noua — daca da, reseteaza
        const storedDate = result.ca_time_date || '';
        checkDayReset(storedDate);

        // Incarca timeUsed doar daca e aceeasi zi
        if (result.ca_time_used &&
                storedDate === today()) {
            timeUsed = result.ca_time_used;
            console.log('[CA] timeUsed restaurat:',
                Object.keys(timeUsed).length,
                'domenii');
        }

        // Dupa restaurare, fetch reguli fresh
        // de la server daca e autentificat
        if (currentUserId && currentToken) {
            fetch(`http://localhost:7842/rules/${currentUserId}`)
                .then(r => r.json())
                .then(data => {
                    applyRules(data);
                    chrome.storage.local.set({
                        ca_rules: data });
                    console.log('[CA] Reguli '
                        + 'fresh de la server:',
                        data.blocked?.length || 0,
                        'blocate,',
                        Object.keys(
                            data.limited || {})
                            .length,
                        'limitate');
                })
                .catch(() => {
                    console.log('[CA] Server '
                        + 'offline — folosesc '
                        + 'regulile din storage');
                });
        }
    });
}

// Apeleaza la fiecare pornire service worker
restoreState();

// Keepalive — previne oprirea service worker
// prin un alarm periodic
chrome.alarms.create('keepalive', {
    periodInMinutes: 0.4
});

// Alarm de reset la miezul noptii
chrome.alarms.create('midnight_reset', {
    when: nextMidnight(),
    periodInMinutes: 24 * 60,
});

function nextMidnight() {
    const now = new Date();
    const midnight = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate() + 1, // maine
        0, 0, 0, 0
    );
    return midnight.getTime();
}

chrome.alarms.onAlarm.addListener((alarm) => {
    if (alarm.name === 'keepalive') {
        // Verifica si reaplica regulile
        chrome.storage.local.get(
            ['ca_rules', 'ca_time_date'], (result) => {
            if (result.ca_rules) {
                applyRules(result.ca_rules);
            }
            // Verifica si reseteaza daca e o zi noua
            checkDayReset(result.ca_time_date || '');
        });
    }

    if (alarm.name === 'midnight_reset') {
        console.log('[CA] Miezul noptii — resetez limitele');
        timeUsed = {};
        chrome.storage.local.set({
            ca_time_used: {},
            ca_time_date: today(),
        });
    }
});

// Asculta schimbari storage
chrome.storage.onChanged.addListener(
    (changes, area) => {
    if (area !== 'local') return;

    if (changes.ca_rules) {
        applyRules(
            changes.ca_rules.newValue || {});
    }
    if (changes.ca_auth) {
        const auth = changes.ca_auth.newValue;
        if (auth) {
            currentUserId = auth.user_id;
            currentToken  = auth.token;
        }
    }
    // Proceseaza cerere auth de la popup
    if (changes.ca_auth_request) {
        const req =
            changes.ca_auth_request.newValue;
        if (req) writeAuthRequest(req);
    }
});

function applyRules(rules) {
    blockedDomains = new Set(
        rules.blocked || []);
    limitedDomains = rules.limited || {};
    console.log('[CA] Reguli aplicate:',
                [...blockedDomains]);
}

// Detecteaza navigare
chrome.webNavigation.onCompleted.addListener(
    (details) => {
    if (details.frameId !== 0) return;

    chrome.tabs.get(details.tabId, (tab) => {
        if (!tab || !tab.url) return;
        handleNavigation(
            details.tabId, tab.url, tab.title);
    });
}, { url: [{ schemes: ['http', 'https'] }] });

chrome.tabs.onActivated.addListener(
    (info) => {
    chrome.tabs.get(info.tabId, (tab) => {
        if (!tab || !tab.url) return;
        handleNavigation(
            info.tabId, tab.url, tab.title);
    });
});

function handleNavigation(tabId, url, title) {
    const domain = extractDomain(url);
    if (!domain) return;

    const status = checkDomain(domain);
    console.log('[CA]', domain, '->', status);

    if (status === 'blocked' ||
            status === 'limit_exceeded') {
        // Inchide tab
        chrome.tabs.remove(tabId);
        // Raporteaza evenimentul
        reportEvent('blocked', domain,
                    url, title, status);
    } else {
        reportEvent('visit', domain,
                    url, title, 'ok');
    }
}

// FIX BUG 3: verifica si limita de timp a fost depasita
function checkDomain(domain) {
    for (const b of blockedDomains) {
        if (domain === b ||
                domain.endsWith('.' + b)) {
            return 'blocked';
        }
    }
    for (const [d, m] of
            Object.entries(limitedDomains)) {
        if (domain === d ||
                domain.endsWith('.' + d)) {
            // Verifica daca limita a fost depasita
            const usedSeconds = timeUsed[domain] || 0;
            const limitSeconds = m * 60;
            if (usedSeconds >= limitSeconds) {
                return 'limit_exceeded';
            }
            return 'limited';
        }
    }
    return 'ok';
}

function extractDomain(url) {
    try {
        return new URL(url).hostname
            .replace('www.', '');
    } catch { return ''; }
}

function reportEvent(action, domain,
                      url, title, reason) {
    if (!currentUserId || !currentToken) {
        console.log('[CA] Skip event — '
                  + 'nu e autentificat');
        return;
    }

    const event = {
        action:  action,
        domain:  domain,
        url:     url,
        title:   title,
        reason:  reason,
        user_id: currentUserId,
        token:   currentToken,
        ts:      Date.now(),
    };

    // Salveaza local pentru UI
    chrome.storage.local.get(
        ['ca_activity_log'], (result) => {
        const log = result.ca_activity_log || [];
        log.unshift({
            action, domain, title,
            ts: Date.now()
        });
        // Pastreaza ultimele 50
        chrome.storage.local.set({
            ca_activity_log: log.slice(0, 50),
            ca_current_site: action === 'visit'
                ? domain : '',
        });
    });

    // Trimite la Python
    fetch('http://localhost:7842/event', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(event),
    })
    .then(r => r.json())
    .then(resp => {
        console.log('[CA] Event OK:',
                    action, domain);
    })
    .catch(err => {
        console.warn('[CA] Event err '
                   + '(server offline?):',
                   err.message);
        // Evenimentul e salvat local oricum
    });
}

function writeAuthRequest(req) {
    // Scrie in storage pentru Python
    chrome.storage.local.set({
        ca_auth_pending: req,
    });
    console.log('[CA] Auth request:',
                req.username);
}

setInterval(() => {
    if (!currentUserId || !currentToken) return;

    // Polling reguli
    fetch(`http://localhost:7842/rules/${currentUserId}`)
        .then(r => r.json())
        .then(data => {
            if (data.blocked || data.limited) {
                applyRules(data);
                chrome.storage.local.set({
                    ca_rules: data });
                console.log('[CA] Reguli OK:',
                    data.blocked?.length || 0,
                    'blocate');
            }
        })
        .catch(() => {
            // Server offline — folosim
            // regulile din storage
            chrome.storage.local.get(
                ['ca_rules'], (result) => {
                if (result.ca_rules) {
                    applyRules(result.ca_rules);
                }
            });
        });

    // Actualizeaza snapshot local
    chrome.storage.local.set({
        ca_time_snapshot: {
            timeUsed: timeUsed,
            ts: Date.now(),
        }
    });

    // Trimite bulk sync la Python — toate domeniile
    if (Object.keys(timeUsed).length > 0) {
        fetch('http://localhost:7842/time_sync', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token:       currentToken,
                all_domains: timeUsed,
            }),
        }).catch(() => {
            // Server offline — ignoram silentios
        });
    }
}, 5000);

// FIX BUG 2: toate handler-ele sunt INAUNTRUL addListener
chrome.runtime.onMessage.addListener(
    (msg, sender, sendResponse) => {

    if (msg.type === 'auth_request') {
        handleAuthRequest(
            msg.username,
            msg.password,
            sendResponse);
        return true; // async response
    }

    if (msg.type === 'rules_updated') {
        applyRules(msg.rules);
    }

    // FIX: get_site_status era in afara listener-ului
    if (msg.type === 'get_site_status') {
        const domain = msg.domain;
        let status   = 'ok';
        let limitMin = 0;
        let usedSec  = 0;

        for (const b of blockedDomains) {
            if (domain === b ||
                    domain.endsWith('.' + b)) {
                status = 'blocked';
                break;
            }
        }

        if (status === 'ok') {
            for (const [d, m] of
                    Object.entries(limitedDomains)) {
                if (domain === d ||
                        domain.endsWith('.' + d)) {
                    status    = 'limited';
                    limitMin  = m;
                    usedSec   = timeUsed[domain] || 0;
                    // Verifica daca limita e depasita
                    if (usedSec >= limitMin * 60) {
                        status = 'limit_exceeded';
                    }
                    break;
                }
            }
        }

        sendResponse({
            status:        status,
            limit_minutes: limitMin,
            used_seconds:  usedSec,
        });
        return true;
    }

    // FIX: update_time_used era in afara listener-ului
    if (msg.type === 'update_time_used') {
        // Actualizeaza doar daca valoarea e mai mare
        const prev = timeUsed[msg.domain] || 0;
        if (msg.used_seconds > prev) {
            timeUsed[msg.domain] = msg.used_seconds;
            chrome.storage.local.set({
                ca_time_used: timeUsed,
                ca_time_date: today(),
            });
            console.log('[CA] timeUsed actualizat:',
                msg.domain, '->', msg.used_seconds, 's');

            // Sincronizeaza cu Python imediat
            if (currentUserId && currentToken) {
                fetch('http://localhost:7842/time_used', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        token:        currentToken,
                        domain:       msg.domain,
                        used_seconds: msg.used_seconds,
                    }),
                }).catch(() => {
                    // Server offline — ignoram, se va sincroniza
                    // la urmatorul poll de reguli
                });
            }
        }
        return true;
    }

    // FIX: limit_reached era in afara listener-ului
    if (msg.type === 'limit_reached') {
        // Inchide tab-ul curent
        chrome.tabs.query(
            {active: true, currentWindow: true},
            (tabs) => {
            if (tabs[0]) {
                chrome.tabs.remove(tabs[0].id);
                reportEvent(
                    'blocked',
                    msg.domain, '', '',
                    'limit_exceeded');
            }
        });
        return true;
    }
});

function handleAuthRequest(username,
                             password,
                             sendResponse) {
    fetch('http://localhost:7842/auth', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: username,
            password: password,
        }),
    })
    .then(r => r.json())
    .then(data => {
        sendResponse(data);
    })
    .catch(err => {
        sendResponse({
            success: false,
            message: 'Aplicația Coffee & Axl '
                   + 'nu rulează sau nu răspunde. '
                   + 'Verifică că aplicația '
                   + 'este deschisă.',
        });
    });
}