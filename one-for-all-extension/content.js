(function() {
  const adSelectors = [
    '.ad-container', '.adsbygoogle', '[id^="ad-"]', '[class^="ad-"]',
    '.sponsored-post', '.promoted-content', '.advertisement', '.layout-slot-header'
  ];
  
  const clean = () => {
    if (typeof hideElements === 'function') hideElements(adSelectors);
  };

  clean();
  const observer = new MutationObserver(clean);
  observer.observe(document.body, { childList: true, subtree: true });
  console.log('One for All: Content Shield Active');
})();