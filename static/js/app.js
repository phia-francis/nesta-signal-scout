// DYNAMIC API CONFIGURATION
let API_BASE_URL = window.location.origin;

const hostname = window.location.hostname;

// 1. GitHub Pages -> Point to Render
if (hostname.includes('github.io')) {
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
};

let globalSignalsArray = [];
let triageQueue = [];
let currentTriageIndex = 0;
let currentMode = 'radar';

const radarFeed = document.getElementById('radar-feed');
const radarStatus = document.getElementById('radar-status');
const databaseGrid = document.getElementById('database-grid');
const pageTitle = document.getElementById('page-title');

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
function generateSparklineSVG(dataPoints) {
  if (!dataPoints || dataPoints.length === 0) return '';

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

  return `
        <svg width="100%" height="30" viewBox="0 0 100 30" class="overflow-visible">
            <polyline points="${points}" fill="none" stroke="#0000FF" stroke-width="2" vector-effect="non-scaling-stroke" />
            <circle cx="${lastX}" cy="${lastY}" r="3" fill="#0000FF" />
        </svg>
    `;
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
  div.innerHTML = `
    <div class="font-bold text-sm tracking-wide">${message}</div>
  `;

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
  const sparklineHTML = generateSparklineSVG(signal.sparkline || [10, 40, 30, 70, 50, 90, 80]);
  const actPercent = Math.min(100, (signal.score_activity / 10) * 100);
  const attPercent = Math.min(100, (signal.score_attention / 10) * 100);
  const isNew = true;
  const pulseHTML = isNew
    ? `
    <div class="pulse-badge">
      <div class="pulse-dot"></div>
      NEW
    </div>
  `
    : '';

  div.innerHTML = `
    ${pulseHTML}
    <div class="flex justify-between items-start">
        <span class="${theme.bg} ${theme.text} text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm shadow-sm">
            ${signal.mission}
        </span>
        <span
            data-tooltip="${getTypologyTooltip(typology)}"
            class="text-nesta-navy border border-slate-200 text-[10px] font-bold uppercase tracking-widest px-2 py-1 bg-slate-50 hover:bg-nesta-navy hover:text-white transition-colors cursor-help">
            ${typology} ?
        </span>
    </div>

    <h3 class="font-display text-xl font-bold leading-tight text-nesta-navy group-hover:text-nesta-blue transition-colors cursor-pointer" onclick="window.open('${signal.url}', '_blank')">
        ${signal.title}
    </h3>

    <p class="text-sm text-nesta-dark-grey leading-relaxed line-clamp-3">
        ${signal.summary}
    </p>

    <div class="mt-auto pt-4 border-t border-slate-100 grid grid-cols-2 gap-6">

        <div class="space-y-2">
            <div>
                <div class="flex justify-between text-[10px] font-bold text-nesta-navy uppercase" data-tooltip="Based on UKRI Grant Funding Data">
                    <span class="border-b border-dotted border-slate-300 cursor-help">Activity</span>
                    <span>${signal.score_activity}</span>
                </div>
                <div class="meter-container"><div class="meter-fill bg-nesta-blue" style="width: ${actPercent}%"></div></div>
            </div>
            <div>
                <div class="flex justify-between text-[10px] font-bold text-nesta-navy uppercase" data-tooltip="Based on Search Volume & News Frequency">
                    <span class="border-b border-dotted border-slate-300 cursor-help">Attention</span>
                    <span>${signal.score_attention}</span>
                </div>
                <div class="meter-container"><div class="meter-fill bg-nesta-pink" style="width: ${attPercent}%"></div></div>
            </div>
        </div>

        <div class="flex flex-col justify-end">
            <div class="text-[9px] font-bold text-nesta-dark-grey uppercase mb-1 text-right">Trend (12mo)</div>
            <div class="h-[30px] w-full border-l border-b border-slate-200">
                ${sparklineHTML}
            </div>
        </div>

    </div>
  `;

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
  currentMode = mode;
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
  const interfaceBox = document.getElementById('search-interface');

  if (mode === 'database') {
    radarView.classList.add('hidden');
    databaseView.classList.remove('hidden');
    pageTitle.textContent = 'Database';
    refreshDatabase();
    showToast('Switched to Database View', 'info');
    return;
  }

  radarView.classList.remove('hidden');
  databaseView.classList.add('hidden');
  pageTitle.textContent = 'Mission Radar';
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
    showToast('Mode: Research (Complex Query Enabled)', 'info');
  } else {
    stdInput.classList.remove('hidden');
    resInput.classList.add('hidden');
    const color = mode === 'policy' ? 'bg-nesta-yellow text-nesta-navy' : 'bg-nesta-blue text-white';
    scanBtn.className = `w-full md:w-auto ${color} px-8 py-4 font-display font-bold tracking-wide shadow-hard hover:translate-y-[-2px] transition-all flex items-center justify-center gap-2`;
    btnText.innerText = `RUN ${mode.toUpperCase()} SCAN`;
    interfaceBox.classList.remove('border-nesta-purple');
    showToast(`Mode: ${mode.toUpperCase()} Active`, 'info');
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
  grid.innerHTML = '';
  renderDatabaseSkeletons();

  try {
    const res = await fetch(`${API_BASE_URL}/api/saved`);
    if (res.status !== 200) {
      const err = await res.json();
      throw new Error(err.detail || 'Database connection failed');
    }
    const data = await res.json();
    state.databaseItems = data.signals || [];
    globalSignalsArray = [...state.databaseItems];
    renderDatabase(state.databaseItems);
    renderNetworkGraph(state.databaseItems);
  } catch (e) {
    grid.innerHTML = `
      <div class="py-10 flex flex-col items-center gap-4">
        <div class="p-4 bg-red-50 border border-red-100 rounded-full text-red-500">
          <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>
        </div>
        <div class="text-center">
          <h3 class="font-bold text-nesta-navy">Connection Error</h3>
          <p class="text-sm text-slate-500 mt-1">${e.message}</p>
        </div>
        <button onclick="refreshDatabase()" class="btn-nesta bg-nesta-navy text-white font-bold px-6 py-2">Retry Connection</button>
      </div>`;
  }
}

