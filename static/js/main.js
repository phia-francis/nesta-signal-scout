"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// 1. Dynamic API Configuration (CRITICAL for GitHub Pages)
// ─────────────────────────────────────────────────────────────────────────────
let API_BASE_URL = window.location.origin;
const hostname = window.location.hostname;

// URLs for different environments
const RENDER_BACKEND_URL = 'https://nesta-signal-backend.onrender.com';
const LOCAL_BACKEND_URL = 'http://localhost:8000';

if (hostname.endsWith('.github.io')) {
  API_BASE_URL = RENDER_BACKEND_URL;
} else if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
  API_BASE_URL = LOCAL_BACKEND_URL;
}
console.log(`[Scout] API configured: ${API_BASE_URL}`);

// ─────────────────────────────────────────────────────────────────────────────
// 2. State & DOM
// ─────────────────────────────────────────────────────────────────────────────
const state = {
  currentMode: "radar",
  globalSignalsArray: [],
  currentScanId: null,  // Track current scan ID for persistence
};

const dom = {
  radarFeed: document.getElementById("radar-feed"),
  emptyState: document.getElementById("empty-state"),
  scanStatus: document.getElementById("scan-status"),
  queryInput: document.getElementById("query-input"),
  researchInput: document.getElementById("research-input"),
  missionSelect: document.getElementById("mission-select"),
  scanLoader: document.getElementById("scan-loader"),
  toastContainer: document.getElementById("toast-container"),
};

// ─────────────────────────────────────────────────────────────────────────────
// 3. Navigation & Mode Switching
// ─────────────────────────────────────────────────────────────────────────────
const MODE_CONFIG = {
  radar: {
    desc: '<strong>Quick Scan:</strong> Fast web sweep for surface-level signals.',
    btnText: 'RUN QUICK SCAN',
    btnClass: 'bg-nesta-blue',
    borderClass: 'border-nesta-blue',
    themeClass: 'theme-navy',
    placeholder: "Enter an emerging topic (e.g., 'Biotech in Agriculture')"
  },
  research: {
    desc: '<strong>Deep Scan:</strong> AI synthesis of blogs & papers. Takes longer.',
    btnText: 'START DEEP RESEARCH',
    btnClass: 'bg-nesta-purple',
    borderClass: 'border-nesta-purple',
    themeClass: 'theme-violet',
    placeholder: ''
  },
  policy: {
    desc: '<strong>Policy Scan:</strong> International policy &amp; grey literature scan.',
    btnText: 'SCAN POLICY LANDSCAPE',
    btnClass: 'bg-nesta-yellow',
    borderClass: 'border-nesta-yellow',
    themeClass: 'theme-aqua',
    placeholder: "Enter a policy area (e.g., 'AI Regulation')"
  }
};

function switchMainView(viewName) {
  // Kept for backward compatibility; scanner is always visible now.
}
window.switchMainView = switchMainView;

// ── Modal Logic ──────────────────────────────────────────────────────────────
function toggleModal(name, show) {
  const modals = {
    db: {
      overlay: document.getElementById('db-overlay'),
      content: document.getElementById('db-modal')
    },
    help: {
      overlay: document.getElementById('help-overlay'),
      content: document.getElementById('help-modal')
    }
  };

  const m = modals[name];
  if (!m || !m.overlay || !m.content) return;
  if (show) {
    m.overlay.classList.add('open');
    m.content.classList.add('open');
    if (name === 'db') refreshDatabase();
  } else {
    m.overlay.classList.remove('open');
    m.content.classList.remove('open');
  }
}

document.getElementById('open-db-btn')?.addEventListener('click',
  () => toggleModal('db', true));
document.getElementById('close-db-btn')?.addEventListener('click',
  () => toggleModal('db', false));
document.getElementById('db-overlay')?.addEventListener('click',
  () => toggleModal('db', false));

