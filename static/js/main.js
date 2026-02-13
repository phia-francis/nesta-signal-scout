window.addEventListener('unhandledrejection', (event) => {
  console.warn('Unhandled promise rejection:', event.reason);
  if (
    event.reason &&
    event.reason.message &&
    event.reason.message.includes('message channel closed')
  ) {
    event.preventDefault();
  }
});

import { startTour } from './modules/guide.js';
import { fetchSavedSignals } from './modules/api.js';
import { renderSignals } from './modules/ui.js';
import { state as moduleState } from './modules/state.js';

// DYNAMIC API CONFIGURATION
let API_BASE_URL = window.location.origin;

const hostname = window.location.hostname;

// 1. GitHub Pages -> Point to Render
if (hostname.endsWith('.github.io')) {
  API_BASE_URL = 'https://nesta-signal-backend.onrender.com';
}
// 2. Localhost -> Point to Local Python
else if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
  API_BASE_URL = 'http://localhost:8000';
}
// 3. Render -> Points to itself (window.location.origin) automatically

console.log(`Signal Scout Configured: Running on ${hostname}, talking to ${API_BASE_URL}`);

const state = {
  activeTab: 'radar',
  radarSignals: [],
  databaseItems: [],
  globalSignalsArray: [],
  triageQueue: [],
  currentTriageIndex: 0,
  currentMode: 'radar',
};

const APP_MODE_CONTENT = {
  radar: {
    heading: 'Emerging Signals',
    description: 'Activity vs. Attention from GtR, OpenAlex, and search signals.',
  },
  research: {
    heading: 'Evidence Base',
    description: 'Activity vs. Attention from GtR, OpenAlex, and search signals.',
  },
  policy: {
    heading: 'Policy Shifts',
    description: 'Activity vs. Attention from GtR, OpenAlex, and search signals.',
  },
  database: {
    heading: 'Innovation Sweet Spots',
    description: 'Activity vs. Attention from GtR, OpenAlex, and search signals.',
  },
  default: {
    heading: 'Innovation Sweet Spots',
    description: 'Activity vs. Attention from GtR, OpenAlex, and search signals.',
  },
};

const radarFeed = document.getElementById('radar-feed');
const radarStatus = document.getElementById('radar-status');
const databaseGrid = document.getElementById('database-grid');
const pageTitle = document.getElementById('page-title');
const viewHeading = document.getElementById('view-heading');
const viewDescription = document.getElementById('view-description');

// WAKE UP PROTOCOL
document.addEventListener('DOMContentLoaded', () => {
  // 1. Ping the server immediately to wake it up
  fetch(`${API_BASE_URL}/`)
    .then((res) => console.log('Server Awake:', res.status))
    .catch(() => console.log('Waking up server...'));

  // 2. Load the database
  refreshDatabase();

  const chips = document.querySelectorAll('.filter-chip');
  chips.forEach((chip) => {
    chip.addEventListener('click', () => {
      chips.forEach((btn) => btn.classList.remove('active'));
      chip.classList.add('active');
      const type = chip.getAttribute('data-filter');
      filterGrid(type);
    });
  });

  document.querySelectorAll('.nav-item[data-mode]').forEach((button) => {
    button.addEventListener('click', () => switchAppMode(button.dataset.mode));
  });

  document.getElementById('refresh-db-btn')?.addEventListener('click', refreshDatabase);
  document.getElementById('database-group')?.addEventListener('change', refreshDatabase);
  document.getElementById('help-tour-btn')?.addEventListener('click', startTour);
  document.getElementById('scan-btn')?.addEventListener('click', runScan);
  document.getElementById('btn-view-grid')?.addEventListener('click', () => switchView('grid'));
  document.getElementById('btn-view-network')?.addEventListener('click', () => switchView('network'));
  document.getElementById('btn-cluster')?.addEventListener('click', generateNarratives);
  document.getElementById('btn-triage')?.addEventListener('click', openTriageMode);
  document.getElementById('triage-close')?.addEventListener('click', closeTriage);
  document.querySelectorAll('[data-triage-action]').forEach((button) => {
    button.addEventListener('click', () => triageAction(button.dataset.triageAction));
  });

  switchAppMode('radar');
});