function renderRadarBlip(blip) {
  renderSignalCard(blip, radarFeed);
}

function addLog(message, type = 'info') {
  const logContainer = document.getElementById('scan-logs');
  if (!logContainer) {
    return;
  }
  const entry = document.createElement('div');
  entry.className = `log-${type}`;
  entry.textContent = message;
  logContainer.appendChild(entry);
  logContainer.scrollTop = logContainer.scrollHeight;
}

async function runScan() {
  const missionSelect = document.getElementById('mission-select');
  const topicInput = document.getElementById('topic-input');
  const researchInput = document.getElementById('research-input');
  const emptyState = document.getElementById('empty-state');
  const logContainer = document.getElementById('scan-logs');
  let blipCount = 0;
  globalSignalsArray = [];

  if (logContainer) {
    logContainer.innerHTML = '';
  }
  if (emptyState) {
    emptyState.classList.add('hidden');
  }

  radarFeed.innerHTML = '';
  radarStatus.textContent = 'Starting scan...';
  try {
    const payload = { mode: currentMode };
    if (currentMode === 'research') {
      const query = researchInput?.value.trim();
      if (!query) {
        showToast('Please enter a research question', 'error');
        return;
      }
      payload.query = query;
      payload.mission = 'Research';
    } else {
      const topic = topicInput && topicInput.value.trim() ? topicInput.value.trim() : '';
      if (!topic) {
        showToast('Please enter a topic', 'error');
        return;
      }
      payload.mission = missionSelect ? missionSelect.value : 'All Missions';
      payload.topic = topic;
    }

    const response = await fetch(`${API_BASE_URL}/api/mode/radar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        const data = JSON.parse(line);
        if (data.msg) {
          radarStatus.textContent = data.msg;
        }

        if (data.status === 'info') {
          addLog(data.msg, 'info');
        } else if (data.status === 'success') {
          addLog(data.msg, 'success');
        } else if (data.status === 'warning') {
          addLog(data.msg, 'warning');
        } else if (data.status === 'blip') {
          globalSignalsArray.push(data.blip);
          renderRadarBlip(data.blip);
          blipCount += 1;
          showToast(`Signal Found: ${data.blip.title.substring(0, 20)}...`, 'success');
        } else if (data.status === 'error') {
          addLog(data.msg, 'error');
          radarStatus.textContent = data.msg || 'Connection failed';
          radarStatus.classList.add('text-red-500');
          showToast('Error during scan', 'error');
        } else if (data.status === 'complete') {
          addLog('Scan Complete.', 'success');
          const triageBtn = document.getElementById('btn-triage');
          const countBadge = document.getElementById('new-signal-count');
          const clusterBtn = document.getElementById('btn-cluster');

          if (triageBtn && countBadge) {
            triageBtn.classList.remove('hidden');
            countBadge.innerText = globalSignalsArray.length;
          }
          if (clusterBtn) {
            clusterBtn.classList.remove('hidden');
          }

          showToast(`Scan finished. ${globalSignalsArray.length} signals ready for review.`, 'success');
        }
      }
    }
    if (blipCount === 0 && emptyState) {
      emptyState.classList.remove('hidden');
    }
    renderNetworkGraph(globalSignalsArray);
  } catch (error) {
    radarStatus.textContent = 'Connection failed: Check API Key';
    radarStatus.classList.add('text-red-500');
    addLog('Connection failed: Check API Key', 'error');
    showToast('Error during scan', 'error');
  }
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
      body: JSON.stringify(globalSignalsArray),
    });
    const clusters = await res.json();

    container.innerHTML = clusters
      .map(
        (cluster) => `
            <div class="bg-white p-4 border-l-4 border-nesta-purple shadow-sm hover:shadow-md transition-all cursor-pointer group">
                <div class="text-[9px] font-bold uppercase text-slate-400 mb-1">
                    ${cluster.count} Signals • ${cluster.keywords.join(', ')}
                </div>
                <h4 class="font-display text-md text-nesta-navy font-bold leading-tight group-hover:text-nesta-purple">
                    ${cluster.title}
                </h4>
            </div>
        `
      )
      .join('');

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
  if (!globalSignalsArray.length) {
    showToast('No signals to triage.', 'error');
    return;
  }

  triageQueue = [...globalSignalsArray];
  currentTriageIndex = 0;

  document.getElementById('triage-modal').classList.remove('hidden');
  renderTriageCard();
  document.addEventListener('keydown', handleTriageKeys);
}

function closeTriage() {
  document.getElementById('triage-modal').classList.add('hidden');
  document.removeEventListener('keydown', handleTriageKeys);
}

function renderTriageCard() {
  if (currentTriageIndex >= triageQueue.length) {
    closeTriage();
    showToast('Triage Complete!', 'success');
    return;
  }

  const signal = triageQueue[currentTriageIndex];
  const container = document.getElementById('triage-card-container');
  const theme = missionThemes[signal.mission] || missionThemes.General;

  const pct = (currentTriageIndex / triageQueue.length) * 100;
  document.getElementById('triage-progress').style.width = `${pct}%`;

  container.innerHTML = `
      <div class="bg-white p-10 shadow-2xl border-t-8 ${theme.border} relative animate-slide-in">
          <span class="${theme.bg} ${theme.text} text-xs font-bold uppercase tracking-widest px-3 py-1 mb-4 inline-block rounded-sm">
              ${signal.mission}
          </span>
          <h1 class="font-display text-4xl font-bold text-nesta-navy mb-6 leading-tight">
              ${signal.title}
          </h1>
          <p class="font-body text-lg text-nesta-dark-grey leading-relaxed mb-8">
              ${signal.summary}
          </p>
          <div class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-6">
              <div class="text-center">
                  <div class="text-xs uppercase font-bold text-slate-400">Activity Score</div>
                  <div class="text-3xl font-display font-bold text-nesta-blue">${signal.score_activity}</div>
              </div>
              <div class="text-center">
                  <div class="text-xs uppercase font-bold text-slate-400">Attention Score</div>
                  <div class="text-3xl font-display font-bold text-nesta-pink">${signal.score_attention}</div>
              </div>
          </div>
      </div>
  `;
}

function handleTriageKeys(event) {
  if (event.key === 'a' || event.key === 'A') triageAction('archive');
  if (event.key === 's' || event.key === 'S') triageAction('star');
  if (event.key === 'ArrowRight') triageAction('keep');
  if (event.key === 'Escape') closeTriage();
}

function triageAction(action) {
  const signal = triageQueue[currentTriageIndex];
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
    currentTriageIndex += 1;
    renderTriageCard();
  }, 200);
}

window.refreshDatabase = refreshDatabase;
window.runScan = runScan;
window.switchView = switchView;
window.generateNarratives = generateNarratives;
window.openTriageMode = openTriageMode;
window.closeTriage = closeTriage;
window.triageAction = triageAction;

window.switchAppMode = switchAppMode;

switchAppMode('radar');
