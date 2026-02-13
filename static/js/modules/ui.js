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

export function createSignalCard(signal) {
  const mission = signal.mission || 'General';
  const theme = getThemeForMission(mission);
  const source = signal.source || 'Google Search';

  const card = document.createElement('article');
  card.className = `signal-card bg-white border-2 ${theme.border} shadow-hard rounded-sm p-6 flex flex-col gap-4 relative`;

  const sourceBadge = document.createElement('span');
  sourceBadge.className = `absolute top-4 right-4 rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${getSourceBadgeTheme(source)}`;
  sourceBadge.textContent = source;

  const missionPill = document.createElement('span');
  missionPill.className = `rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider ${theme.bg} ${theme.text}`;
  missionPill.textContent = mission;

  if (signal.is_novel) {
    const noveltyPill = document.createElement('span');
    noveltyPill.className = 'rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wider bg-nesta-teal/15 text-nesta-navy border border-nesta-teal/40';
    noveltyPill.textContent = 'New';
    card.appendChild(noveltyPill);
  }

  const title = document.createElement('h3');
  title.className = 'font-display text-xl leading-tight text-nesta-navy mb-2';
  title.textContent = signal.title || 'Untitled Signal';

  const summary = document.createElement('p');
  summary.className = 'font-body text-sm text-nesta-navy/80 line-clamp-4';
  summary.textContent = signal.summary || '';

  const footer = document.createElement('footer');
  footer.className = 'mt-auto pt-3 border-t border-nesta-sand/50 flex items-center justify-between gap-3';

  const metricsWrap = document.createElement('div');
  metricsWrap.className = 'flex flex-col gap-1';

  const metrics = document.createElement('div');
  metrics.className = 'text-xs text-nesta-navy/70';
  metrics.textContent = `Activity ${Number(signal.score_activity || 0).toFixed(1)} • Attention ${Number(signal.score_attention || 0).toFixed(1)}`;
  metricsWrap.appendChild(metrics);

  if (signal.narrative_group) {
    const narrativeBadge = document.createElement('span');
    narrativeBadge.className = 'inline-flex w-fit rounded-full px-2 py-0.5 text-[11px] font-semibold bg-nesta-purple/10 text-nesta-purple';
    narrativeBadge.textContent = signal.narrative_group;
    metricsWrap.appendChild(narrativeBadge);
  }

  const copyButton = document.createElement('button');
  copyButton.type = 'button';
  copyButton.className = 'text-nesta-navy/50 hover:text-nesta-blue transition-colors inline-flex items-center gap-1';
  copyButton.title = 'Copy to Clipboard';
  copyButton.innerHTML = `${clipboardIcon()}<span class="sr-only">Copy signal</span>`;
  copyButton.addEventListener('click', async () => {
    const payload = `${signal.title || 'Untitled Signal'} - ${signal.summary || ''} - ${signal.url || ''}`;
    try {
      await navigator.clipboard.writeText(payload);
      showToast('Signal copied to clipboard.', 'success');
    } catch {
      showToast('Unable to copy signal.', 'error');
    }
  });

  footer.append(metricsWrap, copyButton);

  if (signal.url) {
    title.classList.add('cursor-pointer', 'hover:text-nesta-blue', 'transition-colors');
    title.addEventListener('click', () => {
      try {
        const parsedUrl = new URL(signal.url, window.location.origin);
        if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
          window.open(parsedUrl.href, '_blank', 'noopener,noreferrer');
        }
      } catch {
        // Ignore malformed URL while preserving UI rendering.
      }
    });
  }

  card.append(sourceBadge, missionPill, title, summary, footer);
  return card;
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
  const intelligencePlaceholder = document.getElementById('intelligence-placeholder');
  loader?.classList.remove('hidden');
  feed?.classList.add('hidden');
  emptyState?.classList.add('hidden');
  intelligencePlaceholder?.classList.add('hidden');
}

export function finishScan() {
  const loader = document.getElementById('scan-loader');
  const feed = document.getElementById('radar-feed');
  const emptyState = document.getElementById('empty-state');
  const intelligencePlaceholder = document.getElementById('intelligence-placeholder');
  loader?.classList.add('hidden');
  feed?.classList.remove('hidden');
  emptyState?.classList.add('hidden');
  intelligencePlaceholder?.classList.add('hidden');
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

export { MISSION_THEMES };
