
const adBlockingRules = [
  {
    id: 1,
    priority: 1,
    action: { type: 'block' },
    condition: {
      urlFilter: '||*ads*',
      resourceTypes: ['script', 'image', 'xmlhttprequest', 'sub_frame']
    }
  },
  {
    id: 2,
    priority: 1,
    action: { type: 'block' },
    condition: {
      urlFilter: '||*analytics*',
      resourceTypes: ['script', 'xmlhttprequest']
    }
  },
  {
    id: 3,
    priority: 1,
    action: { type: 'block' },
    condition: {
      urlFilter: '||*tracker*',
      resourceTypes: ['script', 'xmlhttprequest']
    }
  },
  {
    id: 4,
    priority: 1,
    action: { type: 'block' },
    condition: {
      urlFilter: '||*advert*',
      resourceTypes: ['script', 'image', 'xmlhttprequest', 'sub_frame']
    }
  },
  {
    id: 5,
    priority: 1,
    action: { type: 'block' },
    condition: {
      urlFilter: '||*banner*',
      resourceTypes: ['script', 'image', 'xmlhttprequest', 'sub_frame']
    }
  }
];

// Initialize the declarativeNetRequest rules
async function initializeAdBlocking() {
  try {
    // Clear any existing rules
    const existingRules = await chrome.declarativeNetRequest.getDynamicRules();
    const existingRuleIds = existingRules.map(rule => rule.id);
    
    // Update with new rules
    await chrome.declarativeNetRequest.updateDynamicRules({
      removeRuleIds: existingRuleIds,
      addRules: adBlockingRules
    });
    
    console.log('Ad blocking rules initialized successfully');
  } catch (error) {
    console.error('Failed to initialize ad blocking rules:', error);
  }
}

// Listen for installation/update events
chrome.runtime.onInstalled.addListener(initializeAdBlocking);

// Initialize rules when the service worker starts
initializeAdBlocking();