document.querySelectorAll(".mode-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-toggle").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const mode = btn.dataset.mode;
    state.currentMode = mode;

    const config = MODE_CONFIG[mode];

    // Apply theme class to body for CSS variable cascade
    document.body.className =
      `bg-app text-main h-screen flex flex-col overflow-hidden ${config.themeClass}`;

    // Update mode description
    const descBox = document.getElementById("mode-description");
    if (descBox && config) {
      descBox.innerHTML = config.desc;
      descBox.className = "text-sm text-main bg-input p-3 rounded border-l-4 " + config.borderClass;
    }

    // Update scan button text and colour
    const scanBtn = document.getElementById("scan-btn");
    if (scanBtn && config) {
      scanBtn.textContent = config.btnText;
      scanBtn.classList.remove("bg-nesta-blue", "bg-nesta-purple", "bg-nesta-yellow", "bg-btn-accent");
      scanBtn.classList.add(config.btnClass);
    }

    // Toggle input visibility (textarea for Deep, input for others)
    if (mode === "research") {
      dom.queryInput?.classList.add("hidden");
      dom.researchInput?.classList.remove("hidden");
    } else {
      dom.queryInput?.classList.remove("hidden");
      dom.researchInput?.classList.add("hidden");
      if (dom.queryInput && config.placeholder) {
        dom.queryInput.placeholder = config.placeholder;
      }
    }

    // Switch to scan view when mode changes
    switchMainView("scan");

    state.globalSignalsArray = [];
    dom.radarFeed.innerHTML = "";
    dom.emptyState.classList.remove("hidden");
    if (dom.scanStatus) dom.scanStatus.textContent = `Mode switched to ${btn.textContent.trim()}`;

    // Update preview for this mode
    loadRecentPreview(mode);
  });
});

document.getElementById("scan-btn")?.addEventListener("click", runScan);
document.getElementById("refresh-db-btn")?.addEventListener("click", refreshDatabase);
dom.queryInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runScan();
  }
});
dom.researchInput?.addEventListener("keydown", (event) => {
  // Use Ctrl+Enter (Windows/Linux) or Cmd+Enter (macOS) to trigger scan
  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
    event.preventDefault();
    runScan();
  }
});
document.getElementById("help-btn")?.addEventListener("click", () => {
  toggleModal('help', true);
});
document.getElementById("close-help-btn")?.addEventListener("click", () => {
  toggleModal('help', false);
});
document.getElementById("help-overlay")?.addEventListener("click", () => {
  toggleModal('help', false);
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Scan Logic
// ─────────────────────────────────────────────────────────────────────────────
async function runScan() {
  const query = state.currentMode === 'research'
    ? (dom.researchInput?.value.trim() || '')
    : (dom.queryInput?.value.trim() || '');
  if (!query) {
    showToast("Please enter a topic", "error");
    return;
  }

  const mission = dom.missionSelect.value;
  state.globalSignalsArray = [];
  dom.radarFeed.innerHTML = "";
  dom.emptyState.classList.add("hidden");
  dom.scanLoader?.classList.remove("hidden");
  if (dom.scanStatus) dom.scanStatus.textContent = "Scanning active...";

  try {
    if (state.currentMode === "research") {
      // Deep Scan (JSON)
      const res = await fetch(`${API_BASE_URL}/api/mode/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, mission }),
      });
      if (!res.ok) throw new Error(`Request failed (${res.status})`);
      
      const signals = await res.json();
      signals.forEach((signal) => {
        state.globalSignalsArray.push(signal);
        renderSignalCard(signal);
      });
      showToast(`Deep Scan complete. ${signals.length} synthesis found.`, "success");
    
    } else {
      // Quick Scan / Monitor (Streaming)
      const res = await fetch(`${API_BASE_URL}/api/mode/${state.currentMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, topic: query, mission, mode: state.currentMode }),
      });
      if (!res.ok || !res.body) throw new Error(`Request failed (${res.status})`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            handleStreamEvent(JSON.parse(line));
          } catch (e) {
            console.warn("Stream parse error", e);
          }
        }
      }
      showToast("Scan complete.", "success");
      
      // Auto-trigger clustering after scan
      if (typeof window.autoClusterAfterScan === 'function') {
        window.autoClusterAfterScan();
      }
    }
  } catch (error) {
    console.error(error);
    showToast(`Scan failed: ${error.message}`, "error");
  } finally {
    dom.scanLoader?.classList.add("hidden");
    if (dom.scanStatus) dom.scanStatus.textContent = "Scan finished.";
    if (state.globalSignalsArray.length === 0) dom.emptyState.classList.remove("hidden");

    // Refresh preview with new data
    loadRecentPreview(state.currentMode);
  }
}

