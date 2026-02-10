import { fetchSavedSignals, runRadarScan, wakeServer } from './api.js';
import { state } from './state.js';
import { renderSignals, showToast } from './ui.js';

async function refreshDatabase() {
  const databaseGrid = document.getElementById('database-grid');
  state.databaseItems = await fetchSavedSignals();
  renderSignals(state.databaseItems, databaseGrid);
}

async function runScan() {
  const mission = document.getElementById('mission-select')?.value || 'A Sustainable Future';
  const topic = document.getElementById('topic-input')?.value || 'innovation';
  const feed = document.getElementById('radar-feed');
  const logs = document.getElementById('scan-logs');
  state.radarSignals = [];
  feed.innerHTML = '';
  logs.innerHTML = '';

  await runRadarScan({ mission, topic, mode: state.currentMode }, (message) => {
    const line = document.createElement('div');
    line.className = 'text-xs text-white/80';
    line.textContent = message.msg || message.status;
    logs.appendChild(line);

    if (message.blip) {
      state.radarSignals.push(message.blip);
      renderSignals(state.radarSignals, feed);
    }
  });

  showToast('Scan complete');
}

function switchMode(mode) {
  state.currentMode = mode;
  document.querySelectorAll('.nav-item[data-mode]').forEach((button) => {
    button.classList.toggle('active', button.dataset.mode === mode);
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  await wakeServer();
  await refreshDatabase();

  document.querySelectorAll('.nav-item[data-mode]').forEach((button) => {
    button.addEventListener('click', () => switchMode(button.dataset.mode));
  });
  document.getElementById('scan-btn')?.addEventListener('click', runScan);
  document.getElementById('refresh-db-btn')?.addEventListener('click', refreshDatabase);
  switchMode('radar');
});
