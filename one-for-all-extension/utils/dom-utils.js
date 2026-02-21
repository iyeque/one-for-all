export function hideElements(selectors) {
  selectors.forEach(s => {
    document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; });
  });
}