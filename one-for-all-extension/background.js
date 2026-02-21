const adBlockingRules = [
  { id: 1, priority: 1, action: { type: 'block' }, condition: { urlFilter: '*ads*', excludedDomains: ['youtube.com', 'google.com', 'googlevideo.com'], resourceTypes: ['script', 'image', 'xmlhttprequest', 'sub_frame'] } },
  { id: 6, priority: 2, action: { type: 'modifyHeaders', requestHeaders: [{ header: 'referer', operation: 'remove' }, { header: 'x-client-data', operation: 'remove' }] }, condition: { urlFilter: '*', domainType: 'thirdParty', excludedDomains: ['youtube.com', 'google.com', 'googlevideo.com', 'ytimg.com', 'ggpht.com'] } },
  { id: 7, priority: 2, action: { type: 'modifyHeaders', requestHeaders: [{ header: 'user-agent', operation: 'set', value: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' }] }, condition: { urlFilter: '*' } }
];

async function init() {
  const existing = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: existing.map(r => r.id), addRules: adBlockingRules });
}
chrome.runtime.onInstalled.addListener(init);
init();

// Handle status checks from settings page (Bypasses CORS)
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === 'checkStatus') {
    const ports = ['3000', '80'];
    const checkPort = (index) => {
      if (index >= ports.length) {
        sendResponse({ status: 'offline' });
        return;
      }
      fetch(`http://localhost:${ports[index]}/`, { mode: 'no-cors', cache: 'no-store' })
        .then(() => sendResponse({ status: 'online' }))
        .catch(() => checkPort(index + 1));
    };
    checkPort(0);
    return true; 
  }
});

function setWebRTC(isEnabled) {
  if (chrome.privacy && chrome.privacy.network) {
    chrome.privacy.network.webRTCIPHandlingPolicy.set({ value: isEnabled ? 'disable_non_proxied_udp' : 'default' });
  }
}
chrome.storage.sync.get("isEnabled", (r) => setWebRTC(r.isEnabled !== false));