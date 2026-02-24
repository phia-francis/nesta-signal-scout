/**
 * UI rendering and manipulation
 * Handles all DOM updates and visual feedback
 */

import { state } from './state.js';

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Format date for display
 */
function formatDate(dateString) {
  if (!dateString) return 'Recent';
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-GB', { 
      day: 'numeric', 
      month: 'short', 
      year: 'numeric' 
    });
  } catch {
    return 'Recent';
  }
}

/**
 * Get mission color based on mission name
 */
function getMissionColor(mission) {

/**
 * Get mission badge class based on mission name
 */
function getMissionBadgeClass(mission) {
  const classes = {
    'A Sustainable Future': 'mission-badge-green',
    'A Healthy Life': 'mission-badge-pink',
    'A Fairer Start': 'mission-badge-yellow',
  };
  return classes[mission] || 'mission-badge-green';
}
  const colors = {
    'A Sustainable Future': 'text-[#18A48C]',  // Green
    'A Healthy Life': 'text-[#F6A4B7]',        // Pink
    'A Fairer Start': 'text-[#FDB633]',        // Yellow
  };
  return colors[mission] || 'text-nesta-blue';
}

/**
 * Get typology colour class
 */
function getTypologyColor(typology) {
  const colors = {
    'Nascent': 'bg-nesta-violet text-white',
    'Hidden Gem': 'bg-nesta-green text-white',
    'Hype': 'bg-nesta-orange text-white',
    'Established': 'bg-nesta-blue text-white',
  };
  return colors[typology] || 'bg-nesta-dark-grey text-white';
}

/**
 * Get source icon/emoji
 */
function getSourceIcon(source) {
  const icons = {
    'UKRI GtR': '🔬',
    'OpenAlex': '📚',
    'Google Search': '🔍',
    'Gov/Policy': '🏛️',
    'AI Synthesis': '🤖',
    'Web Synthesis': '🤖',
    'Aggregated Sources': '📊',
  };
  return icons[source] || '📡';
}

/**
 * Create a signal card element
 */
export function createSignalCard(signal, context = 'feed') {
  const card = document.createElement('article');
  card.className = 'signal-card bg-white rounded-lg p-6 space-y-4 cursor-pointer hover:shadow-xl transition-all';
  card.dataset.url = signal.url;

  // Header with badges
  const header = document.createElement('div');
  header.className = 'flex items-start justify-between gap-4';
  header.innerHTML = `
    <div class="flex-1">
      <div class="flex items-center gap-2 mb-2">
        <span class="text-2xl">${getSourceIcon(signal.source || 'Google Search')}</span>
        <span class="px-2 py-1 ${getTypologyColor(signal.typology)} text-xs font-bold uppercase tracking-wider rounded">
          ${escapeHtml(signal.typology || 'Nascent')}
        </span>
        ${signal.is_novel ? '<span class="px-2 py-1 bg-nesta-red text-white text-xs font-bold uppercase tracking-wider rounded">New</span>' : ''}
      </div>
      <h3 class="font-display text-xl font-bold text-nesta-navy leading-tight">
        ${escapeHtml(signal.title || 'Untitled Signal')}
      </h3>
    </div>
  `;

  // Summary
  const isSynthesis = signal.typology === 'Synthesis';

  const summaryWrap = document.createElement('div');
  summaryWrap.className = 'flex flex-col items-start gap-1 w-full';

  const summary = document.createElement('div');

  if (isSynthesis && window.marked && window.DOMPurify) {
      // Research Synthesis: render full markdown, no clamp
      summary.className = 'prose prose-sm max-w-none text-nesta-navy/80 mt-2';
      summary.innerHTML = DOMPurify.sanitize(marked.parse(signal.summary || ''));
      summaryWrap.append(summary);
      card.classList.add('col-span-full', 'bg-slate-50', 'border-nesta-blue');
  } else {
      // Standard card: 3-line clamp with conditional Show More toggle
      summary.className = 'font-body text-sm text-nesta-navy/80 line-clamp-3 transition-all duration-200';
      summary.textContent = signal.summary || '';

      summaryWrap.append(summary);

      // Only show the toggle if the content overflows the 3-line clamp
      requestAnimationFrame(() => {
          if (summary.scrollHeight > summary.clientHeight) {
              const toggleBtn = document.createElement('button');
              toggleBtn.type = 'button';
              toggleBtn.className = 'text-xs font-bold text-nesta-blue hover:text-nesta-navy underline mt-1';
              toggleBtn.textContent = 'Show More';

              toggleBtn.addEventListener('click', (e) => {
                  e.stopPropagation();
                  if (summary.classList.contains('line-clamp-3')) {
                      summary.classList.remove('line-clamp-3');
                      toggleBtn.textContent = 'Show Less';
                  } else {
                      summary.classList.add('line-clamp-3');
                      toggleBtn.textContent = 'Show More';
                  }
              });

              summaryWrap.append(toggleBtn);
          }
      });
  }

  // Metadata bar
  const metadata = document.createElement('div');
  metadata.className = 'flex items-center justify-between text-sm text-nesta-dark-grey border-t border-nesta-silver pt-4';

  const metricsDiv = document.createElement('div');
  metricsDiv.className = 'text-xs text-nesta-navy/70 cursor-help inline-block w-fit';
  metricsDiv.textContent = `Activity ${Number(signal.score_activity || 0).toFixed(1)} • Attention ${Number(signal.score_attention || 0).toFixed(1)} • AI Confidence ${Number(signal.score_confidence || signal.final_score || 0).toFixed(1)}`;
  metricsDiv.setAttribute(
      'data-tooltip',
      'AI Confidence & Impact Scores: Calculated via rigorous LLM evaluation of source authority, factuality, recency (temporal weighting), and trend relevance.'
  );
  metadata.appendChild(metricsDiv);

  // Actions
  const actions = document.createElement('div');
  actions.className = 'flex items-center gap-2';
  
  if (context === 'feed') {
    actions.innerHTML = `
      <a href="${escapeHtml(signal.url)}" target="_blank" rel="noopener noreferrer" 
         class="flex-1 px-4 py-2 bg-nesta-blue text-white text-center font-bold text-sm uppercase tracking-wider rounded-lg hover:bg-nesta-navy transition-colours">
        Open Source
      </a>
    `;
  } else if (context === 'database') {
    actions.innerHTML = `
      <button class="btn-view flex-1 px-4 py-2 bg-nesta-green text-white font-bold text-sm uppercase tracking-wider rounded-lg hover:bg-nesta-navy transition-colours">
        View
      </button>
      <a href="${escapeHtml(signal.url)}" target="_blank" rel="noopener noreferrer" 
         class="px-4 py-2 bg-nesta-blue text-white font-bold text-sm uppercase tracking-wider rounded-lg hover:bg-nesta-navy transition-colours">
        →
      </a>
    `;
  }

  // Assemble card
  card.appendChild(header);
  card.appendChild(summaryWrap);
  card.appendChild(metadata);
  if (actions.innerHTML.trim()) {
    card.appendChild(actions);
  }

  // Add animation
  card.classList.add('card-enter');

  return card;
}

