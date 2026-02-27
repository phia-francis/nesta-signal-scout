import { escapeHtml } from './utils.js';

const MISSION_THEMES = {
  'A Sustainable Future': {
    color: 'nesta-green',
    bg: 'bg-nesta-green',
    text: 'text-white',
    border: 'border-nesta-green',
  },
  'A Healthy Life': {
    color: 'nesta-pink',
    bg: 'bg-nesta-pink',
    text: 'text-nesta-navy',
    border: 'border-nesta-pink',
  },
  'A Fairer Start': {
    color: 'nesta-yellow',
    bg: 'bg-nesta-yellow',
    text: 'text-nesta-navy',
    border: 'border-nesta-yellow',
  },
  default: {
    color: 'nesta-blue',
    bg: 'bg-nesta-blue',
    text: 'text-white',
    border: 'border-nesta-sand',
  },
};

function getThemeForMission(mission) {
  return MISSION_THEMES[mission] || MISSION_THEMES.default;
}

function getSourceBadgeTheme(source) {
  if (source === 'UKRI GtR') {
    return 'bg-nesta-green/10 text-nesta-green border border-nesta-green';
  }
  if (source === 'OpenAlex') {
    return 'bg-nesta-purple/10 text-nesta-purple border border-nesta-purple';
  }
  return 'bg-nesta-blue/10 text-nesta-blue border border-nesta-blue';
}

function clipboardIcon() {
  return `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" class="w-4 h-4" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2"></rect>
      <path d="M5 15V5a2 2 0 0 1 2-2h10"></path>
    </svg>
  `;
}

