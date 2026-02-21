(function() {
  'use strict';
  const shims = {
    ga: function() { console.log('One for All: Shimmed GA'); },
    gtag: function() { console.log('One for All: Shimmed GTAG'); },
    fbq: function() { console.log('One for All: Shimmed FBQ'); }
  };
  const jitter = () => (Math.random() - 0.5) * 0.0001;
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
  const script = document.createElement('script');
  script.textContent = `window.ga=${shims.ga.toString()};window.gtag=${shims.gtag.toString()};window.fbq=${shims.fbq.toString()};`;
  (document.head || document.documentElement).appendChild(script);
  script.remove();
})();