/**
 * Render signals to a container
 */
export function renderSignals(signals, container, topic = '', groupBy = null) {
  if (!container) return;

  container.innerHTML = '';

  if (signals.length === 0) {
    const emptyState = document.getElementById('empty-state');
    if (emptyState) emptyState.classList.remove('hidden');
    return;
  }

  const emptyState = document.getElementById('empty-state');
  if (emptyState) emptyState.classList.add('hidden');

  // Group signals if requested
  if (groupBy && groupBy !== 'none') {
    const groups = {};
    signals.forEach(signal => {
      const key = signal[groupBy] || 'Other';
      if (!groups[key]) groups[key] = [];
      groups[key].push(signal);
    });

    // Render groups
    Object.entries(groups).forEach(([groupName, groupSignals]) => {
      const groupHeader = document.createElement('div');
      groupHeader.className = 'col-span-full mb-4';
      groupHeader.innerHTML = `
        <h3 class="font-display text-2xl font-bold text-nesta-navy border-b-4 border-nesta-blue pb-2">
          ${escapeHtml(groupName)}
          <span class="text-lg text-nesta-dark-grey ml-2">(${groupSignals.length})</span>
        </h3>
      `;
      container.appendChild(groupHeader);

      groupSignals.forEach(signal => {
        const card = createSignalCard(signal, container.id === 'database-grid' ? 'database' : 'feed');
        container.appendChild(card);
      });
    });
  } else {
    // Render flat list
    signals.forEach((signal, index) => {
      const card = createSignalCard(signal, container.id === 'database-grid' ? 'database' : 'feed');
      // Stagger animation
      card.style.animationDelay = `${index * 0.05}s`;
      container.appendChild(card);
    });
  }
}

/**
 * Append log to console
 */
export function appendConsoleLog(message, type = 'info') {
  const console = document.getElementById('console');
  if (!console) return;

  const consoleContainer = document.getElementById('console-container');
  if (consoleContainer) consoleContainer.classList.remove('hidden');

  const entry = document.createElement('div');
  entry.className = `log-entry ${type === 'error' ? 'log-entry-error' : ''}`;

  const icon = type === 'success' ? '✓' : 
               type === 'error' ? '✗' : 
               type === 'warning' ? '⚠' : 
               'ℹ';

  entry.innerHTML = `
    <span class="font-bold text-lg">${icon}</span>
    <span class="flex-1">${escapeHtml(message)}</span>
  `;

  console.appendChild(entry);
  console.scrollTop = console.scrollHeight;
}