// 1. Mission Theme Configuration (Contrast Safe)
const missionThemes = {
  'A Healthy Life': {
    bg: 'bg-nesta-pink',
    text: 'text-nesta-navy', // AUTO-ALIGN: Pink is light, so text must be dark
    border: 'border-nesta-pink',
  },
  'A Sustainable Future': {
    bg: 'bg-nesta-green',
    text: 'text-white', // AUTO-ALIGN: Green is dark enough for white text
    border: 'border-nesta-green',
  },
  'A Fairer Start': {
    bg: 'bg-nesta-yellow',
    text: 'text-nesta-navy', // AUTO-ALIGN: Yellow is light, so text must be dark
    border: 'border-nesta-yellow',
  },
  General: {
    bg: 'bg-nesta-blue',
    text: 'text-white', // AUTO-ALIGN: Blue is dark, so text is white
    border: 'border-nesta-blue',
  },
};

// HELPER: Generate Sparkline SVG
function generateSparklineElement(dataPoints) {
  if (!dataPoints || dataPoints.length === 0) return null;

  const width = 100;
  const height = 30;
  const maxVal = Math.max(...dataPoints);
  const minVal = Math.min(...dataPoints);
  const range = maxVal - minVal || 1;

  const points = dataPoints
    .map((val, index) => {
      const x = (index / (dataPoints.length - 1 || 1)) * width;
      const y = height - ((val - minVal) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  const [lastX, lastY] = points.split(' ').pop().split(',');

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '30');
  svg.setAttribute('viewBox', '0 0 100 30');
  svg.classList.add('overflow-visible');

  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('points', points);
  polyline.setAttribute('fill', 'none');
  polyline.setAttribute('stroke', '#0000FF');
  polyline.setAttribute('stroke-width', '2');
  polyline.setAttribute('vector-effect', 'non-scaling-stroke');

  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', lastX);
  circle.setAttribute('cy', lastY);
  circle.setAttribute('r', '3');
  circle.setAttribute('fill', '#0000FF');

  svg.append(polyline, circle);
  return svg;
}

// HELPER: Get Tooltip Text for Typology
function getTypologyTooltip(type) {
  const definitions = {
    'Hidden Gem': 'High investment activity but low public attention. A prime innovation opportunity.',
    Hype: 'High public attention but low actual investment/research activity. Use caution.',
    Established: 'High activity and high attention. A mature market.',
    Nascent: 'Low activity and low attention. Early stage or weak signal.',
  };
  return definitions[type] || 'Signal classification based on Activity vs. Attention.';
}

// --- ADVANCED VISUALIZATION: NETWORK GRAPH ---
function renderNetworkGraph(signals) {
  const container = document.getElementById('signal-network');
  if (!container || !window.vis) {
    return;
  }

  const nodes = new window.vis.DataSet(
    signals.map((signal, index) => ({
      id: index,
      label: `${(signal.title || 'Signal').substring(0, 15)}...`,
      title: signal.title || 'Signal',
      value: signal.score_activity || 1,
      group: signal.mission || 'General',
      shape: 'dot',
    }))
  );

  const edgesArray = [];
  for (let i = 0; i < signals.length; i += 1) {
    for (let j = i + 1; j < signals.length; j += 1) {
      if (signals[i].typology === signals[j].typology) {
        edgesArray.push({ from: i, to: j });
      }
    }
  }

  const edges = new window.vis.DataSet(edgesArray);

  const options = {
    nodes: {
      font: { color: '#FFFFFF', face: 'Inter', size: 10 },
      borderWidth: 0,
      shadow: true,
    },
    edges: {
      color: { color: '#0000FF', highlight: '#18A48C' },
      width: 0.5,
      smooth: false,
    },
    groups: {
      'A Sustainable Future': { color: '#18A48C' },
      'A Healthy Life': { color: '#F6A4B7' },
      'A Fairer Start': { color: '#FDB633' },
      General: { color: '#0000FF' },
    },
    physics: {
      stabilization: false,
      barnesHut: { gravitationalConstant: -2000, springConstant: 0.04 },
    },
    interaction: { hover: true, tooltipDelay: 0 },
  };

  window.networkGraph = new window.vis.Network(container, { nodes, edges }, options);

  window.networkGraph.on('click', (params) => {
    if (params.nodes.length > 0) {
      const signalUrl = signals[params.nodes[0]].url;
      if (signalUrl) {
        window.open(signalUrl, '_blank');
      }
    }
  });
}

// --- 1. TOAST SYSTEM ---
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) {
    return;
  }

  const div = document.createElement('div');
  const colors = {
    success: 'bg-nesta-green border-nesta-green text-white',
    error: 'bg-nesta-red border-nesta-red text-white',
    info: 'bg-nesta-navy border-nesta-navy text-white',
  };

  div.className = `pointer-events-auto max-w-sm w-full shadow-hard border-l-8 p-4 flex items-center gap-3 toast-enter ${
    colors[type] || colors.info
  }`;
  const text = document.createElement('div');
  text.className = 'font-bold text-sm tracking-wide';
  text.textContent = message;
  div.appendChild(text);

  container.appendChild(div);

  setTimeout(() => {
    div.classList.remove('toast-enter');
    div.classList.add('toast-exit');
    setTimeout(() => div.remove(), 300);
  }, 4000);
}

