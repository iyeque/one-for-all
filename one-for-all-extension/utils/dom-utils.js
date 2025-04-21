// Shared utility functions for DOM manipulation and element hiding

const defaultHideStyles = {
  display: 'none',
  visibility: 'hidden',
  opacity: '0',
  pointerEvents: 'none',
  height: '0'
};

function hideElement(element, styles = defaultHideStyles) {
  if (element && element.style) {
    Object.assign(element.style, styles);
    element.setAttribute('aria-hidden', 'true');
  }
}

function createDOMObserver(callback, target = document.body || document.documentElement) {
  const observer = new MutationObserver(callback);
  observer.observe(target, {
    childList: true,
    subtree: true
  });
  return observer;
}

function hideElements(selectors, debugInfo = '') {
  try {
    const startTime = performance.now();
    let hiddenCount = 0;

    selectors.forEach(selector => {
      try {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
          try {
            hideElement(element);
            hiddenCount++;
          } catch (elementError) {
            console.debug(`Failed to hide element: ${elementError.message}`);
          }
        });
      } catch (selectorError) {
        console.debug(`Invalid selector ${selector}: ${selectorError.message}`);
      }
    });

    const duration = performance.now() - startTime;
    if (hiddenCount > 0) {
      console.debug(`Hidden ${hiddenCount} ${debugInfo} elements in ${duration.toFixed(2)}ms`);
    }
  } catch (error) {
    console.error(`Element hiding failed: ${error.message}`);
  }
}

export { hideElement, createDOMObserver, hideElements };