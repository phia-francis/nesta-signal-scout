function getTypologyTooltip(type) {
  const definitions = {
    'Hidden Gem': 'High investment activity but low public attention. A prime innovation opportunity.',
    Hype: 'High public attention but lower underlying activity. Validate before action.',
    Established: 'High activity and high attention. A mature and visible signal area.',
    Nascent: 'Low activity and low attention. Early stage signal worth monitoring.',
    Evidence: 'Research-led signal with stronger evidence than market activity.',
  };
  return definitions[type] || 'Signal classification based on activity versus attention.';
}

function missionTheme(mission) {
  const themes = {
    'A Sustainable Future': { bg: 'bg-nesta-green', text: 'text-white' },
    'A Healthy Life': { bg: 'bg-nesta-pink', text: 'text-nesta-navy' },
    'A Fairer Start': { bg: 'bg-nesta-yellow', text: 'text-nesta-navy' },
    General: { bg: 'bg-nesta-blue', text: 'text-white' },
  };
  return themes[mission] || themes.General;
}

function buildSparkline(dataPoints) {
  const points = Array.isArray(dataPoints) && dataPoints.length ? dataPoints : [3, 4, 4, 5, 6, 5, 7, 8];
  const width = 100;
  const height = 28;
  const maxValue = Math.max(...points);
  const minValue = Math.min(...points);
  const range = maxValue - minValue || 1;

  const polyline = points
    .map((value, index) => {
      const x = (index / Math.max(points.length - 1, 1)) * width;
      const y = height - ((value - minValue) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  return `
    <svg viewBox="0 0 ${width} ${height}" class="w-full h-8" aria-label="Signal trendline">
      <polyline points="${polyline}" fill="none" stroke="#0000FF" stroke-width="2" vector-effect="non-scaling-stroke"></polyline>
    </svg>
  `;
}

export function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const palette = {
    success: 'bg-nesta-green border-nesta-green text-white',
    error: 'bg-nesta-red border-nesta-red text-white',
    info: 'bg-nesta-navy border-nesta-navy text-white',
  };

  const toast = document.createElement('div');
  toast.className = `pointer-events-auto max-w-sm w-full shadow-hard border-l-8 p-4 flex items-center gap-3 ${palette[type] || palette.info}`;
  toast.innerHTML = `<div class="font-bold text-sm tracking-wide">${message}</div>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}

export function renderSignals(signals, container) {
  if (!container) return;
  container.innerHTML = '';

  signals.forEach((signal) => {
    const card = document.createElement('article');
    const mission = signal.mission || 'General';
    const typology = signal.typology || 'Nascent';
    const theme = missionTheme(mission);
    const activity = Number(signal.score_activity || 0);
    const attention = Number(signal.score_attention || 0);

    card.className = 'signal-card card-enter bg-white p-6 flex flex-col gap-4 relative overflow-hidden group border border-slate-100';

    const pulseMarkup = signal.is_new
      ? '<div class="pulse-badge"><div class="pulse-dot"></div>NEW</div>'
      : '';

    card.innerHTML = `
      ${pulseMarkup}
      <header class="flex justify-between items-start gap-2">
        <span class="${theme.bg} ${theme.text} text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-sm shadow-sm">${mission}</span>
        <span class="text-nesta-navy border border-slate-200 text-[10px] font-bold uppercase tracking-widest px-2 py-1 bg-slate-50 cursor-help" data-tooltip="${getTypologyTooltip(typology)}">${typology}</span>
      </header>

      <h3 class="font-display text-xl font-bold leading-tight text-nesta-navy group-hover:text-nesta-blue transition-colors cursor-pointer" data-role="signal-title">${signal.title || 'Untitled Signal'}</h3>

      <p class="text-sm text-nesta-dark-grey leading-relaxed line-clamp-3">${signal.summary || ''}</p>

      <section class="grid grid-cols-2 gap-4 border-t border-slate-100 pt-4">
        <div class="space-y-2">
          <div class="flex justify-between text-[10px] font-bold text-nesta-navy uppercase" data-tooltip="Based on funding and investment activity.">
            <span class="border-b border-dotted border-slate-300 cursor-help">Activity</span>
            <span>${activity.toFixed(1)}</span>
          </div>
          <div class="meter-container w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div class="meter-fill bg-nesta-blue h-2" style="width: ${Math.max(0, Math.min(100, activity * 10))}%"></div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="flex justify-between text-[10px] font-bold text-nesta-navy uppercase" data-tooltip="Based on mainstream versus niche attention.">
            <span class="border-b border-dotted border-slate-300 cursor-help">Attention</span>
            <span>${attention.toFixed(1)}</span>
          </div>
          <div class="meter-container w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div class="meter-fill bg-nesta-pink h-2" style="width: ${Math.max(0, Math.min(100, attention * 10))}%"></div>
          </div>
        </div>
      </section>

      <div class="pt-1" data-tooltip="Indicative trend based on score relationship.">
        ${buildSparkline(signal.sparkline)}
      </div>
    `;

    const titleNode = card.querySelector('[data-role="signal-title"]');
    titleNode?.addEventListener('click', () => {
      try {
        const parsedUrl = new URL(signal.url || '', window.location.origin);
        if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
          window.open(parsedUrl.href, '_blank');
        }
      } catch (error) {
        // Intentionally ignore malformed URLs to preserve rendering flow.
      }
    });

    container.appendChild(card);
  });
}