// --- 2. UPDATE CARD RENDERER (With Visual Meters) ---
function renderSignalCard(signal, container) {
  const typology = signal.typology || 'Nascent';
  const div = document.createElement('div');
  div.className =
    'signal-card card-enter bg-white p-6 flex flex-col gap-4 relative overflow-hidden group border border-slate-100';
  div.dataset.typology = typology;

  const theme = missionThemes[signal.mission] || missionThemes.General;
  const sparklineElement = generateSparklineElement(signal.sparkline);
  const actPercent = Math.min(100, (signal.score_activity / 10) * 100);
  const attPercent = Math.min(100, (signal.score_attention / 10) * 100);
  const isNew = Boolean(signal.is_novel);
  if (isNew) {
    const badge = document.createElement('div');
    badge.className = 'pulse-badge';
    const dot = document.createElement('div');
    dot.className = 'pulse-dot';
    badge.append(dot, document.createTextNode('NEW'));
    div.appendChild(badge);
  }

  const header = document.createElement('div');
  header.className = 'flex justify-between items-start';

  const missionSpan = document.createElement('span');
  missionSpan.className = `${theme.bg} ${theme.text} text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm shadow-sm`;
  missionSpan.textContent = signal.mission;

  const typologySpan = document.createElement('span');
  typologySpan.className =
    'text-nesta-navy border border-slate-200 text-[10px] font-bold uppercase tracking-widest px-2 py-1 bg-slate-50 hover:bg-nesta-navy hover:text-white transition-colors cursor-help';
  typologySpan.setAttribute('data-tooltip', getTypologyTooltip(typology));
  typologySpan.textContent = `${typology} ?`;

  header.append(missionSpan, typologySpan);

  const title = document.createElement('h3');
  title.className =
    'font-display text-xl font-bold leading-tight text-nesta-navy group-hover:text-nesta-blue transition-colors cursor-pointer';
  title.textContent = signal.title;
  title.addEventListener('click', () => {
    try {
      const parsedUrl = new URL(signal.url, window.location.origin);
      if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
        window.open(parsedUrl.href, '_blank');
      }
    } catch (error) {
      return;
    }
  });

  const summary = document.createElement('p');
  summary.className = 'text-sm text-nesta-dark-grey leading-relaxed line-clamp-3';
  summary.textContent = signal.summary;

  const footer = document.createElement('div');
  footer.className = 'mt-auto pt-4 border-t border-slate-100 grid grid-cols-2 gap-6';

  const metrics = document.createElement('div');
  metrics.className = 'space-y-2';

  const activityGroup = document.createElement('div');
  const activityHeader = document.createElement('div');
  activityHeader.className = 'flex justify-between text-[10px] font-bold text-nesta-navy uppercase';
  activityHeader.setAttribute('data-tooltip', 'Based on UKRI Grant Funding Data');
  const activityLabel = document.createElement('span');
  activityLabel.className = 'border-b border-dotted border-slate-300 cursor-help';
  activityLabel.textContent = 'Activity';
  const activityValue = document.createElement('span');
  activityValue.textContent = signal.score_activity;
  activityHeader.append(activityLabel, activityValue);
  const activityMeter = document.createElement('div');
  activityMeter.className = 'meter-container';
  const activityFill = document.createElement('div');
  activityFill.className = 'meter-fill bg-nesta-blue';
  activityFill.style.width = `${actPercent}%`;
  activityMeter.appendChild(activityFill);
  activityGroup.append(activityHeader, activityMeter);

  const attentionGroup = document.createElement('div');
  const attentionHeader = document.createElement('div');
  attentionHeader.className = 'flex justify-between text-[10px] font-bold text-nesta-navy uppercase';
  attentionHeader.setAttribute('data-tooltip', 'Based on Search Volume & News Frequency');
  const attentionLabel = document.createElement('span');
  attentionLabel.className = 'border-b border-dotted border-slate-300 cursor-help';
  attentionLabel.textContent = 'Attention';
  const attentionValue = document.createElement('span');
  attentionValue.textContent = signal.score_attention;
  attentionHeader.append(attentionLabel, attentionValue);
  const attentionMeter = document.createElement('div');
  attentionMeter.className = 'meter-container';
  const attentionFill = document.createElement('div');
  attentionFill.className = 'meter-fill bg-nesta-pink';
  attentionFill.style.width = `${attPercent}%`;
  attentionMeter.appendChild(attentionFill);
  attentionGroup.append(attentionHeader, attentionMeter);

  metrics.append(activityGroup, attentionGroup);

  const trend = document.createElement('div');
  trend.className = 'flex flex-col justify-end';
  const trendLabel = document.createElement('div');
  trendLabel.className = 'text-[9px] font-bold text-nesta-dark-grey uppercase mb-1 text-right';
  trendLabel.textContent = 'Trend (12mo)';
  const trendChart = document.createElement('div');
  trendChart.className = 'h-[30px] w-full border-l border-b border-slate-200';
  if (sparklineElement) {
    trendChart.appendChild(sparklineElement);
  }
  trend.append(trendLabel, trendChart);

  footer.append(metrics, trend);

  div.append(header, title, summary, footer);

  div.classList.add('border-l-4', theme.border);
  container.prepend(div);

  setTimeout(() => {
    const meters = div.querySelectorAll('.meter-fill');
    meters.forEach((meter) => {
      meter.style.transform = 'scaleX(1)';
    });
  }, 50);
}

