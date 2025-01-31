
const blockedDomains = [
  "ads.example.com",
  "tracking.example.com",
  "analytics.example.com"
];

chrome.webRequest.onBeforeRequest.addListener(
  function(details) {
    const url = new URL(details.url);
    if (blockedDomains.includes(url.hostname)) {
      console.log(`Blocked request to: ${url.hostname}`);
      return { cancel: true };
    }
  },
  { urls: ["<all_urls>"] },
  ["blocking"]
);