export function createSignalCard(signal, context = "scan") {
    // Support both API-normalised keys and raw Google Sheets capitalised headers.
    const titleText = signal.title || signal.Title || "Untitled";
    const summaryText = signal.summary || signal.Summary || signal.Hook || "";
    const signalUrl = signal.url || signal.URL || "";
    const mission = signal.mission || signal.Mission || "General";
    const typology = signal.typology || signal.Typology || "";
    const activityScore = signal.score_activity ?? signal.Score_Activity ?? signal.Score ?? 0;
    const attentionScore = signal.score_attention ?? signal.Score_Attention ?? signal.Score ?? 0;
    const theme = getThemeForMission(mission);
    const isSynthesis = typology === "Synthesis";

    const card = document.createElement("article");
    card.className = isSynthesis
        ? "signal-card bg-slate-50 border-2 border-nesta-blue shadow-hard rounded-lg p-8 h-auto min-h-[250px] flex flex-col gap-4 relative col-span-full"
        : `signal-card bg-white border-2 ${theme.border} shadow-hard rounded-lg p-6 h-auto min-h-[250px] flex flex-col gap-4 relative`;

    // --- Header: mission pill + cluster pill ---
    const headerWrap = document.createElement("div");
    headerWrap.className = "flex flex-wrap items-center gap-2 mb-2";

    const missionPill = document.createElement("span");
    missionPill.className = `rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ${theme.bg} ${theme.text}`;
    missionPill.textContent = mission;
    headerWrap.appendChild(missionPill);

    if (signal.narrative_group && signal.narrative_group !== "Unsorted") {
        const clusterPill = document.createElement("span");
        clusterPill.className =
            "rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wider bg-nesta-purple/10 text-nesta-purple border border-nesta-purple/30";
        clusterPill.textContent = signal.narrative_group;
        headerWrap.appendChild(clusterPill);
    }

    // --- Title: hyperlinked to source ---
    const title = document.createElement("a");
    title.className =
        "font-display text-xl leading-tight text-slate-900 hover:text-nesta-blue transition-colors cursor-pointer decoration-2 hover:underline";
    title.textContent = titleText;
    if (signalUrl) {
        title.href = signalUrl;
        title.target = "_blank";
        title.rel = "noopener noreferrer";
        title.addEventListener("click", (e) => e.stopPropagation());
    }

    // --- Summary: markdown for Synthesis, toggle for all others ---
    const summaryWrap = document.createElement("div");
    summaryWrap.className = "flex flex-col items-start gap-1 w-full flex-grow";

    const summary = document.createElement("div");

    if (isSynthesis && window.marked && window.DOMPurify) {
        summary.className = "prose prose-sm max-w-none text-nesta-navy/80 mt-2";
        summary.innerHTML = DOMPurify.sanitize(marked.parse(summaryText));
        summaryWrap.appendChild(summary);
    } else {
        summary.className =
            "font-body text-sm text-nesta-navy/80 line-clamp-3 transition-all duration-200";
        summary.textContent = summaryText;
        summaryWrap.appendChild(summary);

        // Only render the "Show More" toggle if the summary actually overflows
        if (typeof requestAnimationFrame === "function") {
            requestAnimationFrame(() => {
                const isOverflowing = summary.scrollHeight > summary.clientHeight + 1;
                if (!isOverflowing) {
                    return;
                }

                const toggleBtn = document.createElement("button");
                toggleBtn.type = "button";
                toggleBtn.className =
                    "text-xs font-bold text-nesta-blue hover:text-nesta-navy underline mt-1";
                toggleBtn.textContent = "Show More";
                toggleBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const collapsed = summary.classList.toggle("line-clamp-3");
                    toggleBtn.textContent = collapsed ? "Show More" : "Show Less";
                });
                summaryWrap.appendChild(toggleBtn);
            });
        }
    }

    let domainName = "Unknown Source";
    if (signalUrl) {
        try {
            const urlObj = new URL(signalUrl);
            domainName = urlObj.hostname.replace(/^www\./, '');
        } catch (e) {
            // Invalid URL, keep default
        }
    }

    const country = signal.origin_country || signal.Origin_Country || "Global";

    const footer = document.createElement("footer");
    footer.className =
        "mt-auto pt-3 border-t border-nesta-sand/50 flex flex-wrap items-center justify-between gap-3";

    const metrics = document.createElement("div");
    metrics.className = "text-xs text-nesta-navy/70 cursor-help relative inline-block";
    metrics.innerHTML = `<strong>${domainName}</strong> <span class="text-slate-400">(${country})</span><br/>Activity ${Number(activityScore || 0).toFixed(1)} • Attention ${Number(attentionScore || 0).toFixed(1)}`;
    metrics.setAttribute(
        "data-tooltip",
        "AI Confidence & Impact Scores: Calculated via rigorous LLM evaluation of source authority, factuality, recency, and trend relevance."
    );

    const actionWrap = document.createElement("div");
    actionWrap.className = "flex gap-2 items-center";

    if (signal.status !== "Archived") {
        const starBtn = document.createElement("button");
        starBtn.innerHTML = "⭐ Star";
        starBtn.className =
            "text-xs font-bold px-2 py-1 rounded bg-slate-100 hover:bg-yellow-100 text-slate-600 hover:text-yellow-700 transition-colors";
        starBtn.onclick = (e) => updateSignalStatus(e, signalUrl, "Starred");

        const archiveBtn = document.createElement("button");
        archiveBtn.innerHTML = "🗑️ Archive";
        archiveBtn.className =
            "text-xs font-bold px-2 py-1 rounded bg-slate-100 hover:bg-red-100 text-slate-600 hover:text-red-700 transition-colors";
        archiveBtn.onclick = (e) => updateSignalStatus(e, signalUrl, "Archived");

        actionWrap.append(starBtn, archiveBtn);
    } else {
        const unarchiveBtn = document.createElement("button");
        unarchiveBtn.innerHTML = "📦 Unarchive";
        unarchiveBtn.className =
            "text-xs font-bold px-2 py-1 rounded bg-slate-100 hover:bg-green-100 text-slate-600 hover:text-green-700 transition-colors";
        unarchiveBtn.onclick = (e) => updateSignalStatus(e, signalUrl, "Active");
        actionWrap.append(unarchiveBtn);
    }

    footer.append(metrics, actionWrap);
    card.append(headerWrap, title, summaryWrap, footer);

    if (context === "preview") {
        card.classList.add("cursor-pointer", "hover:border-nesta-blue", "transition-all");
        card.addEventListener("click", () => {
            document.getElementById("db-overlay").classList.add("active");
            document.getElementById("db-modal").classList.add("active");
        });
    }

    return card;
}

