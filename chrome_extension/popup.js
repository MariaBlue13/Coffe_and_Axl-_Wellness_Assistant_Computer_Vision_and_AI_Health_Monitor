let rules   = { blocked: [], limited: {} };
let authData = null;

document.addEventListener('DOMContentLoaded', init);

function init() {
    chrome.storage.local.get(
        ['ca_auth', 'ca_rules'],
        (result) => {
        // FIX: seteaza regulile INAINTE de showMain
        // altfel renderRules() ruleaza cu rules gol
        if (result.ca_rules) {
            rules = result.ca_rules;
        }
        if (result.ca_auth &&
                result.ca_auth.token) {
            authData = result.ca_auth;
            showMain();
            loadRulesFromPython();
        } else {
            showLogin();
        }
    });

    document.getElementById('btn-login')
        .addEventListener('click', doLogin);
    document.getElementById('login-password')
        .addEventListener('keydown', (e) => {
        if (e.key === 'Enter') doLogin();
    });

    document.getElementById('btn-block')
        .addEventListener('click', () =>
            addRule('blocat'));
    document.getElementById('btn-limit')
        .addEventListener('click', () =>
            addRule('limitat'));
    document.getElementById('btn-logout')
        .addEventListener('click', doLogout);
    document.getElementById('domain-input')
        .addEventListener('keydown', (e) => {
        if (e.key === 'Enter')
            addRule('blocat');
    });
}

// -- Login --

function doLogin() {
    const username = document.getElementById(
        'login-username').value.trim();
    const password = document.getElementById(
        'login-password').value;

    if (!username || !password) {
        setLoginStatus(
            'Completeaza toate campurile.',
            'red');
        return;
    }

    setLoginStatus('Se autentifica...', '');

    chrome.runtime.sendMessage({
        type:     'auth_request',
        username: username,
        password: password,
        ts:       Date.now(),
    }, (response) => {
        if (chrome.runtime.lastError) {
            setLoginStatus(
                'Eroare comunicare.', 'red');
            return;
        }
        handleAuthResponse(response);
    });
}

function handleAuthResponse(resp) {
    if (!resp) {
        setLoginStatus(
            'Niciun raspuns.', 'red');
        return;
    }
    if (resp.success) {
        authData = {
            token:   resp.token,
            user_id: resp.user_id,
            role:    resp.role,
            display: resp.display,
        };
        const toStore = { ca_auth: authData };
        if (resp.rules) {
            rules = resp.rules;
            toStore.ca_rules = resp.rules;
        }
        chrome.storage.local.set(toStore, () => {
            showMain();
            loadRulesFromPython();
        });
    } else {
        setLoginStatus(
            'Eroare: ' + resp.message, 'red');
    }
}

function doLogout() {
    chrome.storage.local.remove(
        ['ca_auth', 'ca_rules'], () => {
        authData = null;
        rules    = { blocked: [], limited: {} };
        showLogin();
    });
}

// -- UI --

function showLogin() {
    document.getElementById(
        'login-section').style.display = 'block';
    document.getElementById(
        'main-section').style.display  = 'none';
}

function showMain() {
    document.getElementById(
        'login-section').style.display = 'none';
    document.getElementById(
        'main-section').style.display  = 'block';

    const info = document.getElementById(
        'user-info');
    if (authData) {
        info.textContent =
            'Conectat: ' + (authData.display || '-')
            + ' [' + (authData.role || '') + ']';
    }
    renderRules();
}

function setLoginStatus(msg, color) {
    const el = document.getElementById(
        'login-status');
    el.textContent = msg;
    el.className   = 'status' +
        (color === 'red' ? ' error' : '');
}

// -- Reguli --

