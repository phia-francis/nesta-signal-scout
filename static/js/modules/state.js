const hostname = window.location.hostname;

function resolveApiBaseUrl() {
  if (hostname.endsWith('.github.io')) {
    return 'https://nesta-signal-backend.onrender.com';
  }
  return window.location.origin;
}

export const state = {
  apiBaseUrl: resolveApiBaseUrl(),
  currentMode: 'radar',
  radarSignals: [],
  globalSignalsArray: [],
  currentScanId: null,
  databaseItems: [],
  triageQueue: [],
};

function getShareUrl() {
  if (!state.currentScanId) {
    import('./ui.js').then(({ showToast }) => showToast('No scan to share yet', 'warning'));
    return null;
  }
  return `${window.location.origin}${window.location.pathname}?scan=${state.currentScanId}`;
}

export async function shareCurrentScan() {
  const shareUrl = getShareUrl();
  if (!shareUrl) return;

  try {
    await navigator.clipboard.writeText(shareUrl);
    import('./ui.js').then(({ showToast }) => showToast('Share link copied to clipboard!', 'success'));
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    import('./ui.js').then(({ showToast }) => showToast('Failed to copy link', 'error'));
  }
}

export async function loadScan(scanId) {
  try {
    console.log(`Loading scan ${scanId}...`);
    const { showEnhancedToast } = await import('./ui.js');
    showEnhancedToast('Loading saved scan...', 'info');

    const response = await fetch(`${state.apiBaseUrl}/scan/${scanId}`);

    if (response.status === 404) {
      throw new Error('This scan link has expired or does not exist.');
    }

    if (!response.ok) {
      throw new Error('Failed to load the requested scan.');
    }

    const scanData = await response.json();

    state.currentScanId = scanId;
    state.globalSignalsArray = scanData.signals || [];
    state.radarSignals = scanData.signals || [];

    const queryInput = document.getElementById('query-input');
    if (queryInput) {
      queryInput.value = scanData.query || '';
    }

    const radarFeed = document.getElementById('radar-feed');
    if (radarFeed) {
      radarFeed.innerHTML = '';
      const uiModule = await import('./ui.js');
      scanData.signals.forEach((signal, index) => {
        const card = uiModule.createSignalCard(signal, index);
        radarFeed.appendChild(card);
      });
    }

    if (scanData.themes && scanData.themes.length > 0) {
      const container = document.getElementById('theme-chips-container');
      if (container) {
        const uiModule = await import('./ui.js');
        uiModule.renderThemeChips(scanData.themes, container, () => {});
      }
    }

    document.getElementById('empty-state')?.classList.add('hidden');
    showEnhancedToast(`Loaded scan: ${scanData.query}`, 'success');

  } catch (error) {
    console.error('Failed to load scan:', error);
    const { showEnhancedToast } = await import('./ui.js');
    showEnhancedToast(error.message, 'error');

    const newUrl = new URL(window.location.href);
    newUrl.searchParams.delete('scan');
    window.history.replaceState({}, '', newUrl.toString());

    document.getElementById('empty-state')?.classList.remove('hidden');
    const feed = document.getElementById('radar-feed');
    if (feed) feed.innerHTML = '';
  }
}
