const API_BASE_URL = window.location.origin;

const state = {
  activeTab: 'radar',
  radarSignals: [],
  databaseItems: [],
};

const radarFeed = document.getElementById('radar-feed');
const radarStatus = document.getElementById('radar-status');
const databaseGrid = document.getElementById('database-grid');
const pageTitle = document.getElementById('page-title');

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

// 2. Render Function
function renderSignalCard(signal, container) {
  const div = document.createElement('div');
  div.className = 'signal-card bg-white p-6 flex flex-col gap-3 relative overflow-hidden group';

  // Get Theme
  const theme = missionThemes[signal.mission] || missionThemes.General;

  div.innerHTML = `
        <div class="flex justify-between items-start">
            <span class="${theme.bg} ${theme.text} text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm shadow-sm">
                ${signal.mission}
            </span>
            
            <span class="text-nesta-navy border border-slate-200 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm">
                ${signal.typology}
            </span>
        </div>
        
        <h3 class="font-display text-xl font-bold leading-tight text-nesta-navy group-hover:text-nesta-blue transition-colors mt-2 cursor-pointer" onclick="window.open('${signal.url}', '_blank')">
            ${signal.title}
        </h3>
        
        <p class="text-sm text-nesta-dark-grey leading-relaxed line-clamp-3">
            ${signal.summary}
        </p>

        <div class="mt-auto pt-4 border-t border-slate-100 flex justify-between items-center text-xs font-bold text-nesta-navy opacity-60">
            <span title="Funding Activity">Act: ${signal.score_activity}</span>
            <span title="News Attention">Att: ${signal.score_attention}</span>
        </div>
    `;

  // Add the coloured border
  div.classList.add('border-l-4', theme.border);

  container.prepend(div);
}

function setActiveNav(tab) {
  const navRadar = document.getElementById('nav-radar');
  const navDb = document.getElementById('nav-db');
  navRadar.classList.toggle('nav-button--active', tab === 'radar');
  navDb.classList.toggle('nav-button--active', tab === 'database');
}

function setTab(tab) {
  state.activeTab = tab;
  document.getElementById('view-radar').classList.toggle('hidden', tab !== 'radar');
  document.getElementById('view-database').classList.toggle('hidden', tab !== 'database');
  setActiveNav(tab);
  pageTitle.textContent = tab === 'radar' ? 'Mission Radar' : 'Database';
  if (tab === 'database') {
    refreshDatabase();
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
    renderDatabase(state.databaseItems);
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

async function runRadar() {
  radarFeed.innerHTML = '';
  radarStatus.textContent = 'Starting scan...';
  try {
    const response = await fetch(`${API_BASE_URL}/api/mode/radar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mission: 'All Missions', topic: null }),
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
        if (data.status === 'error') {
          radarStatus.textContent = data.msg || 'Connection failed';
          radarStatus.classList.add('text-red-500');
        }
        if (data.blip) {
          renderRadarBlip(data.blip);
        }
      }
    }
  } catch (error) {
    radarStatus.textContent = 'Connection failed: Check API Key';
    radarStatus.classList.add('text-red-500');
  }
}

document.getElementById('radar-rescan').addEventListener('click', runRadar);

window.setTab = setTab;
window.refreshDatabase = refreshDatabase;

setTab('radar');
runRadar();
