(function() {
  'use strict';
  // Shims for tracking scripts
  window.ga = window.ga || function() { (window.ga.q = window.ga.q || []).push(arguments); };
  window.gtag = window.gtag || function() { (window.dataLayer = window.dataLayer || []).push(arguments); };
  window.fbq = window.fbq || function() { (window.fbq.q = window.fbq.q || []).push(arguments); };
  
  // Fingerprint Jittering
  const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
  HTMLCanvasElement.prototype.toDataURL = function() {
    const ctx = this.getContext('2d');
    if (ctx) {
      const imgData = ctx.getImageData(0, 0, this.width, this.height);
      imgData.data[3] = imgData.data[3] + (Math.random() > 0.5 ? 1 : -1);
      ctx.putImageData(imgData, 0, 0);
    }
    return originalToDataURL.apply(this, arguments);
  };
  Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
})();