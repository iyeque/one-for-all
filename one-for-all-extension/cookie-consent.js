(function() {
  const cookieSelectors = [
    '[id*="cookie-consent"]', '[class*="cookie-banner"]',
    '.qc-cmp2-container', '#onetrust-consent-sdk',
    '.trustarc-banner-container', '#didomi-popup', '.cookie-notice'
  ];
  
  const clean = () => {
    if (typeof hideElements === 'function') hideElements(cookieSelectors);
  };

  clean();
  const observer = new MutationObserver(clean);
  observer.observe(document.body, { childList: true, subtree: true });
  console.log('One for All: Cookie Shield Active');
})();