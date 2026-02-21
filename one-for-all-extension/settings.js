document.addEventListener('DOMContentLoaded', () => {
  const stats = document.getElementById('stats');
  chrome.runtime.sendMessage({ action: 'checkStatus' }, (response) => {
    if (response && response.status === 'online') {
      stats.textContent = 'AdGuard Home is Connected and Filtering.';
      stats.style.color = 'green';
    } else {
      stats.textContent = 'AdGuard Home is not responding. Check the Control Panel.';
      stats.style.color = 'red';
    }
  });
});