function getApiBaseUrl() {
    const hostname = window.location.hostname;
    if (hostname.endsWith('.github.io')) {
        return 'https://nesta-signal-backend.onrender.com';
    }
    return window.location.origin;
}

async function updateSignalStatus(event, url, status) {
    event.stopPropagation();
    try {
        const response = await fetch(`${getApiBaseUrl()}/api/saved`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, status }),
        });
        if (response.ok) {
            showToast(`Signal marked as ${status}`, "success");
            if (typeof window.refreshDatabase === "function") window.refreshDatabase();
        }
    } catch {
        showToast("Failed to update signal status.", "error");
    }
}

export function showEmptyState(topic, container) {
  if (!container) return;
  const safeTopic = topic && topic.trim() ? topic.trim() : 'your search';
  const wrapper = document.createElement('div');
  wrapper.className = 'col-span-full py-20 flex flex-col items-center justify-center text-center';
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('fill', 'none');
  icon.setAttribute('stroke', 'currentColor');
  icon.setAttribute('stroke-width', '1.8');
  icon.setAttribute('class', 'w-16 h-16 text-nesta-sand mb-6');
  icon.setAttribute('aria-hidden', 'true');

  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', '11');
  circle.setAttribute('cy', '11');
  circle.setAttribute('r', '7');

  const line = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  line.setAttribute('d', 'M20 20l-3.5-3.5');
  icon.append(circle, line);

  const heading = document.createElement('h3');
  heading.className = 'font-display text-xl text-nesta-navy';
  heading.textContent = `No signals found for '${safeTopic}'.`;

  const subtext = document.createElement('p');
  subtext.className = 'font-body text-sm text-nesta-navy/70 mt-2';
  subtext.textContent = 'Try adjusting your search terms or enabling Friction Mode.';

  wrapper.append(icon, heading, subtext);
  container.appendChild(wrapper);
}

export function clearConsole() {
  const consoleEl = document.getElementById('console');
  if (consoleEl) {
    consoleEl.innerHTML = '';
  }
}

export function appendConsoleLog(message, type = 'info') {
  const consoleEl = document.getElementById('console');
  if (!consoleEl) return;

  const lastEntry = consoleEl.lastElementChild;
  if (lastEntry?.textContent === message && lastEntry.classList.contains(`log-entry-${type}`)) {
    return;
  }

  const line = document.createElement('div');
  line.className = `log-entry log-entry-${type}`;
  line.textContent = message;
  consoleEl.appendChild(line);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

export function startScan() {
  const loader = document.getElementById('scan-loader');
  const feed = document.getElementById('radar-feed');
  const emptyState = document.getElementById('empty-state');
  loader?.classList.remove('hidden');
  feed?.classList.add('hidden');
  emptyState?.classList.add('hidden');
}

export function finishScan() {
  const loader = document.getElementById('scan-loader');
  const feed = document.getElementById('radar-feed');
  const emptyState = document.getElementById('empty-state');
  loader?.classList.add('hidden');
  feed?.classList.remove('hidden');
  emptyState?.classList.add('hidden');
}

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  container.querySelectorAll('.modern-toast').forEach((existingToast) => existingToast.remove());

  const toast = document.createElement('div');
  toast.className = `modern-toast ${type === 'error' ? 'error' : ''}`.trim();
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  toast.textContent = message;
  container.appendChild(toast);

  window.setTimeout(() => {
    toast.remove();
  }, 4000);
}

