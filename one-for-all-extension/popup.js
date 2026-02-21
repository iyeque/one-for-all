document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('openSettings');
  if (btn) {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      chrome.runtime.openOptionsPage();
    });
  }
});