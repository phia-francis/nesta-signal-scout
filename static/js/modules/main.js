import {
  clusterSignals,
  fetchSavedSignals,
  triggerScan,
  updateSignalStatus,
  wakeServer,
} from './api.js';
import { state } from './state.js';
import { initialiseTriage } from './triage.js';
import { appendConsoleLog, clearConsole, finishScan, renderClusterInsights, renderResearchResult, renderSignals, showToast, startScan } from './ui.js';
import { renderNetworkGraph } from './vis.js';

let triageController;

async function refreshDatabase() {
  try {
    const databaseGrid = document.getElementById('database-grid');
    const groupByValue = document.getElementById('database-group')?.value || 'none';
    const groupBy = groupByValue === 'none' ? null : groupByValue;
    state.databaseItems = await fetchSavedSignals();
    renderSignals(state.databaseItems, databaseGrid, 'database', groupBy);
  } catch (error) {
    console.error("Failed to load database:", error);
  }
}

function toggleDatabaseModal(show) {
  const modal = document.getElementById('db-modal');
  const overlay = document.getElementById('db-overlay');
  modal?.classList.toggle('open', show);
  overlay?.classList.toggle('open', show);
  if (show) refreshDatabase();
}

function toggleHelpModal(show) {
  const modal = document.getElementById('help-modal');
  const overlay = document.getElementById('help-overlay');
  modal?.classList.toggle('open', show);
  overlay?.classList.toggle('open', show);
}

function appendLog(message, type = 'info') {
  appendConsoleLog(message, type);
}

function updateTriageBadge() {
  const count = document.getElementById('new-signal-count');
  const triageButton = document.getElementById('btn-triage');
  if (count) {
    count.textContent = String(state.triageQueue.length);
  }
  if (triageButton) {
    triageButton.classList.toggle('hidden', state.triageQueue.length === 0);
  }
}

async function runScan() {
  const mission = document.getElementById('mission-select')?.value || 'A Sustainable Future';
  const topic = (document.getElementById('query-input')?.value || '').trim();
  const feed = document.getElementById('radar-feed');

  state.radarSignals = [];
  state.triageQueue = [];
  updateTriageBadge();
  if (feed) feed.innerHTML = '';
  clearConsole();
  startScan();

  try {
    const data = await triggerScan(topic, mission, state.currentMode);

    if (state.currentMode === 'deep_dive' || state.currentMode === 'research') {
      if (feed) {
        renderResearchResult(data, feed);
      }
      if (data && data.signals) {
        state.radarSignals = data.signals;
        state.triageQueue = data.signals.slice();
        updateTriageBadge();
      }
    } else if (data && data.signals) {
      state.radarSignals = data.signals;
      state.triageQueue = data.signals.slice();
      updateTriageBadge();
      if (feed) {
        feed.innerHTML = '';

        if (!data.signals || data.signals.length === 0) {
            feed.innerHTML = `
                <div class="flex flex-col items-center justify-center p-12 text-center bg-nesta-sand/10 rounded-lg border border-nesta-sand border-dashed">
                    <h3 class="text-xl font-bold text-nesta-navy mb-2">No Novel Trends Found</h3>
                    <p class="text-nesta-navy/70 max-w-md">
                        The agent scanned the web but discarded all sources because they were either
                        outdated (older than 1 year), irrelevant, or lacked strong evidence.
                        <br><br>Try a broader search query or a different mode.
                    </p>
                    <p class="text-xs text-nesta-navy/50 mt-4">
                        Searches attempted: ${data.related_terms ? data.related_terms.join(', ') : 'None'}
                    </p>
                </div>
            `;
        } else {
            if (data.cluster_insights) {
              renderClusterInsights(data.cluster_insights, feed);
            }
            renderSignals(state.radarSignals, feed, topic);
        }
      }
    }

    showToast('Scan complete', 'success');
  } catch (error) {
    appendLog('Connection Failed', 'error');
    showToast('Connection Failed', 'error');
  } finally {
    finishScan();
  }
}