export function renderSignals(signals, container, topic = '', groupBy = null) {
  if (!container) return;
  container.innerHTML = '';

  if (!signals.length) {
    showEmptyState(topic, container);
    return;
  }

  if (!groupBy) {
    signals.forEach((signal) => {
      container.appendChild(createSignalCard(signal));
    });
    return;
  }

  const groupedSignals = signals.reduce((acc, signal) => {
    const rawGroup = signal?.[groupBy];
    const groupName = typeof rawGroup === 'string' && rawGroup.trim() ? rawGroup.trim() : 'Unsorted';
    if (!acc[groupName]) {
      acc[groupName] = [];
    }
    acc[groupName].push(signal);
    return acc;
  }, {});

  const sortedGroupNames = Object.keys(groupedSignals).sort((left, right) => {
    if (left === 'Unsorted') return 1;
    if (right === 'Unsorted') return -1;
    return left.localeCompare(right);
  });

  sortedGroupNames.forEach((groupName) => {
    const section = document.createElement('div');
    section.className = 'mb-8';

    const heading = document.createElement('h3');
    heading.className = 'font-display text-lg text-nesta-navy mb-4 border-b border-slate-200 pb-2';
    heading.textContent = groupName;
    const countSpan = document.createElement('span');
    countSpan.className = 'text-sm text-slate-400 ml-2';
    countSpan.textContent = `(${groupedSignals[groupName].length})`;
    heading.appendChild(countSpan);

    const groupGrid = document.createElement('div');
    groupGrid.className = 'masonry-grid';

    groupedSignals[groupName].forEach((signal) => {
      groupGrid.appendChild(createSignalCard(signal));
    });

    section.append(heading, groupGrid);
    container.appendChild(section);
  });
}

export function renderThemeChips(themes, container, onSelect) {
  if (!container) return;
  container.innerHTML = '';

  if (!themes || themes.length === 0) return;

  const label = document.createElement('span');
  label.className = 'text-xs font-bold text-slate-500 uppercase tracking-wider mr-2';
  label.textContent = 'Detected Themes:';
  container.appendChild(label);

  const allBtn = document.createElement('button');
  allBtn.className = 'px-3 py-1 rounded-full text-xs font-bold transition-colors bg-nesta-navy text-white';
  allBtn.textContent = 'All Signals';
  allBtn.addEventListener('click', () => {
    container.querySelectorAll('button').forEach(b => {
      b.classList.remove('bg-nesta-navy', 'text-white');
      b.classList.add('bg-slate-100', 'text-slate-600');
    });
    allBtn.classList.remove('bg-slate-100', 'text-slate-600');
    allBtn.classList.add('bg-nesta-navy', 'text-white');
    onSelect(null);
  });
  container.appendChild(allBtn);

  themes.forEach((theme) => {
    const btn = document.createElement('button');
    btn.className = 'px-3 py-1 rounded-full text-xs font-bold transition-colors bg-slate-100 text-slate-600 hover:bg-slate-200';
    btn.textContent = theme.name;
    btn.title = theme.description;

    btn.addEventListener('click', () => {
      container.querySelectorAll('button').forEach(b => {
        b.classList.remove('bg-nesta-navy', 'text-white');
        b.classList.add('bg-slate-100', 'text-slate-600');
      });
      btn.classList.remove('bg-slate-100', 'text-slate-600');
      btn.classList.add('bg-nesta-navy', 'text-white');
      onSelect(theme);
    });
    container.appendChild(btn);
  });

  const toggles = document.getElementById('view-toggles');
  if (toggles) toggles.classList.remove('hidden');
}

