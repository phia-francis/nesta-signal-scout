/**
 * UI rendering and manipulation
 * Handles all DOM updates and visual feedback
 */

import { state } from './state.js';

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
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
  const summary = document.createElement('p');
  summary.className = 'text-nesta-dark-grey leading-relaxed line-clamp-4';
  summary.textContent = signal.summary || 'No description available.';

  // Metadata bar
  const metadata = document.createElement('div');
  metadata.className = 'flex items-center justify-between text-sm text-nesta-dark-grey border-t border-nesta-silver pt-4';
  metadata.innerHTML = `
    <div class="flex items-center gap-4">
      <div class="flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
        </svg>
        <span class="font-bold">${(signal.score_activity || 0).toFixed(1)}</span>
      </div>
      <div class="flex items-center gap-1">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        <span class="font-bold">${(signal.score_attention || 0).toFixed(1)}</span>
      </div>
    </div>
    <div class="text-xs">
      <span>${formatDate(signal.date)}</span>
      ${signal.mission ? `<span class="ml-2 text-nesta-blue font-bold">${escapeHtml(signal.mission)}</span>` : ''}
    </div>
  `;

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
  card.appendChild(summary);
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
    policy: {
      title: 'Policy Scanning',
      description: 'Targeted search across global government and policy sources',
    },
  };

  const { title, description } = config[mode] || config.radar;
  if (modeTitle) modeTitle.textContent = title;
  if (modeDescription) modeDescription.textContent = description;
}
