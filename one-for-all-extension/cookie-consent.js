
const cookieConsentSelectors = [
  // Common cookie consent banners
  ".cc-banner", ".cookie-consent", ".cookie-notice", ".gdpr-banner",
  "#cookie-banner", "#cookie-consent", "#cookie-notice", "#gdpr-banner",
  // Additional common patterns
  "[class*='cookie-banner']", "[id*='cookie-banner']",
  "[class*='cookie-popup']", "[id*='cookie-popup']",
  "[class*='gdpr-consent']", "[id*='gdpr-consent']",
  // Common cookie policy notices
  ".cookie-policy", "#cookie-policy",
  // Data specific attributes
  "[data-cookie-notice]", "[data-gdpr-banner]",
  "[aria-label*='cookie']", "[aria-label*='gdpr']"
];

import { hideElements, createDOMObserver } from './utils/dom-utils.js';

function hideCookieConsent() {
  hideElements(cookieConsentSelectors, 'cookie consent');
}

const observer = createDOMObserver(hideCookieConsent);

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", hideCookieConsent);
} else {
  hideCookieConsent();
}