export function renderClusterInsights(clusterInsights, container) {
    if (!clusterInsights || clusterInsights.length === 0) return;

    const dashboardWrap = document.createElement('div');
    dashboardWrap.className = 'w-full mb-8 flex flex-col gap-4';

    const header = document.createElement('h3');
    header.className = 'text-lg font-bold text-nesta-navy border-b border-nesta-sand/50 pb-2';
    header.textContent = 'Agent Trend Analysis';
    dashboardWrap.appendChild(header);

    const gridWrap = document.createElement('div');
    gridWrap.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4';

    clusterInsights.forEach(insight => {
        if (!insight || typeof insight.cluster_name !== 'string' || typeof insight.trend_summary !== 'string') return;

        const card = document.createElement('div');
        card.className = 'bg-white rounded-lg p-4 border border-nesta-sand shadow-sm flex flex-col';

        const cardHeader = document.createElement('div');
        cardHeader.className = 'flex justify-between items-start mb-2 gap-2';

        const title = document.createElement('h4');
        title.className = 'font-bold text-nesta-navy text-md leading-tight';
        title.textContent = insight.cluster_name;

        const strengthClassMap = {
            'Strong':   'bg-green-100 text-green-800 border-green-200',
            'Moderate': 'bg-yellow-100 text-yellow-800 border-yellow-200',
            'Weak':     'bg-red-100 text-red-800 border-red-200'
        };
        const strengthBadge = document.createElement('span');
        strengthBadge.className = `text-xs font-bold px-2 py-1 rounded-full border ${strengthClassMap[insight.strength] || 'bg-gray-100 text-gray-800'}`;
        strengthBadge.textContent = insight.strength || 'Unknown';

        cardHeader.append(title, strengthBadge);

        const summary = document.createElement('p');
        summary.className = 'text-sm text-nesta-navy/80 font-body mb-3';
        summary.textContent = insight.trend_summary;

        const reasoningWrap = document.createElement('div');
        reasoningWrap.className = 'mt-auto pt-3 border-t border-nesta-sand/50';
        const reasoning = document.createElement('p');
        reasoning.className = 'text-xs text-nesta-navy/60 italic';
        reasoning.textContent = `Evidence: ${insight.reasoning || 'No reasoning provided'}`;
        reasoningWrap.appendChild(reasoning);

        card.append(cardHeader, summary, reasoningWrap);
        gridWrap.appendChild(card);
    });

    dashboardWrap.appendChild(gridWrap);
    container.insertBefore(dashboardWrap, container.firstChild);
}

function sanitizeUrl(url) {
    if (!url) return "#";
    const cleaned = String(url).trim();
    if (/^https?:\/\//i.test(cleaned) || /^mailto:/i.test(cleaned)) {
        return cleaned;
    }
    return "#";
}