function switchAppMode(mode) {
  state.currentMode = mode;
  const modeContent = APP_MODE_CONTENT[mode] || APP_MODE_CONTENT.default;

  document.querySelectorAll('.nav-item').forEach((el) => el.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${mode}`);
  if (activeNav) {
    activeNav.classList.add('active');
  }

  const radarView = document.getElementById('view-radar');
  const databaseView = document.getElementById('view-database');
  const stdInput = document.getElementById('input-standard');
  const resInput = document.getElementById('input-research');
  const scanBtn = document.getElementById('scan-btn');
  const interfaceBox = document.getElementById('search-panel');

  if (mode === 'database') {
    radarView.classList.add('hidden');
    databaseView.classList.remove('hidden');
    pageTitle.textContent = 'Database';
    if (viewHeading) viewHeading.textContent = modeContent.heading;
    if (viewDescription) viewDescription.textContent = modeContent.description;
    refreshDatabase();
    return;
  }

  radarView.classList.remove('hidden');
  databaseView.classList.add('hidden');
  pageTitle.textContent = 'Mission Discovery';
  if (viewHeading) viewHeading.textContent = modeContent.heading;
  if (viewDescription) viewDescription.textContent = modeContent.description;

  const btnText = scanBtn?.querySelector('span');

  if (!stdInput || !resInput || !scanBtn || !interfaceBox || !btnText) {
    return;
  }

  if (mode === 'research') {
    stdInput.classList.add('hidden');
    resInput.classList.remove('hidden');
    scanBtn.className =
      'w-full md:w-auto bg-nesta-purple text-white px-8 py-4 font-display font-bold tracking-wide shadow-hard hover:translate-y-[-2px] transition-all flex items-center justify-center gap-2';
    btnText.innerText = 'RUN DEEP DIVE';
    interfaceBox.classList.add('border-nesta-purple');
  } else {
    stdInput.classList.remove('hidden');
    resInput.classList.add('hidden');
    const color = mode === 'policy' ? 'bg-nesta-yellow text-nesta-navy' : 'bg-nesta-blue text-white';
    scanBtn.className = `w-full md:w-auto ${color} px-8 py-4 font-display font-bold tracking-wide shadow-hard hover:translate-y-[-2px] transition-all flex items-center justify-center gap-2`;
    btnText.innerText = `RUN ${mode.toUpperCase()} SCAN`;
    interfaceBox.classList.remove('border-nesta-purple');
  }
}

function renderDatabaseSkeletons(count = 6) {
  const grid = document.getElementById('database-grid');
  grid.innerHTML = Array(count)
    .fill(0)
    .map(
      () => `
        <div class="bg-white p-6 rounded-2xl border border-slate-100 shadow-sm h-64 flex flex-col gap-4 signal-card">
          <div class="h-6 bg-slate-100 rounded w-3/4 skeleton"></div>
          <div class="h-4 bg-slate-100 rounded w-full skeleton"></div>
          <div class="h-4 bg-slate-100 rounded w-5/6 skeleton"></div>
          <div class="mt-auto h-32 bg-slate-50 rounded skeleton"></div>
        </div>
      `
    )
    .join('');
}

function renderDatabase(items) {
  databaseGrid.innerHTML = '';
  if (!items.length) {
    databaseGrid.innerHTML = '<div class="text-slate-500">Database is empty.</div>';
    return;
  }
  items.forEach((item) => {
    const card = document.createElement('article');
    card.className = 'bg-white p-6 rounded-2xl signal-card';
    card.innerHTML = `
      <h3 class="text-lg font-display text-nesta-navy">${item.title || 'Untitled'}</h3>
      <p class="text-sm text-slate-600 mt-2">${item.summary || 'No summary available.'}</p>
      <div class="mt-4 text-xs text-slate-500 space-y-1">
        <div>Typology: ${item.typology || 'Nascent'}</div>
        <div>Activity: ${item.score_activity ?? 0}</div>
        <div>Attention: ${item.score_attention ?? 0}</div>
      </div>
    `;
    databaseGrid.appendChild(card);
  });
}

async function refreshDatabase() {
  const grid = document.getElementById('database-grid');
  const groupByValue = document.getElementById('database-group')?.value || 'none';
  const groupBy = groupByValue === 'none' ? null : groupByValue;

  if (!grid) return;
  grid.innerHTML = '';
  renderDatabaseSkeletons();

  try {
    moduleState.databaseItems = await fetchSavedSignals();
    state.databaseItems = moduleState.databaseItems;
    state.globalSignalsArray = [...moduleState.databaseItems];
    renderSignals(moduleState.databaseItems, grid, 'database', groupBy);
    renderNetworkGraph(moduleState.databaseItems);
  } catch (e) {
    grid.replaceChildren();
    const wrapper = document.createElement('div');
    wrapper.className = 'py-10 flex flex-col items-center gap-4';

    const iconWrap = document.createElement('div');
    iconWrap.className = 'p-4 bg-red-50 border border-red-100 rounded-full text-red-500';
    iconWrap.innerHTML =
      '<svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';

    const textWrap = document.createElement('div');
    textWrap.className = 'text-center';
    const h3 = document.createElement('h3');
    h3.className = 'font-bold text-nesta-navy';
    h3.textContent = 'Connection Error';
    const p = document.createElement('p');
    p.className = 'text-sm text-slate-500 mt-1';
    p.textContent = e.message;
    textWrap.append(h3, p);

    const retry = document.createElement('button');
    retry.className = 'btn-nesta bg-nesta-navy text-white font-bold px-6 py-2';
    retry.textContent = 'Retry Connection';
    retry.addEventListener('click', refreshDatabase);

    wrapper.append(iconWrap, textWrap, retry);
    grid.appendChild(wrapper);
  }
}

function renderRadarBlip(blip) {
  renderSignalCard(blip, radarFeed);
}

function getConsoleContainer() {
  return document.getElementById('console') || document.getElementById('scan-logs');
}

function addLog(message, type = 'info') {
  const logContainer = getConsoleContainer();
  if (!logContainer) {
    return;
  }
  const entry = document.createElement('div');
  entry.className = `log-entry log-entry-${type}`;
  entry.textContent = message;
  logContainer.appendChild(entry);
  logContainer.scrollTop = logContainer.scrollHeight;
}


function startScan() {
  const loader = document.getElementById('scan-loader');
  loader?.classList.remove('hidden');
  radarFeed.classList.add('hidden');
}

function finishScan() {
  const loader = document.getElementById('scan-loader');
  loader?.classList.add('hidden');
}
async function runScan() {
  const missionSelect = document.getElementById('mission-select');
  const topicInput = document.getElementById('topic-input');
  const researchInput = document.getElementById('research-input');
  const emptyState = document.getElementById('empty-state');
  const resultsContainer = document.getElementById('live-results-grid') || radarFeed;
  const logContainer = getConsoleContainer();
  state.globalSignalsArray = [];

  if (logContainer) {
    logContainer.innerHTML = '';
  }
  startScan();
  if (emptyState) {
    emptyState.classList.add('hidden');
  }

  if (resultsContainer) {
    resultsContainer.innerHTML = '<div class="animate-pulse text-slate-400">Scanning horizon...</div>';
  }
  radarStatus.textContent = 'Starting scan...';

  try {
    const payload = buildScanPayload(missionSelect, topicInput, researchInput);
    if (!payload) {
      return;
    }

    const mode = state.currentMode || 'radar';
    const endpoint = mode === 'research' ? '/api/mode/research' : '/api/mode/radar';
    const query = payload.query || payload.topic || '';

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error('Scan failed');
    }

    const newSignals = await response.json();

    if (newSignals && newSignals.length > 0 && resultsContainer) {
      resultsContainer.innerHTML = '';
      renderSignals(newSignals, resultsContainer, 'live');
      state.globalSignalsArray = newSignals;
      radarStatus.textContent = `Scan complete: ${newSignals.length} signal(s) found.`;
      radarStatus.classList.remove('text-red-500');
    } else if (resultsContainer) {
      resultsContainer.innerHTML = '<div>No signals found.</div>';
      if (emptyState) {
        emptyState.classList.remove('hidden');
      }
    }

    await refreshDatabase();
    renderNetworkGraph(state.globalSignalsArray);
  } catch (error) {
    console.error('Scan Error:', error);
    if (resultsContainer) {
      resultsContainer.innerHTML = `<div class="text-red-500">Error: ${error.message}</div>`;
    }
    radarStatus.textContent = 'Connection failed: Check API Key';
    radarStatus.classList.add('text-red-500');
    addLog('Connection failed: Check API Key', 'error');
    showToast('Connection Failed', 'error');
  } finally {
    finishScan();
  }
}

function buildScanPayload(missionSelect, topicInput, researchInput) {
  const payload = { mode: state.currentMode };
  if (state.currentMode === 'research') {
    const query = researchInput?.value.trim();
    if (!query) {
      showToast('Please enter a research question', 'error');
      return null;
    }
    payload.query = query;
    payload.mission = 'Research';
    return payload;
  }

  const topic = topicInput && topicInput.value.trim() ? topicInput.value.trim() : '';
  if (!topic) {
    showToast('Please enter a topic', 'error');
    return null;
  }
  payload.mission = missionSelect ? missionSelect.value : 'All Missions';
  payload.topic = topic;
  return payload;
}

function handleStreamData(data) {
  if (data.msg) {
    radarStatus.textContent = data.msg;
  }

  if (data.status === 'info') {
    addLog(data.msg, 'info');
    return 0;
  }
  if (data.status === 'success') {
    addLog(data.msg, 'success');
    return 0;
  }
  if (data.status === 'warning') {
    addLog(data.msg, 'warning');
    return 0;
  }
  if (data.status === 'blip') {
    state.globalSignalsArray.push(data.blip);
    renderRadarBlip(data.blip);
    showToast(`Signal Found: ${data.blip.title.substring(0, 20)}...`, 'success');
    return 1;
  }
  if (data.status === 'error') {
    addLog(data.msg, 'error');
    radarStatus.textContent = data.msg || 'Connection failed';
    radarStatus.classList.add('text-red-500');
    showToast('Error during scan', 'error');
    return 0;
  }
  if (data.status === 'complete') {
    addLog('Scan Complete.', 'success');
    const triageBtn = document.getElementById('btn-triage');
    const countBadge = document.getElementById('new-signal-count');
    const clusterBtn = document.getElementById('btn-cluster');
    if (triageBtn && countBadge) {
      triageBtn.classList.remove('hidden');
      countBadge.innerText = state.globalSignalsArray.length;
    }
    if (clusterBtn) {
      clusterBtn.classList.remove('hidden');
    }
    showToast(`Scan finished. ${state.globalSignalsArray.length} signals ready for review.`, 'success');
  }
  return 0;
}

function switchView(mode) {
  const grid = document.getElementById('radar-feed');
  const net = document.getElementById('view-network-container');
  const btnGrid = document.getElementById('btn-view-grid');
  const btnNet = document.getElementById('btn-view-network');

  if (!grid || !net || !btnGrid || !btnNet) {
    return;
  }

  if (mode === 'grid') {
    grid.classList.remove('hidden');
    net.classList.add('hidden');

    btnGrid.classList.add('bg-white', 'shadow-sm', 'text-nesta-navy');
    btnGrid.classList.remove('text-slate-500');
    btnNet.classList.remove('bg-white', 'shadow-sm', 'text-nesta-navy');
    btnNet.classList.add('text-slate-500');
  } else {
    grid.classList.add('hidden');
    net.classList.remove('hidden');

    if (window.networkGraph) window.networkGraph.fit();

    btnNet.classList.add('bg-white', 'shadow-sm', 'text-nesta-navy');
    btnNet.classList.remove('text-slate-500');
    btnGrid.classList.remove('bg-white', 'shadow-sm', 'text-nesta-navy');
    btnGrid.classList.add('text-slate-500');
  }
}

async function generateNarratives() {
  const btn = document.getElementById('btn-cluster');
  const drawer = document.getElementById('narrative-drawer');
  const container = document.getElementById('narrative-container');

  if (!btn || !drawer || !container) {
    return;
  }

  if (!drawer.classList.contains('hidden')) {
    drawer.classList.add('hidden');
    return;
  }

  btn.innerHTML = `<span class="animate-spin">↻</span> Thinking...`;

  try {
    const res = await fetch(`${API_BASE_URL}/api/intelligence/cluster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.globalSignalsArray),
    });
    const clusters = await res.json();

    container.replaceChildren();
    const clusterList = Array.isArray(clusters) ? clusters : [];
    clusterList.forEach((cluster) => {
      const card = document.createElement('div');
      card.className =
        'bg-white p-4 border-l-4 border-nesta-purple shadow-sm hover:shadow-md transition-all cursor-pointer group';

      const meta = document.createElement('div');
      meta.className = 'text-[9px] font-bold uppercase text-slate-400 mb-1';
      meta.textContent = `${cluster.count} Signals • ${cluster.keywords.join(', ')}`;

      const title = document.createElement('h4');
      title.className = 'font-display text-md text-nesta-navy font-bold leading-tight group-hover:text-nesta-purple';
      title.textContent = cluster.title;

      card.append(meta, title);
      container.appendChild(card);
    });

    drawer.classList.remove('hidden');
    btn.innerHTML = `<span>✨ Auto-Cluster</span>`;
  } catch (e) {
    showToast(`Cluster Engine Failed: ${e.message}`, 'error');
    btn.innerHTML = `<span>⚠ Error</span>`;
  }
}