function switchMode(mode) {
  state.currentMode = mode;
  document.querySelectorAll('.mode-toggle').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
}

function switchVisualMode(mode) {
  const networkContainer = document.getElementById('view-network-container');
  const gridButton = document.getElementById('btn-view-grid');
  const networkButton = document.getElementById('btn-view-network');

  if (!networkContainer) return;

  if (mode === 'network') {
    networkContainer.classList.remove('hidden');
    renderNetworkGraph(state.radarSignals);
  } else {
    networkContainer.classList.add('hidden');
  }

  gridButton?.classList.toggle('bg-white', mode === 'grid');
  networkButton?.classList.toggle('bg-white', mode === 'network');
}

async function runAutoCluster() {
  if (!state.radarSignals.length) {
    showToast('No signals available to cluster yet.', 'info');
    return;
  }
  const narratives = await clusterSignals(state.radarSignals);
  const drawer = document.getElementById('narrative-drawer');
  const container = document.getElementById('narrative-container');
  if (!drawer || !container) return;

  drawer.classList.remove('hidden');
  container.innerHTML = narratives
    .map(
      (narrative) =>
        `<article class="bg-white border border-slate-200 p-4"><h4 class="font-bold text-sm text-nesta-navy">${narrative.title}</h4><p class="text-xs text-slate-600 mt-2">${narrative.count} signals</p></article>`
    )
    .join('');
}

document.addEventListener('DOMContentLoaded', () => {

  // 1. Attach all event listeners synchronously — nothing awaited here
  triageController = initialiseTriage({
    getQueue: () => state.triageQueue,
    onArchive: async (signal) => updateSignalStatus(signal.url, 'Archived'),
    onKeep: async (signal) => updateSignalStatus(signal.url, 'New'),
    onStar: async (signal) => updateSignalStatus(signal.url, 'Starred'),
  });

  document.querySelectorAll('.mode-toggle').forEach((button) => {
    button.addEventListener('click', () => switchMode(button.dataset.mode));
  });

  // 3. Database modal
  document.getElementById('open-db-btn')?.addEventListener('click', () => toggleDatabaseModal(true));
  document.getElementById('close-db-btn')?.addEventListener('click', () => toggleDatabaseModal(false));
  document.getElementById('db-overlay')?.addEventListener('click', () => toggleDatabaseModal(false));
  document.getElementById('refresh-db-btn')?.addEventListener('click', refreshDatabase);
  document.getElementById('database-group')?.addEventListener('change', refreshDatabase);

  // 4. Help modal
  document.getElementById('help-btn')?.addEventListener('click', () => toggleHelpModal(true));
  document.getElementById('close-help-btn')?.addEventListener('click', () => toggleHelpModal(false));
  document.getElementById('close-help-btn-top')?.addEventListener('click', () => toggleHelpModal(false));
  document.getElementById('help-overlay')?.addEventListener('click', () => toggleHelpModal(false));

  // 5. Actions
  document.getElementById('scan-btn')?.addEventListener('click', runScan);
  document.getElementById('btn-view-grid')?.addEventListener('click', () => switchVisualMode('grid'));
  document.getElementById('btn-view-network')?.addEventListener('click', () => switchVisualMode('network'));
  document.getElementById('btn-generate-analysis')?.addEventListener('click', runAutoCluster);
  document.getElementById('btn-regroup-clusters')?.addEventListener('click', runAutoCluster);
  document.getElementById('btn-triage')?.addEventListener('click', () => triageController?.open());

  switchMode('radar');
  switchVisualMode('grid');
  updateTriageBadge();

  // 2. Fire network calls in a non-blocking IIFE — a failure here
  //    cannot prevent the listeners above from working.
  //    Note: refreshDatabase handles its own errors internally;
  //    the outer catch covers wakeServer failures.
  (async () => {
    try {
      await wakeServer();
      await refreshDatabase();
    } catch (err) {
      console.warn('Background initialisation warning:', err);
      const message = err && err.message ? err.message : 'Unknown error';
      showToast(`Initialisation issue: ${message}`, 'error');
    }
  })();
});