function escapeAttribute(value) {
  return escapeHtml(value || "");
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

/**
 * Open detail panel with signal information
 */
export function openDetailPanel(signal) {
  const panel = document.getElementById('detail-panel');
  const overlay = document.getElementById('detail-overlay');
  const content = document.getElementById('detail-content');
  
  if (!panel || !overlay || !content) return;

  const title = signal.title || signal.Title || 'Untitled';
  const mission = signal.mission || signal.Mission || '';
  const typology = signal.typology || signal.Typology || signal.Lenses || '';
  const summary = signal.summary || signal.Hook || signal.Description || signal.Analysis || 'No description available.';
  const scoreActivity = Number(signal.score_activity ?? signal.scoreActivity ?? signal.Score_Activity ?? 0);
  const scoreAttention = Number(signal.score_attention ?? signal.scoreAttention ?? signal.Score_Attention ?? signal.Score ?? 0);
  const scoreRecency = Number(signal.score_recency ?? signal.scoreRecency ?? signal.Score_Recency ?? 0);
  const source = signal.source || signal.Source || 'Unknown';
  const sourceUrl = signal.url || signal.URL || '';
  const publishedDate = signal.date || signal.source_date || signal.published_date || signal.Source_Date || signal.Published_Date || '';
  
  // Populate content
  content.innerHTML = `
    <div class="space-y-6">
      <div>
        <h3 class="text-3xl font-display font-bold text-nesta-navy mb-2">${escapeHtml(title)}</h3>
        <div class="flex flex-wrap gap-2 mb-4">
          ${mission ? `<span class="mission-badge ${getMissionBadgeClassForDetail(mission)}">${escapeHtml(mission)}</span>` : ''}
          ${typology ? `<span class="px-3 py-1 bg-nesta-blue text-white text-xs font-bold uppercase rounded-full">${escapeHtml(typology)}</span>` : ''}
        </div>
      </div>
      
      <div>
        <h4 class="text-sm font-bold text-nesta-navy uppercase tracking-wider mb-2">Summary</h4>
        <p class="text-base text-slate-700 leading-relaxed">${escapeHtml(summary)}</p>
      </div>
      
      <div class="grid grid-cols-3 gap-4 p-4 bg-slate-50 rounded-lg">
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Activity</div>
          <div class="text-2xl font-bold text-nesta-navy">${scoreActivity.toFixed(1)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Attention</div>
          <div class="text-2xl font-bold text-nesta-navy">${scoreAttention.toFixed(1)}</div>
        </div>
        <div>
          <div class="text-xs text-slate-500 uppercase tracking-wider mb-1">Recency</div>
          <div class="text-2xl font-bold text-nesta-navy">${scoreRecency.toFixed(1)}</div>
        </div>
      </div>
      
      <div>
        <h4 class="text-sm font-bold text-nesta-navy uppercase tracking-wider mb-2">Source</h4>
        <p class="text-sm text-slate-600 mb-2">${escapeHtml(source)}</p>
        ${sourceUrl ? `<a href="${escapeAttribute(sanitizeUrl(sourceUrl))}" target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 px-4 py-2 bg-nesta-blue text-white font-bold text-sm rounded-lg hover:bg-nesta-navy transition-colors">
          <span>View Source</span>
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path>
          </svg>
        </a>` : ''}
      </div>
      
      ${publishedDate ? `<div class="text-xs text-slate-500">Published: ${escapeHtml(publishedDate)}</div>` : ''}
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
export function closeDetailPanel() {
  const panel = document.getElementById('detail-panel');
  const overlay = document.getElementById('detail-overlay');
  
  if (!panel || !overlay) return;
  
  panel.classList.remove('open');
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}

/**
 * Enhanced toast notification with bottom-right stacking
 */
export function showEnhancedToast(message, type = 'info', duration = 3000) {
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

export function renderResearchResult(data, container) {
    container.innerHTML = "";

    const researchData = data.signals ? data.signals[0] : data;

    const card = document.createElement("div");
    card.className =
        "w-full max-w-4xl mx-auto bg-white border border-nesta-purple/20 rounded-xl shadow-lg overflow-hidden mb-8";

    card.innerHTML = `
        <div class="bg-nesta-purple text-white p-6">
            <div class="flex justify-between items-start">
                <div>
                    <span class="inline-block px-2 py-1 bg-white/20 rounded text-xs font-bold uppercase tracking-wider mb-2">
                        Deep Dive Research
                    </span>
                    <h2 class="text-3xl font-display font-bold mb-2">${escapeHtml(researchData.Title || "Untitled Research")}</h2>
                    <p class="text-white/90 text-lg italic">"${escapeHtml(researchData.Hook || "")}"</p>
                </div>
                <div class="flex flex-col items-center bg-white/10 rounded-lg p-3 backdrop-blur-sm">
                    <span class="text-3xl font-bold">${researchData.Score || 0}%</span>
                    <span class="text-xs opacity-75">Relevance</span>
                </div>
            </div>
        </div>

        <div class="p-8 space-y-8">
            <section>
                <h3 class="text-xl font-bold text-nesta-black mb-3 border-b border-gray-100 pb-2">Executive Summary</h3>
                <div class="prose max-w-none text-gray-600 leading-relaxed">
                    ${typeof marked !== 'undefined' ? marked.parse(researchData.Analysis || researchData.Description || "No analysis provided.") : escapeHtml(researchData.Analysis || researchData.Description || "No analysis provided.")}
                </div>
            </section>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-gray-50 p-5 rounded-lg border border-gray-100">
                    <h4 class="font-bold text-nesta-purple mb-2">Strategic Implications</h4>
                    <p class="text-sm text-gray-700">${escapeHtml(researchData.Implications || "N/A")}</p>
                </div>
                <div class="bg-gray-50 p-5 rounded-lg border border-gray-100">
                    <h4 class="font-bold text-teal-600 mb-2">Future Outlook (2030)</h4>
                    <p class="text-sm text-gray-700">${escapeHtml(researchData.Future_Outlook || "N/A")}</p>
                </div>
            </div>

            <div class="flex items-center justify-between text-sm text-gray-400 border-t pt-4 mt-4">
                <div class="flex gap-4">
                    <span>Target Mission: ${escapeHtml(researchData.Mission || "General")}</span>
                    <span>Lenses: ${escapeHtml(researchData.Lenses || "N/A")}</span>
                </div>
                <a href="${escapeHtml(sanitizeUrl(researchData.URL || ""))}" target="_blank"
                   class="text-nesta-purple hover:underline font-semibold flex items-center gap-1">
                    View Source
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                    </svg>
                </a>
            </div>
        </div>
    `;

    container.appendChild(card);
}

export { MISSION_THEMES };
