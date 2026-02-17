"use strict";

// ─────────────────────────────────────────────────────────────────────────────
// 1. Dynamic API Configuration (CRITICAL for GitHub Pages)
// ─────────────────────────────────────────────────────────────────────────────
let API_BASE_URL = window.location.origin;
const hostname = window.location.hostname;

if (hostname.endsWith('.github.io')) {
  // Point to Render when running on GitHub Pages
  API_BASE_URL = 'https://nesta-signal-backend.onrender.com';
} else if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
  // Point to local Python server when developing locally
  API_BASE_URL = 'http://localhost:8000';
}
console.log(`[Scout] API configured: ${API_BASE_URL}`);

// ─────────────────────────────────────────────────────────────────────────────
// 2. State & DOM
// ─────────────────────────────────────────────────────────────────────────────
const state = {
  currentMode: "radar",
  globalSignalsArray: [],
};

const dom = {
  radarFeed: document.getElementById("radar-feed"),
  emptyState: document.getElementById("empty-state"),
  scanStatus: document.getElementById("scan-status"),
  queryInput: document.getElementById("query-input"),
  missionSelect: document.getElementById("mission-select"),
  scanLoader: document.getElementById("scan-loader"),
  toastContainer: document.getElementById("toast-container"),
};

// ─────────────────────────────────────────────────────────────────────────────
// 3. Navigation & Mode Switching
// ─────────────────────────────────────────────────────────────────────────────
function switchMainView(viewName) {
  const scanView = document.getElementById("view-scan");
  const dbView = document.getElementById("view-database");
  const navScan = document.getElementById("nav-scan");
  const navDb = document.getElementById("nav-db");

  if (viewName === "scan") {
    scanView.classList.remove("hidden");
    dbView.classList.add("hidden");
    navScan.classList.add("bg-white", "shadow-sm", "text-nesta-navy");
    navScan.classList.remove("text-slate-500");
    navDb.classList.remove("bg-white", "shadow-sm", "text-nesta-navy");
    navDb.classList.add("text-slate-500");
  } else {
    scanView.classList.add("hidden");
    dbView.classList.remove("hidden");
    navDb.classList.add("bg-white", "shadow-sm", "text-nesta-navy");
    navDb.classList.remove("text-slate-500");
    navScan.classList.remove("bg-white", "shadow-sm", "text-nesta-navy");
    navScan.classList.add("text-slate-500");
    refreshDatabase();
  }
}
window.switchMainView = switchMainView;

document.querySelectorAll(".mode-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-toggle").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.currentMode = btn.dataset.mode;

    state.globalSignalsArray = [];
    dom.radarFeed.innerHTML = "";
    dom.emptyState.classList.remove("hidden");
    dom.scanStatus.textContent = `Mode switched to ${btn.textContent.trim()}`;
  });
});

document.getElementById("scan-btn")?.addEventListener("click", runScan);
document.getElementById("refresh-db-btn")?.addEventListener("click", refreshDatabase);
dom.queryInput?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runScan();
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// 4. Scan Logic
// ─────────────────────────────────────────────────────────────────────────────
async function runScan() {
  const query = dom.queryInput.value.trim();
  if (!query) {
    showToast("Please enter a topic", "error");
    return;
  }

  const mission = dom.missionSelect.value;
  state.globalSignalsArray = [];
  dom.radarFeed.innerHTML = "";
  dom.emptyState.classList.add("hidden");
  dom.scanLoader.classList.remove("hidden");
  dom.scanStatus.textContent = "Scanning active...";

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
    }
  } catch (error) {
    console.error(error);
    showToast(`Scan failed: ${error.message}`, "error");
  } finally {
    dom.scanLoader.classList.add("hidden");
    dom.scanStatus.textContent = "Scan finished.";
    if (state.globalSignalsArray.length === 0) dom.emptyState.classList.remove("hidden");
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
  } catch (e) {
    console.error(e);
    showToast(`Action failed: ${e.message}`, "error");
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