function handleStreamEvent(event) {
  if (event.msg) {
    dom.scanStatus.textContent = event.msg;
  }
  if (event.status === "blip" && event.blip) {
    state.globalSignalsArray.push(event.blip);
    renderSignalCard(event.blip);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 5. Rendering & UI
// ─────────────────────────────────────────────────────────────────────────────
function renderSignalCard(signal) {
  const el = document.createElement("article");
  el.className = "bg-white p-6 rounded-xl border border-slate-200 shadow-sm animate-slide-in relative";

  el.innerHTML = `
    <div class="flex justify-between items-start mb-3 gap-3">
      <span class="bg-slate-100 text-slate-700 text-[10px] font-bold uppercase px-2 py-1 rounded tracking-wider">${escapeHtml(signal.mission || "General")}</span>
      <div class="flex gap-2">
        <button class="text-xs font-bold px-2 py-1 rounded bg-nesta-yellow text-nesta-navy hover:opacity-90 transition-opacity" data-action="star">★ Star</button>
        <button class="text-xs font-bold px-2 py-1 rounded bg-nesta-navy text-white hover:opacity-90 transition-opacity" data-action="archive">Archive</button>
      </div>
    </div>
    <h3 class="font-display text-lg font-bold text-nesta-navy leading-tight mb-2">
      <a href="${escapeAttribute(signal.url || "#")}" target="_blank" class="hover:text-nesta-blue transition-colors">${escapeHtml(signal.title || "Untitled")}</a>
    </h3>
    <p class="text-sm text-slate-600 leading-relaxed mb-4">${escapeHtml(signal.summary || "")}</p>
    <div class="border-t border-slate-100 pt-3 flex justify-between items-center">
      <div class="text-xs text-slate-500 truncate pr-3 max-w-[200px]">${escapeHtml(signal.source || "Web")}</div>
      <div class="text-right">
        <div class="text-[10px] font-bold uppercase text-slate-400">Score</div>
        <div class="font-display font-bold text-nesta-blue">${Number(signal.final_score || 0).toFixed(2)}</div>
      </div>
    </div>
  `;

  const starBtn = el.querySelector('[data-action="star"]');
  const archiveBtn = el.querySelector('[data-action="archive"]');

  starBtn?.addEventListener("click", () => toggleStar(signal.url));
  archiveBtn?.addEventListener("click", async () => {
    await archiveSignal(signal.url);
    el.remove();
    if (dom.radarFeed.children.length === 0) dom.emptyState.classList.remove("hidden");
  });

  dom.radarFeed.prepend(el);
}

// ─────────────────────────────────────────────────────────────────────────────
// 6. Database & System Actions
// ─────────────────────────────────────────────────────────────────────────────
async function refreshDatabase() {
  const grid = document.getElementById("database-grid");
  if (!grid) return;

  grid.innerHTML = '<div class="col-span-3 text-center text-slate-400">Loading...</div>';
  try {
    const res = await fetch(`${API_BASE_URL}/api/saved`); // Updated to use API_BASE_URL
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    const items = await res.json();

    grid.innerHTML = "";
    if (!Array.isArray(items) || items.length === 0) {
      grid.innerHTML = '<div class="col-span-3 text-center text-slate-400">Database is empty.</div>';
      return;
    }

    items.forEach((item) => {
      const title = item.title || item.Title || "Untitled";
      const mission = item.mission || item.Mission || "General";
      const summary = item.summary || item.Summary || "";
      const url = item.url || item.URL || "";

      const card = document.createElement("div");
      card.className = "bg-white p-6 rounded-xl border border-slate-200 shadow-sm";
      card.innerHTML = `
        <div class="flex justify-between mb-2 gap-2">
           <span class="text-xs font-bold bg-nesta-blue text-white px-2 py-1 rounded">${escapeHtml(mission)}</span>
           <button class="text-xs font-bold px-2 py-1 rounded bg-nesta-navy text-white hover:opacity-90" data-action="archive">Archive</button>
        </div>
        <h4 class="font-bold text-nesta-navy mb-2 line-clamp-2">${escapeHtml(title)}</h4>
        <div class="text-xs text-slate-500 mb-4 line-clamp-3">${escapeHtml(summary.slice(0, 150))}</div>
        <a href="${escapeAttribute(url || "#")}" target="_blank" class="inline-block text-xs font-bold text-nesta-blue hover:underline">View source</a>
      `;
      card.querySelector('[data-action="archive"]')?.addEventListener("click", async () => {
        await archiveSignal(url);
        card.remove();
        if (grid.children.length === 0) grid.innerHTML = '<div class="col-span-3 text-center text-slate-400">Database is empty.</div>';
      });
      grid.appendChild(card);
    });
  } catch (error) {
    grid.innerHTML = `<div class="text-red-500">Error: ${escapeHtml(error.message)}</div>`;
  }
}

async function toggleStar(url) {
  if (!url) return;
  await updateSignalStatus(url, "Starred");
  showToast("Signal starred", "success");
}

async function archiveSignal(url) {
  if (!url) return;
  await updateSignalStatus(url, "Archived");
  showToast("Signal archived", "info");
}

async function updateSignalStatus(url, status) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/saved`, { // Updated to use API_BASE_URL
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, status }),
    });
    if (!res.ok) {
      throw new Error(`Failed to set status: ${status}`);
    }
    return true;
  } catch (e) {
    console.error(e);
    showToast(`Action failed: ${e.message}`, "error");
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 6b. Recent Preview Panel (Context-Aware)
// ─────────────────────────────────────────────────────────────────────────────
const MAX_PREVIEW_CARDS = 3;
const MAX_PREVIEW_SUMMARY_LENGTH = 150;
const PREVIEW_MODE_NAMES = {
  radar: { title: "Quick Scan", icon: "⚡" },
  research: { title: "Deep Scan", icon: "🧠" },
  policy: { title: "Policy Scan", icon: "🌍" }
};

const PREVIEW_MODE_MAP = {
  radar: ["Radar", "Quick"],
  research: ["Research", "Deep", "Synthesis"],
  policy: ["Policy", "Monitor"]
};

async function loadRecentPreview(mode) {
  const container = document.getElementById("recent-preview-container");
  const grid = document.getElementById("recent-preview-grid");
  const title = document.getElementById("recent-preview-title");
  const icon = document.getElementById("recent-preview-icon");

  if (!container || !grid || !title || !icon) return;

  container.classList.remove("hidden");
  grid.innerHTML = '<div class="col-span-3 text-center text-muted">Loading...</div>';

  const modeInfo = PREVIEW_MODE_NAMES[mode] || PREVIEW_MODE_NAMES.radar;
  title.textContent = `Recent ${modeInfo.title}s`;
  icon.textContent = modeInfo.icon;

  try {
    const res = await fetch(`${API_BASE_URL}/api/saved`);
    if (!res.ok) throw new Error(`Request failed (${res.status})`);
    const items = await res.json();

    if (!Array.isArray(items)) {
      grid.innerHTML = `
        <div class="col-span-3 text-center text-muted py-4
                    border border-dashed border-borderline rounded-xl">
            No saved ${escapeHtml(modeInfo.title)}s. Run a scan to populate.
        </div>`;
      return;
    }

    const modeKeys = PREVIEW_MODE_MAP[mode] || PREVIEW_MODE_MAP.radar;
    const filtered = items
      .filter(item => {
        const itemMode = item.Mode || item.mode || "Radar";
        return modeKeys.some(m =>
          itemMode.toLowerCase().includes(m.toLowerCase())
        );
      })
      .slice(0, MAX_PREVIEW_CARDS);

    grid.innerHTML = "";
    if (filtered.length === 0) {
      grid.innerHTML = `
        <div class="col-span-3 text-center text-muted py-4
                    border border-dashed border-borderline rounded-xl">
            No saved ${escapeHtml(modeInfo.title)}s. Run a scan to populate.
        </div>`;
      return;
    }

    filtered.forEach(item => {
      const itemTitle = item.Title || item.title || "Untitled";
      const itemMission = item.Mission || item.mission || "General";
      const itemSummary = item.Summary || item.summary || "";
      const itemUrl = item.URL || item.url || "";
      const itemScore = Number(item.score_activity || 0).toFixed(1);

      const card = document.createElement("div");
      card.className =
        "bg-panel backdrop-blur-sm p-5 rounded-xl border border-borderline " +
        "hover:shadow-xl hover:-translate-y-1 cursor-pointer transition-all";
      card.innerHTML = `
        <div class="flex justify-between mb-2">
            <span class="text-[10px] font-bold bg-input text-main px-2 py-1 rounded border border-borderline">
                ${escapeHtml(itemMission)}
            </span>
            <span class="text-xs text-muted font-bold">${escapeHtml(itemScore)}</span>
        </div>
        <h4 class="font-bold text-main mb-2 line-clamp-2">${escapeHtml(itemTitle)}</h4>
        <p class="text-xs text-muted line-clamp-3">${escapeHtml(itemSummary.slice(0, MAX_PREVIEW_SUMMARY_LENGTH))}</p>
      `;
      if (itemUrl) {
        card.addEventListener("click", () => window.open(itemUrl, "_blank", "noopener,noreferrer"));
      }
      grid.appendChild(card);
    });
  } catch (error) {
    console.warn("Preview load failed:", error.message);
    grid.innerHTML = `
      <div class="col-span-3 text-center text-muted py-4
                  border border-dashed border-borderline rounded-xl">
          Could not load recent scans.
      </div>`;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// 7. Utilities
// ─────────────────────────────────────────────────────────────────────────────
function showToast(message, type = "info") {
  if (!dom.toastContainer) return;

  const colors = {
    success: "bg-nesta-green text-white",
    error: "bg-nesta-red text-white",
    info: "bg-nesta-navy text-white",
  };

  const toast = document.createElement("div");
  toast.className = `p-3 rounded shadow-lg text-sm font-bold ${colors[type] || colors.info} animate-slide-in`;
  toast.textContent = message;
  dom.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value || "");
}

// ─────────────────────────────────────────────────────────────────────────────
// 8. Slide-Over Detail Panel
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Open detail panel with signal information
 */
function openDetailPanel(signal) {
  const panel = document.getElementById('detail-panel');
  const overlay = document.getElementById('detail-overlay');
  const content = document.getElementById('detail-content');
  
  if (!panel || !overlay || !content) return;
  
  // Populate content
  content.innerHTML = `
    <div class="space-y-6">
      <div>
        <h3 class="text-3xl font-display font-bold text-nesta-navy mb-2">${escapeHtml(signal.title || 'Untitled')}</h3>
        <div class="flex flex-wrap gap-2 mb-4">
          ${signal.mission ? `<span class="mission-badge ${getMissionBadgeClassForDetail(signal.mission)}">${escapeHtml(signal.mission)}</span>` : ''}
          ${signal.typology ? `<span class="px-3 py-1 bg-nesta-blue text-white text-xs font-bold uppercase rounded-full">${escapeHtml(signal.typology)}</span>` : ''}
        </div>
      </div>
      
      <div>
        <h4 class="text-sm font-bold text-nesta-navy uppercase tracking-wider mb-2">Summary</h4>
        <p class="text-base text-slate-700 leading-relaxed">${escapeHtml(signal.summary || 'No description available.')}</p>
      </div>
      
      <div class="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Activity</div>
          <div class="text-2xl font-bold text-nesta-navy">${(signal.score_activity || 0).toFixed(1)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Attention</div>
          <div class="text-2xl font-bold text-nesta-navy">${(signal.score_attention || 0).toFixed(1)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Recency</div>
          <div class="text-2xl font-bold text-nesta-navy">${(signal.score_recency || 0).toFixed(1)}</div>
        </div>
      </div>
      
      <div>
        <h4 class="text-sm font-bold text-nesta-navy uppercase tracking-wider mb-2">Source</h4>
        <p class="text-sm text-slate-600 mb-2">${escapeHtml(signal.source || 'Unknown')}</p>
        ${signal.url ? `<a href="${escapeAttribute(signal.url)}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 px-4 py-2 bg-nesta-blue text-white font-bold text-sm rounded-lg hover:bg-nesta-navy transition-colors">
          <span>View Source</span>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
          </svg>
        </a>` : ''}
      </div>
      
      ${signal.date ? `<div class="text-xs text-slate-500">Published: ${escapeHtml(signal.date)}</div>` : ''}
    </div>
  `;
  
  // Open panel
  panel.classList.add('open');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}

/**
 * Close detail panel
 */
function closeDetailPanel() {
  const panel = document.getElementById('detail-panel');
  const overlay = document.getElementById('detail-overlay');
  
  if (!panel || !overlay) return;
  
  panel.classList.remove('open');
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

/**
 * Get mission badge class for detail view
 */
function getMissionBadgeClassForDetail(mission) {
  const classes = {
    'A Sustainable Future': 'mission-badge-green',
    'A Healthy Life': 'mission-badge-pink',
    'A Fairer Start': 'mission-badge-yellow',
  };
  return classes[mission] || 'mission-badge-green';
}

// Set up panel event listeners
document.addEventListener('DOMContentLoaded', () => {
  const closeBtn = document.getElementById('close-detail-panel');
  const overlay = document.getElementById('detail-overlay');
  
  if (closeBtn) {
    closeBtn.addEventListener('click', closeDetailPanel);
  }
  
  if (overlay) {
    overlay.addEventListener('click', closeDetailPanel);
  }
  
  // Listen for card clicks
  document.addEventListener('click', (e) => {
    const card = e.target.closest('.signal-card');
    if (card && !e.target.closest('a') && !e.target.closest('button')) {
      // Get signal data from card (you'll need to store this in dataset or similar)
      const title = card.querySelector('h3')?.textContent || '';
      const summary = card.querySelector('p')?.textContent || '';
      const url = card.dataset.url || '';
      
      openDetailPanel({ title, summary, url });
    }
    
    // Handle action button clicks
    const actionBtn = e.target.closest('.action-btn');
    if (actionBtn) {
      e.stopPropagation();
      const action = actionBtn.dataset.action;
      const url = actionBtn.dataset.url;
      
      switch (action) {
        case 'star':
          toggleStar(url);
          showToast('Signal starred!', 'success');
          break;
        case 'archive':
          archiveSignal(url);
          showToast('Signal archived', 'info');
          break;
        case 'view':
          // Get full signal data and open detail panel
          openDetailPanel({ url });
          break;
      }
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// 9. Enhanced Toast Notification System
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Enhanced toast notification with bottom-right stacking
 */
function showEnhancedToast(message, type = 'info', duration = 3000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  
  const toast = document.createElement('div');
  toast.className = `toast-notification ${type}`;
  
  const icons = {
    success: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>',
    error: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>',
    warning: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>',
    info: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path></svg>',
  };
  
  toast.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="flex-shrink-0">
        ${icons[type] || icons.info}
      </div>
      <div class="flex-1 text-sm font-medium text-nesta-navy">
        ${escapeHtml(message)}
      </div>
      <button class="toast-close flex-shrink-0 text-slate-400 hover:text-nesta-navy transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
  `;
  
  // Add close button handler
  const closeBtn = toast.querySelector('.toast-close');
  closeBtn?.addEventListener('click', () => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  });
  
  container.appendChild(toast);
  
  // Auto remove after duration
  setTimeout(() => {
    if (toast.parentElement) {
      toast.classList.add('toast-exit');
      setTimeout(() => toast.remove(), 300);
    }
  }, duration);
}

// Replace the old showToast with the enhanced version for new calls
window.showEnhancedToast = showEnhancedToast;

// ─────────────────────────────────────────────────────────────────────────────
// 10. Smart Clustering & Matrix Visualization
// ─────────────────────────────────────────────────────────────────────────────

let currentThemes = [];
let currentThemeFilter = null;

/**
 * Call clustering API and render theme chips
 */
async function clusterAndRenderThemes(signals) {
  if (!signals || signals.length < 3) {
    console.log('Not enough signals for clustering (minimum 3 required)');
    return;
  }
  
  try {
    console.log(`Clustering ${signals.length} signals...`);
    
    const response = await fetch(`${API_BASE_URL}/api/mode/cluster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signals: signals })
    });
    
    if (!response.ok) {
      throw new Error(`Clustering failed: ${response.status}`);
    }
    
    const result = await response.json();
    currentThemes = result.themes || [];
    
    // Save scan_id and update URL if returned
    if (result.scan_id) {
      state.currentScanId = result.scan_id;
      updateUrlWithScanId(result.scan_id);
      
      // Show share button
      const shareBtn = document.getElementById('share-scan-btn');
      if (shareBtn) {
        shareBtn.style.display = 'inline-flex';
      }
      
      console.log(`Scan saved with ID: ${result.scan_id}`);
    }
    
    if (currentThemes.length > 0) {
      console.log(`Found ${currentThemes.length} themes`);
      
      // Import and render theme chips
      import('./ui.js').then(uiModule => {
        const container = document.getElementById('theme-chips-container');
        uiModule.renderThemeChips(currentThemes, container, handleThemeFilter);
      });
    } else {
      console.log('No themes found');
    }
  } catch (error) {
    console.error('Clustering failed:', error);
  }
}

/**
 * Handle theme filter selection
 */
function handleThemeFilter(theme) {
  currentThemeFilter = theme;
  
  // Re-render signals with filter
  const feed = document.getElementById('radar-feed');
  if (!feed) return;
  
  feed.innerHTML = '';
  
  let filteredSignals = state.globalSignalsArray;
  
  if (theme && theme.signal_ids) {
    filteredSignals = state.globalSignalsArray.filter((signal, index) => {
      return theme.signal_ids.includes(index);
    });
  }
  
  // Re-render filtered signals
  import('./ui.js').then(uiModule => {
    filteredSignals.forEach((signal, index) => {
      const card = uiModule.createSignalCard(signal);
      if (card) {
        card.style.setProperty('--card-index', index);
        feed.appendChild(card);
      }
    });
  });
  
  console.log(`Filtered to ${filteredSignals.length} signals`);
}

/**
 * Setup view toggle buttons
 */
function setupViewToggle() {
  const gridBtn = document.getElementById('gridViewBtn');
  const matrixBtn = document.getElementById('matrixViewBtn');
  const gridView = document.getElementById('radar-feed');
  const matrixView = document.getElementById('matrixContainer');
  
  if (!gridBtn || !matrixBtn || !gridView || !matrixView) return;
  
  gridBtn.addEventListener('click', () => {
    gridBtn.classList.add('active');
    matrixBtn.classList.remove('active');
    gridView.classList.remove('hidden');
    matrixView.classList.add('hidden');
  });
  
  matrixBtn.addEventListener('click', () => {
    matrixBtn.classList.add('active');
    gridBtn.classList.remove('active');
    gridView.classList.add('hidden');
    matrixView.classList.remove('hidden');
    
    // Render matrix
    import('./matrix.js').then(matrixModule => {
      let signalsToShow = state.globalSignalsArray;
      if (currentThemeFilter && currentThemeFilter.signal_ids) {
        signalsToShow = state.globalSignalsArray.filter((signal, index) => {
          return currentThemeFilter.signal_ids.includes(index);
        });
      }
      matrixModule.renderHorizonMatrix(signalsToShow);
    });
  });
}

// Initialize view toggle on page load
document.addEventListener('DOMContentLoaded', () => {
  setupViewToggle();
});

/**
 * Auto-trigger clustering after scan completes
 */
function autoClusterAfterScan() {
  if (state.globalSignalsArray.length >= 3) {
    setTimeout(() => {
      clusterAndRenderThemes(state.globalSignalsArray);
    }, 500);
  }
}

/**
 * Load a saved scan from storage
 */
async function loadScan(scanId) {
  try {
    console.log(`Loading scan ${scanId}...`);
    showToast('Loading saved scan...', 'info');
    
    const response = await fetch(`${API_BASE_URL}/api/mode/scan/${scanId}`);
    
    if (!response.ok) {
      throw new Error('Scan not found');
    }
    
    const scanData = await response.json();
    
    // Update state
    state.currentScanId = scanId;
    state.globalSignalsArray = scanData.signals || [];
    
    // Update query input
    if (dom.queryInput) {
      dom.queryInput.value = scanData.query || '';
    }
    
    // Render signals
    dom.radarFeed.innerHTML = '';
    scanData.signals.forEach((signal, index) => {
      const cardHtml = import('./ui.js').then(uiModule => {
        const card = uiModule.createSignalCard(signal, index);
        dom.radarFeed.appendChild(card);
      });
    });
    
    // Render themes if available
    if (scanData.themes && scanData.themes.length > 0) {
      currentThemes = scanData.themes;
      const container = document.getElementById('theme-chips-container');
      if (container) {
        import('./ui.js').then(uiModule => {
          uiModule.renderThemeChips(scanData.themes, container, handleThemeFilter);
        });
      }
    }
    
    // Hide empty state
    dom.emptyState.classList.add('hidden');
    
    showToast(`Loaded scan: ${scanData.query}`, 'success');
    console.log(`Scan ${scanId} loaded with ${scanData.signals.length} signals and ${scanData.themes.length} themes`);
    
  } catch (error) {
    console.error('Failed to load scan:', error);
    showToast('Failed to load scan', 'error');
  }
}

/**
 * Get share URL for current scan
 */
function getShareUrl() {
  if (!state.currentScanId) {
    showToast('No scan to share yet', 'warning');
    return null;
  }
  return `${window.location.origin}${window.location.pathname}?scan=${state.currentScanId}`;
}

/**
 * Copy share URL to clipboard
 */
async function shareCurrentScan() {
  const shareUrl = getShareUrl();
  if (!shareUrl) return;
  
  try {
    await navigator.clipboard.writeText(shareUrl);
    showToast('Share link copied to clipboard!', 'success');
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    showToast('Failed to copy link', 'error');
  }
}

/**
 * Check URL for scan parameter on page load
 */
function checkUrlForScan() {
  const params = new URLSearchParams(window.location.search);
  const scanId = params.get('scan');
  
  if (scanId) {
    console.log(`Found scan ID in URL: ${scanId}`);
    loadScan(scanId);
  }
}

/**
 * Update URL with scan ID
 */
function updateUrlWithScanId(scanId) {
  const newUrl = new URL(window.location.href);
  newUrl.searchParams.set('scan', scanId);
  window.history.pushState({ scanId }, '', newUrl.toString());
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  setupViewToggle();
  checkUrlForScan();

  // Load initial preview for default mode
  loadRecentPreview(state.currentMode);
  
  // Add share button if not exists
  const resultsHeader = document.querySelector('.results-header');
  if (resultsHeader && !document.getElementById('share-scan-btn')) {
    const shareBtn = document.createElement('button');
    shareBtn.id = 'share-scan-btn';
    shareBtn.className = 'btn btn-secondary';
    shareBtn.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
              d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"></path>
      </svg>
      Share Scan
    `;
    shareBtn.addEventListener('click', shareCurrentScan);
    shareBtn.style.display = 'none'; // Hide until scan completes
    resultsHeader.appendChild(shareBtn);
  }
});

// Expose functions globally
window.autoClusterAfterScan = autoClusterAfterScan;
window.handleThemeFilter = handleThemeFilter;
window.loadScan = loadScan;
window.shareCurrentScan = shareCurrentScan;