/**
 * Clear console
 */
export function clearConsole() {
  const console = document.getElementById('console');
  if (console) console.innerHTML = '';
}

/**
 * Show toast notification
 */
export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `modern-toast ${type === 'error' ? 'error' : ''}`;
  
  const icon = type === 'success' ? '✓' : 
               type === 'error' ? '✗' : 
               'ℹ';

  toast.innerHTML = `
    <div class="flex items-center gap-3">
      <span class="text-2xl">${icon}</span>
      <span class="flex-1 font-body">${escapeHtml(message)}</span>
    </div>
  `;

  container.appendChild(toast);

  // Auto-remove after 4 seconds
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/**
 * Start scan UI state
 */
export function startScan() {
  const scanBtn = document.getElementById('scan-btn');
  const scanBtnText = document.getElementById('scan-btn-text');
  const scanBtnLoader = document.getElementById('scan-btn-loader');
  const controlBar = document.getElementById('control-bar');

  if (scanBtn) scanBtn.disabled = true;
  if (scanBtnText) scanBtnText.classList.add('hidden');
  if (scanBtnLoader) scanBtnLoader.classList.remove('hidden');
  if (controlBar) controlBar.classList.add('hidden');

  state.isScanning = true;
}

/**
 * Finish scan UI state
 */
export function finishScan() {
  const scanBtn = document.getElementById('scan-btn');
  const scanBtnText = document.getElementById('scan-btn-text');
  const scanBtnLoader = document.getElementById('scan-btn-loader');
  const controlBar = document.getElementById('control-bar');

  if (scanBtn) scanBtn.disabled = false;
  if (scanBtnText) scanBtnText.classList.remove('hidden');
  if (scanBtnLoader) scanBtnLoader.classList.add('hidden');
  if (controlBar) controlBar.classList.remove('hidden');

  state.isScanning = false;
}

/**
 * Update mode title and description
 */
export function updateModeUI(mode) {
  const modeTitle = document.getElementById('mode-title');
  const modeDescription = document.getElementById('mode-description');

  const config = {
    radar: {
      title: 'Radar Scanning',
      description: 'Discover emerging signals at the innovation frontier',
    },
    research: {
      title: 'Research Synthesis',
      description: 'Deep-dive analysis combining multiple sources into comprehensive insights',
    },
    governance: {
      title: 'Regulatory Horizon',
      description: 'Targeted search across global government and policy sources',
    },
  };

  const { title, description } = config[mode] || config.radar;
  if (modeTitle) modeTitle.textContent = title;
  if (modeDescription) modeDescription.textContent = description;
}

/**
 * Create action footer with icon buttons
 */
function createActionFooter(signal) {
  const footer = document.createElement('div');
  footer.className = 'action-footer';
  
  footer.innerHTML = `
    <button class="action-btn" data-action="star" data-url="${signal.url}" title="Star this signal">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
      </svg>
    </button>
    <button class="action-btn" data-action="archive" data-url="${signal.url}" title="Archive signal">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path>
      </svg>
    </button>
    <button class="action-btn" data-action="view" data-url="${signal.url}" title="View details">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
      </svg>
    </button>
  `;
  
  return footer;
}

/**
 * Create SVG sparkline for activity trend
 */
function createSparkline(signal) {
  const container = document.createElement('div');
  container.className = 'sparkline-container';
  
  const baseValue = signal.score_activity || 5;
  const points = [];
  for (let i = 0; i < 10; i++) {
    points.push(baseValue + Math.random() * 3 - 1.5);
  }
  
  const max = Math.max(...points);
  const min = Math.min(...points);
  const range = max - min || 1;
  
  const width = 200;
  const height = 40;
  const pathData = points.map((point, i) => {
    const x = (i / (points.length - 1)) * width;
    const y = height - ((point - min) / range) * height;
    return `${i === 0 ? 'M' : 'L'} ${x} ${y}`;
  }).join(' ');
  
  container.innerHTML = `
    <svg width="100%" height="40" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">
      <defs>
        <linearGradient id="sparklineGradient-${Date.now()}" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:#0000FF;stop-opacity:0.2" />
          <stop offset="100%" style="stop-color:#0000FF;stop-opacity:0" />
        </linearGradient>
      </defs>
      <path d="${pathData}" class="sparkline-path" />
      <path d="${pathData} L ${width} ${height} L 0 ${height} Z" class="sparkline-area" fill="url(#sparklineGradient-${Date.now()})" />
    </svg>
  `;
  
  return container;
}

/**
 * Create synthesis card with gradient background
 */