function addRule(tip) {
    const input  = document.getElementById(
        'domain-input');
    const domain = input.value.trim()
        .toLowerCase()
        .replace('www.', '')
        .replace(/https?:\/\//g, '')
        .split('/')[0];

    if (!domain) {
        setMainStatus(
            'Introdu un domeniu!', 'red');
        return;
    }

    if (tip === 'blocat') {
        if (!rules.blocked.includes(domain)) {
            rules.blocked.push(domain);
        }
        delete rules.limited[domain];
    } else {
        const minutes = parseInt(
            document.getElementById(
                'limit-input').value) || 30;
        rules.limited[domain] = minutes;
        rules.blocked = rules.blocked.filter(
            d => d !== domain);
    }

    input.value = '';
    saveRules();
    setMainStatus(domain + ' adaugat!', 'green');
}

function deleteRule(domain, tip) {
    if (tip === 'blocat') {
        rules.blocked = rules.blocked.filter(
            d => d !== domain);
    } else {
        delete rules.limited[domain];
    }
    saveRules();
}

function saveRules() {
    chrome.storage.local.set(
        { ca_rules: rules }, () => {
        chrome.runtime.sendMessage({
            type:    'rules_updated',
            rules:   rules,
            user_id: authData?.user_id,
        });
        renderRules();
    });

    // Salveaza regulile si in baza de date Python
    if (authData && authData.token) {
        fetch('http://localhost:7842/rules', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token:   authData.token,
                blocked: rules.blocked,
                limited: rules.limited,
            }),
        })
        .then(r => r.json())
        .then(resp => {
            if (resp.success) {
                console.log('[CA] Reguli salvate in DB.');
            } else {
                console.warn('[CA] Eroare salvare reguli:', resp.message);
            }
        })
        .catch(err => {
            console.warn('[CA] Server offline:', err.message);
        });
    }
}

function loadRulesFromPython() {
    if (!authData || !authData.user_id) return;

    fetch('http://localhost:7842/rules/' + authData.user_id)
        .then(r => r.json())
        .then(data => {
            rules = data;
            chrome.storage.local.set(
                { ca_rules: data });
            chrome.runtime.sendMessage({
                type:  'rules_updated',
                rules: data,
            });
            renderRules();
        })
        .catch(() => {
            chrome.storage.local.get(
                ['ca_rules'], (result) => {
                if (result.ca_rules) {
                    rules = result.ca_rules;
                    renderRules();
                }
            });
        });
}

function renderRules() {
    const list = document.getElementById(
        'rules-list');

    const total = rules.blocked.length +
        Object.keys(rules.limited).length;

    if (total === 0) {
        list.innerHTML =
            '<div style="color:#666;'
            + 'font-size:11px;padding:4px 0">'
            + 'Nicio regula adaugata.</div>';
        return;
    }

    let html = '';

    for (const d of rules.blocked) {
        html += '<div class="rule-item rule-blocked">'
            + '<span>Blocat: ' + d + '</span>'
            + '<button class="delete-btn"'
            + ' data-domain="' + d + '"'
            + ' data-tip="blocat">X</button>'
            + '</div>';
    }

    for (const [d, m] of
            Object.entries(rules.limited)) {
        html += '<div class="rule-item rule-limited">'
            + '<span>Limitat: ' + d + ' (' + m + 'min/zi)</span>'
            + '<button class="delete-btn"'
            + ' data-domain="' + d + '"'
            + ' data-tip="limitat">X</button>'
            + '</div>';
    }

    list.innerHTML = html;
    list.querySelectorAll('.delete-btn')
        .forEach(btn => {
        btn.addEventListener('click', () => {
            deleteRule(
                btn.dataset.domain,
                btn.dataset.tip);
        });
    });
}

function setMainStatus(msg, color) {
    const el = document.getElementById(
        'main-status');
    const colors = {
        green:  '#4CAF50',
        red:    '#E53935',
        orange: '#F57F17',
    };
    el.textContent = msg;
    el.style.color = colors[color] || '#4CAF50';
    setTimeout(() => {
        el.textContent = 'Monitor activ';
        el.style.color = '#4CAF50';
    }, 2000);
}