function filterGrid(type) {
  const cards = document.querySelectorAll('.signal-card');
  let delay = 0;

  cards.forEach((card) => {
    const cardType = (card.dataset.typology || '').trim();

    card.style.animation = 'none';
    card.offsetHeight;
    card.style.animation = null;

    if (type === 'all' || cardType.toUpperCase() === type.toUpperCase()) {
      card.classList.remove('hidden');
      card.style.animation = `fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards ${delay}s`;
      delay += 0.05;
    } else {
      card.classList.add('hidden');
    }
  });
}

function openTriageMode() {
  if (!state.globalSignalsArray.length) {
    showToast('No signals to triage.', 'error');
    return;
  }

  state.triageQueue = [...state.globalSignalsArray];
  state.currentTriageIndex = 0;

  document.getElementById('triage-modal').classList.remove('hidden');
  renderTriageCard();
  document.addEventListener('keydown', handleTriageKeys);
}

function closeTriage() {
  document.getElementById('triage-modal').classList.add('hidden');
  document.removeEventListener('keydown', handleTriageKeys);
}

function renderTriageCard() {
  if (state.currentTriageIndex >= state.triageQueue.length) {
    closeTriage();
    showToast('Triage Complete!', 'success');
    return;
  }

  const signal = state.triageQueue[state.currentTriageIndex];
  const container = document.getElementById('triage-card-container');
  const theme = missionThemes[signal.mission] || missionThemes.General;

  const pct = (state.currentTriageIndex / state.triageQueue.length) * 100;
  document.getElementById('triage-progress').style.width = `${pct}%`;

  const card = document.createElement('div');
  card.className = `bg-white p-10 shadow-2xl border-t-8 ${theme.border} relative animate-slide-in`;

  const badge = document.createElement('span');
  badge.className = `${theme.bg} ${theme.text} text-xs font-bold uppercase tracking-widest px-3 py-1 mb-4 inline-block rounded-sm`;
  badge.textContent = signal.mission;

  const title = document.createElement('h1');
  title.className = 'font-display text-4xl font-bold text-nesta-navy mb-6 leading-tight';
  title.textContent = signal.title;

  const summary = document.createElement('p');
  summary.className = 'font-body text-lg text-nesta-dark-grey leading-relaxed mb-8';
  summary.textContent = signal.summary;

  const grid = document.createElement('div');
  grid.className = 'grid grid-cols-2 gap-4 border-t border-slate-100 pt-6';

  const activity = document.createElement('div');
  activity.className = 'text-center';
  const activityLabel = document.createElement('div');
  activityLabel.className = 'text-xs uppercase font-bold text-slate-400';
  activityLabel.textContent = 'Activity Score';
  const activityValue = document.createElement('div');
  activityValue.className = 'text-3xl font-display font-bold text-nesta-blue';
  activityValue.textContent = signal.score_activity;
  activity.append(activityLabel, activityValue);

  const attention = document.createElement('div');
  attention.className = 'text-center';
  const attentionLabel = document.createElement('div');
  attentionLabel.className = 'text-xs uppercase font-bold text-slate-400';
  attentionLabel.textContent = 'Attention Score';
  const attentionValue = document.createElement('div');
  attentionValue.className = 'text-3xl font-display font-bold text-nesta-pink';
  attentionValue.textContent = signal.score_attention;
  attention.append(attentionLabel, attentionValue);

  grid.append(activity, attention);
  card.append(badge, title, summary, grid);
  container.replaceChildren(card);
}

function handleTriageKeys(event) {
  if (event.key === 'a' || event.key === 'A') triageAction('archive');
  if (event.key === 's' || event.key === 'S') triageAction('star');
  if (event.key === 'ArrowRight') triageAction('keep');
  if (event.key === 'Escape') closeTriage();
}

function triageAction(action) {
  const signal = state.triageQueue[state.currentTriageIndex];
  if (!signal) {
    return;
  }

  const cardElement = document.getElementById('triage-card-container').firstElementChild;
  if (!cardElement) {
    return;
  }

  if (action === 'archive') {
    cardElement.style.transform = 'translateX(-100px) rotate(-5deg)';
    cardElement.style.opacity = '0';
    showToast('Archived', 'info');
  } else if (action === 'star') {
    cardElement.style.transform = 'translateY(-50px) scale(1.05)';
    cardElement.style.opacity = '0';
    showToast('Starred for Briefing', 'success');
  } else {
    cardElement.style.transform = 'translateX(100px) rotate(5deg)';
    cardElement.style.opacity = '0';
  }

  setTimeout(() => {
    state.currentTriageIndex += 1;
    renderTriageCard();
  }, 200);
}