export function renderSynthesis(synthesisData, container) {
  if (!container || !synthesisData) return;
  
  const card = document.createElement('article');
  card.className = 'synthesis-card p-8 mb-6';
  
  card.innerHTML = `
    <div class="flex items-center gap-3 mb-4">
      <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
      </svg>
      <h2 class="text-2xl font-display font-bold">AI Synthesis</h2>
    </div>
    <p class="text-lg text-white/90 leading-relaxed typewriter-text" style="white-space: normal;">
      ${synthesisData.synthesis || 'Analyzing signals...'}
    </p>
    ${synthesisData.signals && synthesisData.signals.length > 0 ? `
      <div class="mt-6 space-y-2">
        <h3 class="text-sm font-bold text-white/70 uppercase tracking-wider">Key Signals:</h3>
        ${synthesisData.signals.map((sig, i) => `
          <div class="flex items-start gap-2 text-white/80">
            <span class="text-white font-bold">${i + 1}.</span>
            <span>${sig}</span>
          </div>
        `).join('')}
      </div>
    ` : ''}
  `;
  
  container.insertBefore(card, container.firstChild);
}

/**
 * Render theme chips for signal clustering
 */
export function renderThemeChips(themes, container, onFilterChange) {
  if (!container || !themes || themes.length === 0) {
    if (container) container.innerHTML = '';
    return;
  }
  
  // Create chip container
  const chipsWrapper = document.createElement('div');
  chipsWrapper.className = 'theme-chips-container flex flex-wrap items-center gap-3 p-4 bg-white rounded-lg shadow-sm mb-6';
  chipsWrapper.innerHTML = '<span class="text-sm font-bold text-nesta-navy uppercase tracking-wider mr-2">Themes:</span>';
  
  // Add "All" chip
  const allChip = document.createElement('button');
  allChip.className = 'theme-chip active';
  allChip.dataset.themeId = 'all';
  allChip.innerHTML = `<span class="font-bold">All</span> <span class="ml-1 opacity-75">(${getTotalSignalCount(themes)})</span>`;
  allChip.addEventListener('click', () => selectThemeChip(allChip, null, onFilterChange));
  chipsWrapper.appendChild(allChip);
  
  // Add theme chips
  themes.forEach((theme, index) => {
    const chip = document.createElement('button');
    chip.className = 'theme-chip';
    chip.dataset.themeId = index;
    chip.innerHTML = `
      <span class="font-bold">${escapeHtml(theme.name)}</span>
      <span class="ml-1 opacity-75">(${theme.signal_ids ? theme.signal_ids.length : 0})</span>
    `;
    chip.title = theme.description || '';
    chip.addEventListener('click', () => selectThemeChip(chip, theme, onFilterChange));
    chipsWrapper.appendChild(chip);
  });
  
  container.innerHTML = '';
  container.appendChild(chipsWrapper);
}

/**
 * Select a theme chip and trigger filtering
 */
function selectThemeChip(clickedChip, theme, onFilterChange) {
  // Remove active class from all chips
  document.querySelectorAll('.theme-chip').forEach(chip => {
    chip.classList.remove('active');
  });
  
  // Add active to clicked chip
  clickedChip.classList.add('active');
  
  // Update URL parameter
  const url = new URL(window.location);
  if (theme) {
    url.searchParams.set('theme', theme.name.toLowerCase().replace(/\s+/g, '-'));
  } else {
    url.searchParams.delete('theme');
  }
  window.history.pushState({}, '', url);
  
  // Trigger filter callback
  if (typeof onFilterChange === 'function') {
    onFilterChange(theme);
  }
}

/**
 * Get total count of signals across all themes
 */
function getTotalSignalCount(themes) {
  const uniqueIds = new Set();
  themes.forEach(theme => {
    if (theme.signal_ids) {
      theme.signal_ids.forEach(id => uniqueIds.add(id));
    }
  });
  return uniqueIds.size;
}

/**
 * Filter signals by theme
 */
export function filterSignalsByTheme(signals, theme) {
  if (!theme || !theme.signal_ids) {
    // Show all signals
    return signals;
  }
  
  // Filter to only signals in this theme
  return signals.filter((signal, index) => {
    return theme.signal_ids.includes(index);
  });
}

/**
 * Sanitize a URL to only allow safe schemes (http, https, mailto).
 */
function sanitizeUrl(url) {
  if (!url) return "#";
  const cleaned = String(url).trim();
  if (/^https?:\/\//i.test(cleaned) || /^mailto:/i.test(cleaned)) {
    return cleaned;
  }
  return "#";
}

/**
 * Render a single research / deep-dive result card.
 */
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
                    ${marked.parse(researchData.Analysis || researchData.Description || "No analysis provided.")}
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
                <a href="${sanitizeUrl(researchData.URL || "")}" target="_blank"
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
