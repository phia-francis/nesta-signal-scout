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

  const footer = document.createElement('footer');
  footer.className = 'mt-auto pt-3 border-t border-nesta-sand/50 flex items-center justify-between gap-3';

  const metricsWrap = document.createElement('div');
  metricsWrap.className = 'flex flex-col gap-1';

  const metrics = document.createElement('div');
  metrics.className = 'text-xs text-nesta-navy/70 cursor-help inline-block w-fit';
  metrics.textContent = `Activity ${Number(signal.score_activity || 0).toFixed(1)} • Attention ${Number(signal.score_attention || 0).toFixed(1)} • AI Confidence ${Number(signal.score_confidence || signal.final_score || 0).toFixed(1)}`;
  metrics.setAttribute(
      'data-tooltip',
      'AI Confidence & Impact Scores: Calculated via rigorous LLM evaluation of source authority, factuality, recency (temporal weighting), and trend relevance.'
  );
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

  card.append(sourceBadge, missionPill, title, summaryWrap, footer);
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

export { MISSION_THEMES };
