
const adSelectors = [
  "div[id*='ad-']",
  "iframe[src*='ads']",
  "img[src*='ads']",
  ".ad",
  "#ad",
  ".advertisement"
];

function hideAds() {
  adSelectors.forEach(selector => {
    const ads = document.querySelectorAll(selector);
    ads.forEach(ad => {
      ad.style.display = "none";
      console.log(`Hidden ad element: ${selector}`);
    });
  });
}

document.addEventListener("DOMContentLoaded", hideAds);
setInterval(hideAds, 2000);
