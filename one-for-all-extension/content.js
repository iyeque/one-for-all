
const adSelectors = [
  // Generic ad selectors
  "div[id*='ad-']", "div[id*='ads-']", "div[class*='ad-']", "div[class*='ads-']",
  "iframe[src*='ad']", "iframe[src*='ads']", "iframe[id*='ad']", "iframe[id*='ads']",
  "img[src*='ad']", "img[src*='ads']", "img[id*='ad']", "img[id*='ads']",
  ".ad", ".ads", ".advertisement", ".advert", ".sponsored",
  "#ad", "#ads", "#advertisement", "#advert",
  // Banner and sponsored content
  "[class*='banner']", "[id*='banner']",
  "[class*='sponsor']", "[id*='sponsor']",
  // Additional common ad patterns
  "[class*='adsbox']", "[id*='adsbox']",
  "[class*='adunit']", "[id*='adunit']",
  "[data-ad]", "[data-ads]", "[data-adunit]"
];

import { hideElements, createDOMObserver } from './utils/dom-utils.js';

function hideAds() {
  hideElements(adSelectors, 'ad');
}

const observer = createDOMObserver(hideAds);

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", hideAds);
} else {
  hideAds();
}
