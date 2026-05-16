// Citeste regulile din storage si le aplica
// Rulat periodic din background

async function syncRulesFromFile() {
    // Citeste din chrome.storage
    // (Python scrie acolo prin bridge)
    chrome.storage.local.get(
        ['ca_rules'], (stored) => {

        const rules = stored.ca_rules || {
            blocked: [], limited: {}
        };

        blockedDomains = new Set(
            rules.blocked || []);
        limitedDomains = rules.limited || {};
    });
}