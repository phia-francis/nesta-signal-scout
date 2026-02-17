import {
  clusterSignals,
  fetchSavedSignals,
  runRadarScan,
  updateSignalStatus,
  wakeServer,
} from './api.js';
import { state } from './state.js';
import { initialiseTriage } from './triage.js';
import { appendConsoleLog, clearConsole, finishScan, renderSignals, showToast, startScan } from './ui.js';
import { renderNetworkGraph } from './vis.js';

let triageController;

async function refreshDatabase() {
  const databaseGrid = document.getElementById('database-grid');
  const groupByValue = document.getElementById('database-group')?.value || 'none';
  const groupBy = groupByValue === 'none' ? null : groupByValue;
  state.databaseItems = await fetchSavedSignals();
  renderSignals(state.databaseItems, databaseGrid, 'database', groupBy);
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
  const topic = (document.getElementById('topic-input')?.value || '').trim();
  const feed = document.getElementById('radar-feed');

  state.radarSignals = [];
  state.triageQueue = [];
  if (feed) feed.innerHTML = '';
  clearConsole();
  startScan();

  let receivedBlip = false;
  try {
    await runRadarScan({ mission, topic, mode: state.currentMode }, async (message) => {
    appendLog(message.msg || message.status, message.status || 'info');

    if (message.blip) {
      receivedBlip = true;
      state.radarSignals.push(message.blip);
      state.triageQueue.push(message.blip);
      renderSignals(state.radarSignals, feed, topic);
      updateTriageBadge();
    }
  });

    if (!receivedBlip) {
      renderSignals([], feed, topic);
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

function switchView(view) {
  const radarView = document.getElementById('view-radar');
  const databaseView = document.getElementById('view-database');
  const databaseBtn = document.getElementById('nav-database');
  
  if (view === 'database') {
    radarView?.classList.add('hidden');
    databaseView?.classList.remove('hidden');
    databaseBtn?.classList.add('active');
    refreshDatabase();
  } else {
    radarView?.classList.remove('hidden');
    databaseView?.classList.add('hidden');
    databaseBtn?.classList.remove('active');
  }
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

document.addEventListener('DOMContentLoaded', async () => {
  await wakeServer();
  await refreshDatabase();

  triageController = initialiseTriage({
    getQueue: () => state.triageQueue,
    onArchive: async (signal) => {
      await updateSignalStatus(signal.url, 'Archived');
    },
    onKeep: async (signal) => {
      await updateSignalStatus(signal.url, 'New');
    },
    onStar: async (signal) => {
      await updateSignalStatus(signal.url, 'Starred');
    },
  });

  document.querySelectorAll('.mode-toggle').forEach((button) => {
    button.addEventListener('click', () => switchMode(button.dataset.mode));
  });

  document.getElementById('nav-database')?.addEventListener('click', () => switchView('database'));

  document.querySelectorAll('.mode-toggle').forEach((button) => {
    button.addEventListener('click', () => switchView('radar'));
  });

  document.getElementById('scan-btn')?.addEventListener('click', runScan);
  document.getElementById('refresh-db-btn')?.addEventListener('click', refreshDatabase);
  document.getElementById('database-group')?.addEventListener('change', refreshDatabase);
  document.getElementById('btn-view-grid')?.addEventListener('click', () => switchVisualMode('grid'));
  document.getElementById('btn-view-network')?.addEventListener('click', () => switchVisualMode('network'));
  document.getElementById('btn-cluster')?.addEventListener('click', runAutoCluster);
  document.getElementById('btn-triage')?.addEventListener('click', () => triageController?.open());

  switchMode('radar');
  switchVisualMode('grid');
  updateTriageBadge();
});
