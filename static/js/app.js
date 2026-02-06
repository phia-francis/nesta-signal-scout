const API_BASE_URL = window.location.origin;

const state = {
  activeTab: 'research',
  databaseItems: [],
  tutorialIndex: 0,
  radarChart: null,
  radarSignals: [],
  lastResearch: null,
  lastRadar: null,
  radarPreviewLoaded: false,
};

const missionColors = {
  'A Fairer Start': '#9B59B6',
  'A Healthy Life': '#F6A4B7',
  'A Sustainable Future': '#18A48C',
  Default: '#0F294A',
};

const tabs = {
  research: document.getElementById('view-research'),
  radar: document.getElementById('view-radar'),
  database: document.getElementById('view-database'),
  policy: document.getElementById('view-policy'),
};

const tabButtons = {
  research: document.getElementById('tab-research'),
  radar: document.getElementById('tab-radar'),
  database: document.getElementById('tab-database'),
  policy: document.getElementById('tab-policy'),
};

const researchStatus = document.getElementById('research-status');
const radarStatus = document.getElementById('radar-status');
const researchFeed = document.getElementById('research-feed');
const radarFeed = document.getElementById('radar-feed');
const databaseGrid = document.getElementById('database-grid');
const policyFeed = document.getElementById('policy-feed');
const policyStatus = document.getElementById('policy-status');

const researchButton = document.getElementById('research-submit');
const radarButton = document.getElementById('radar-submit');
const policyButton = document.getElementById('policy-submit');

const databaseMission = document.getElementById('database-mission');
const databaseType = document.getElementById('database-type');
const policyMission = document.getElementById('policy-mission');
const policyTopic = document.getElementById('policy-topic');

const userGuide = document.getElementById('user-guide');
const openGuideButton = document.getElementById('open-guide');
const closeGuideButton = document.getElementById('close-guide');

const welcomeModal = document.getElementById('welcome-modal');
const welcomeStart = document.getElementById('welcome-start');
const welcomeTutorial = document.getElementById('welcome-tutorial');
const welcomeSkip = document.getElementById('welcome-skip');

const tutorialSpotlight = document.getElementById('tutorial-spotlight');
const tutorialTooltip = document.getElementById('tutorial-tooltip');
const tutorialText = document.getElementById('tutorial-text');
const tutorialSkip = document.getElementById('tutorial-skip');
const tutorialNext = document.getElementById('tutorial-next');
const perspectiveButton = document.getElementById('btn-perspective');
const radarPerspectiveSlot = document.getElementById('radar-perspective-slot');
const processStepper = document.getElementById('process-stepper');
const stepElements = {
  searching: document.getElementById('step-1'),
  classifying: document.getElementById('step-2'),
  synthesizing: document.getElementById('step-3'),
};
const radarChartWrapper = document.getElementById('radar-chart-wrapper');

const tutorialSteps = [
  {
    id: 'tab-research',
    text: 'Start with Targeted Research to answer a specific question using deep synthesis.',
    action: () => setTab('research'),
  },
  {
    id: 'tab-radar',
    text: 'Use Mission Radar to scan for broad signals tied to a mission.',
    action: () => setTab('radar'),
  },
  {
    id: 'tab-database',
    text: 'Visit the Database to curate saved signals and keep the best ones.',
    action: () => setTab('database'),
  },
  {
    id: 'open-guide',
    text: 'Open the guide anytime for quick help.',
    action: () => {},
  },
];

function initRadarChart() {
  const ctx = document.getElementById('radar-chart');
  if (!ctx) return;
  if (state.radarChart) {
    state.radarChart.destroy();
  }
  const quadrantPlugin = {
    id: 'quadrantPlugin',
    beforeDraw(chart) {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;
      const midX = (chartArea.left + chartArea.right) / 2;
      const midY = (chartArea.top + chartArea.bottom) / 2;
      ctx.save();
      ctx.strokeStyle = '#CBD5F5';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(midX, chartArea.top);
      ctx.lineTo(midX, chartArea.bottom);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(chartArea.left, midY);
      ctx.lineTo(chartArea.right, midY);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = '#64748B';
      ctx.font = '12px Averta, sans-serif';
      ctx.fillText('HOT', midX + 8, chartArea.top + 16);
      ctx.fillText('EMERGING', chartArea.left + 8, chartArea.top + 16);
      ctx.fillText('STABILISING', midX + 8, chartArea.bottom - 8);
      ctx.fillText('DORMANT', chartArea.left + 8, chartArea.bottom - 8);
      ctx.restore();
    },
  };
  state.radarChart = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Signals',
          data: [],
          pointBackgroundColor: [],
          backgroundColor: 'rgba(15, 41, 74, 0.6)',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: { min: 0, max: 10, title: { display: true, text: 'Growth' } },
        y: { min: 0, max: 10, title: { display: true, text: 'Magnitude' } },
      },
      plugins: {
        legend: { display: false },
      },
    },
    plugins: [quadrantPlugin],
  });
}

function addBlipToRadar(blip) {
  state.radarSignals.push(blip);
  if (!state.radarChart) return;
  const color = missionColors[blip.mission] || missionColors.Default;
  state.radarChart.data.datasets[0].data.push({
    x: blip.growth_metric ?? blip.score_novelty,
    y: blip.magnitude_metric ?? blip.score_impact,
  });
  const dataset = state.radarChart.data.datasets[0];
  if (!dataset.pointBackgroundColor) {
    dataset.pointBackgroundColor = [];
  }
  dataset.pointBackgroundColor.push(color);
  state.radarChart.update();
}

function setTab(tab) {
  state.activeTab = tab;
  Object.keys(tabs).forEach((key) => {
    tabs[key].classList.toggle('hidden', key !== tab);
    tabButtons[key].classList.toggle('active', key === tab);
  });
  if (tab === 'database') {
    loadDatabase();
  }
  if (tab === 'radar' && radarPerspectiveSlot && perspectiveButton) {
    radarPerspectiveSlot.appendChild(perspectiveButton);
  }
  if (tab === 'research' && perspectiveButton) {
    const researchSlot = document.querySelector('#view-research .flex.items-center.justify-end');
    if (researchSlot) {
      researchSlot.appendChild(perspectiveButton);
    }
  }
  if (tab === 'radar' && !state.radarChart) {
    initRadarChart();
  }
  if (tab === 'radar' && !state.radarPreviewLoaded) {
    loadRadarPreview();
  }
  if (tab === 'policy') {
    policyStatus.textContent = '';
  }
}

tabButtons.research.addEventListener('click', () => setTab('research'));
tabButtons.radar.addEventListener('click', () => setTab('radar'));
tabButtons.database.addEventListener('click', () => setTab('database'));
tabButtons.policy.addEventListener('click', () => setTab('policy'));

openGuideButton.addEventListener('click', () => {
  userGuide.classList.remove('hidden');
  userGuide.classList.add('flex');
});

closeGuideButton.addEventListener('click', () => {
  userGuide.classList.add('hidden');
  userGuide.classList.remove('flex');
});

userGuide.addEventListener('click', (event) => {
  if (event.target === userGuide) {
    userGuide.classList.add('hidden');
    userGuide.classList.remove('flex');
  }
});

function setButtonLoading(button, isLoading) {
  button.disabled = isLoading;
  button.classList.toggle('opacity-70', isLoading);
  const label = button.querySelector('.btn-label');
  const spinner = button.querySelector('.btn-spinner');
  if (button.dataset.spinner === 'false') {
    return;
  }
  if (label && spinner) {
    label.classList.toggle('hidden', isLoading);
    spinner.classList.toggle('hidden', !isLoading);
  }
}

function resetProcessStepper() {
  if (!processStepper) return;
  processStepper.classList.remove('hidden');
  Object.values(stepElements).forEach((step) => {
    if (!step) return;
    step.classList.add('opacity-50');
    step.classList.remove('opacity-100');
    const indicator = step.querySelector('.step-indicator');
    if (indicator) {
      indicator.classList.remove('active', 'complete');
    }
  });
}

function markStep(status, isComplete) {
  const step = stepElements[status];
  if (!step) return;
  step.classList.remove('opacity-50');
  step.classList.add('opacity-100');
  const indicator = step.querySelector('.step-indicator');
  if (!indicator) return;
  indicator.classList.remove('active');
  if (isComplete) {
    indicator.classList.add('complete');
  } else {
    indicator.classList.add('active');
  }
}

function updateProcessStepper(status) {
  if (!processStepper) return;
  if (status === 'searching') {
    markStep('searching', false);
  }
  if (status === 'classifying') {
    markStep('searching', true);
    markStep('classifying', false);
  }
  if (status === 'synthesizing') {
    markStep('classifying', true);
    markStep('synthesizing', false);
  }
  if (status === 'complete') {
    markStep('synthesizing', true);
  }
}

function formatSources(sources) {
  return sources
    .map((source) => `<li class="text-sm text-nesta-blue"><a href="${source}" target="_blank" rel="noopener">${source}</a></li>`)
    .join('');
}

async function updateSignal(url, status, card) {
  if (!url) return;
  await fetch(`${API_BASE_URL}/api/update_signal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, status }),
  });
  if (status === 'Saved') {
    card.classList.add('border-green-300');
  }
  if (status === 'Rejected') {
    card.classList.add('opacity-50');
  }
}

async function sendFeedback(signalId, relevant) {
  if (!signalId) return;
  await fetch(`${API_BASE_URL}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signal_id: signalId, relevant }),
  });
}

function renderSparkline(canvas) {
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const values = Array.from({ length: 8 }, () => Math.random() * 10 + 2);
  const maxVal = Math.max(...values);
  const minVal = Math.min(...values);
  const w = canvas.width;
  const h = canvas.height;
  const points = values.map((val, idx) => ({
    x: (idx / (values.length - 1)) * w,
    y: h - ((val - minVal) / (maxVal - minVal || 1)) * h,
  }));
  const duration = 1000;
  const pointDelay = 100;
  const totalDuration = duration + pointDelay * (points.length - 1);
  const startTime = performance.now();

  function drawFrame(now) {
    const elapsed = now - startTime;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = '#0F294A';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 0; i < points.length - 1; i += 1) {
      const segmentStart = i * pointDelay;
      const segmentProgress = Math.min(Math.max((elapsed - segmentStart) / duration, 0), 1);
      const nextX = points[i].x + (points[i + 1].x - points[i].x) * segmentProgress;
      const nextY = points[i].y + (points[i + 1].y - points[i].y) * segmentProgress;
      ctx.lineTo(nextX, nextY);
      if (segmentProgress < 1) {
        break;
      }
    }
    ctx.stroke();
    if (elapsed < totalDuration) {
      requestAnimationFrame(drawFrame);
    }
  }

  requestAnimationFrame(drawFrame);
}

function createActionBar({ url, card }) {
  const wrapper = document.createElement('div');
  wrapper.className = 'mt-4 flex flex-wrap items-center gap-2';

  const keepButton = document.createElement('button');
  keepButton.className = 'btn-secondary border-green-200 text-green-700 hover:border-green-400 hover:text-green-700';
  keepButton.textContent = 'Keep';

  const discardButton = document.createElement('button');
  discardButton.className = 'btn-secondary border-red-200 text-red-600 hover:border-red-400 hover:text-red-600';
  discardButton.textContent = 'Discard';

  keepButton.addEventListener('click', async () => {
    await updateSignal(url, 'Saved', card);
    keepButton.textContent = 'Saved ✓';
    keepButton.classList.add('bg-green-600', 'text-white', 'border-green-600');
    discardButton.disabled = true;
  });

  discardButton.addEventListener('click', async () => {
    await updateSignal(url, 'Rejected', card);
    discardButton.textContent = 'Discarded';
    discardButton.classList.add('opacity-70');
    keepButton.disabled = true;
  });

  wrapper.appendChild(keepButton);
  wrapper.appendChild(discardButton);
  return wrapper;
}

function renderResearchCard(card, isPerspective = false) {
  const wrapper = document.createElement('article');
  wrapper.className = 'rounded-2xl bg-white p-6 shadow-soft fade-in-up';
  const perspectiveBadge = isPerspective
    ? '<span class="badge-perspective">Perspective Shift</span>'
    : '';
  wrapper.innerHTML = `
    <h3 class="text-xl font-semibold text-nesta-navy brand-font">${card.title}</h3>
    ${perspectiveBadge}
    <p class="mt-3 text-sm text-slate-600">${card.summary}</p>
    <div class="mt-4 space-y-3 text-sm text-slate-700">
      <div>
        <h4 class="font-semibold text-nesta-navy">Analysis</h4>
        <p>${card.analysis}</p>
      </div>
      <div>
        <h4 class="font-semibold text-nesta-navy">Implications</h4>
        <p>${card.implications}</p>
      </div>
      <div>
        <h4 class="font-semibold text-nesta-navy">Evidence Base</h4>
        <ul class="list-disc pl-5">${formatSources(card.sources)}</ul>
      </div>
    </div>
    <div class="mt-4 flex items-center justify-between text-xs text-slate-500">
      <span>Typology: Research</span>
      <canvas class="sparkline" width="120" height="32"></canvas>
    </div>
    <div class="mt-2 flex items-center gap-2 text-xs">
      <button class="btn-secondary" data-feedback="up">👍 Relevant</button>
      <button class="btn-secondary" data-feedback="down">👎 Not Relevant</button>
    </div>
  `;

  const actionBar = createActionBar({ url: card.sources?.[0], card: wrapper });
  wrapper.appendChild(actionBar);
  renderSparkline(wrapper.querySelector('.sparkline'));
  const feedbackButtons = wrapper.querySelectorAll('[data-feedback]');
  feedbackButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      sendFeedback(card.sources?.[0] || card.title, btn.dataset.feedback === 'up');
    });
  });
  researchFeed.prepend(wrapper);
}

function renderBlip(blip, isPerspective = false, isArchive = false) {
  const wrapper = document.createElement('article');
  wrapper.className = `rounded-xl border ${isArchive ? 'border-dashed border-slate-300' : 'border-slate-100'} bg-slate-50 p-4 fade-in-up`;
  const perspectiveBadge = isPerspective
    ? '<span class="badge-perspective">Perspective Shift</span>'
    : '';
  const archiveBadge = isArchive
    ? '<span class="inline-flex rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-500">Archive</span>'
    : '';
  wrapper.innerHTML = `
    <h4 class="font-semibold text-nesta-navy">${blip.title}</h4>
    ${perspectiveBadge}
    ${archiveBadge}
    <p class="mt-2 text-sm text-slate-600">${blip.hook}</p>
    <div class="mt-3 flex items-center justify-between text-xs text-slate-500">
      <span>Novelty: ${blip.score_novelty}/10</span>
      <span>Impact: ${blip.score_impact}/10</span>
    </div>
    <div class="mt-2 text-xs text-slate-500">
      <span>Typology: ${blip.typology || 'EMERGING'}</span>
      <span class="ml-3">Growth: ${blip.growth_metric ?? blip.score_novelty}</span>
      <span class="ml-3">Magnitude: ${blip.magnitude_metric ?? blip.score_impact}</span>
    </div>
    <div class="mt-2 flex items-center justify-between text-xs text-slate-500">
      <canvas class="sparkline" width="120" height="32"></canvas>
      <div class="flex items-center gap-2">
        <button class="btn-secondary" data-feedback="up">👍 Relevant</button>
        <button class="btn-secondary" data-feedback="down">👎 Not Relevant</button>
      </div>
    </div>
    <a class="mt-2 inline-flex text-xs font-semibold text-nesta-blue" href="${blip.url}" target="_blank" rel="noopener">Source →</a>
  `;

  const actionBar = createActionBar({ url: blip.url, card: wrapper });
  wrapper.appendChild(actionBar);
  renderSparkline(wrapper.querySelector('.sparkline'));
  const feedbackButtons = wrapper.querySelectorAll('[data-feedback]');
  feedbackButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      sendFeedback(blip.url || blip.title, btn.dataset.feedback === 'up');
    });
  });
  radarFeed.prepend(wrapper);
}

async function readNdjson(response, onMessage) {
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
      onMessage(JSON.parse(line));
    }
  }
}

async function runResearch({ frictionMode = false, perspective = false } = {}) {
  const query = document.getElementById('research-input').value.trim();
  if (!query) return;
  const timeHorizon = document.getElementById('research-time').value;
  state.lastResearch = { query, timeHorizon };

  researchStatus.textContent = '';
  resetProcessStepper();
  setButtonLoading(researchButton, true);

  try {
    const response = await fetch(`${API_BASE_URL}/api/mode/research`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, time_horizon: timeHorizon, friction_mode: frictionMode }),
    });

    await readNdjson(response, (data) => {
      if (data.status === 'error') {
        researchStatus.textContent = data.msg;
        researchStatus.classList.add('text-red-600');
        return;
      }
      researchStatus.classList.remove('text-red-600');
      if (data.status) {
        updateProcessStepper(data.status);
      }
      if (data.card) {
        renderResearchCard(data.card, perspective);
      }
    });
  } catch (error) {
    researchStatus.textContent = 'Request failed. Please try again.';
    researchStatus.classList.add('text-red-600');
  } finally {
    setButtonLoading(researchButton, false);
    perspectiveButton.classList.remove('hidden');
  }
}

async function runRadar({ frictionMode = false, perspective = false } = {}) {
  const mission = document.getElementById('radar-mission').value;
  const topic = document.getElementById('radar-topic').value.trim();
  state.lastRadar = { mission, topic };

  radarStatus.textContent = 'Starting radar scan...';
  radarStatus.classList.remove('text-red-600');
  radarFeed.innerHTML = '';
  state.radarSignals = [];
  initRadarChart();
  if (radarChartWrapper) {
    radarChartWrapper.classList.add('radar-scan-container');
  }
  setButtonLoading(radarButton, true);

  try {
    const response = await fetch(`${API_BASE_URL}/api/mode/radar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mission, topic: topic || null, friction_mode: frictionMode }),
    });

    await readNdjson(response, (data) => {
      if (data.status === 'error') {
        radarStatus.textContent = data.msg;
        radarStatus.classList.add('text-red-600');
        return;
      }
      radarStatus.classList.remove('text-red-600');
      if (data.msg) {
        radarStatus.textContent = data.msg;
      }
      if (data.blip) {
        renderBlip(data.blip, perspective);
        addBlipToRadar(data.blip);
      }
      if (data.status === 'complete' && radarChartWrapper) {
        radarChartWrapper.classList.remove('radar-scan-container');
      }
    });
  } catch (error) {
    radarStatus.textContent = 'Request failed. Please try again.';
    radarStatus.classList.add('text-red-600');
  } finally {
    if (radarChartWrapper) {
      radarChartWrapper.classList.remove('radar-scan-container');
    }
    setButtonLoading(radarButton, false);
    perspectiveButton.classList.remove('hidden');
  }
}

async function loadRadarPreview() {
  if (!state.radarChart) {
    initRadarChart();
  }
  try {
    const response = await fetch(`${API_BASE_URL}/api/saved`);
    const data = await response.json();
    const signals = (data.signals || [])
      .filter((item) => (item.Type || item.type || '').toLowerCase() !== 'research')
      .slice(-20);
    signals.forEach((item) => {
      const blip = {
        title: item.Title || item.title || 'Signal',
        hook: item.Hook || item.hook || 'No summary available.',
        score_novelty: parseInt(item.Score_Novelty || item.score_novelty || 5, 10),
        score_impact: parseInt(item.Score_Impact || item.score_impact || 5, 10),
        url: item.URL || item.url || '',
        mission: item.Mission || item.mission || 'All Missions',
        typology: item.Typology || item.typology,
        growth_metric: parseFloat(item.Growth_Metric || item.growth_metric || 5),
        magnitude_metric: parseFloat(item.Magnitude_Metric || item.magnitude_metric || 5),
      };
      renderBlip(blip, false, true);
      addBlipToRadar(blip);
    });
    state.radarPreviewLoaded = true;
  } catch (error) {
    state.radarPreviewLoaded = true;
  }
}

function buildDatabaseCard(item) {
  const wrapper = document.createElement('article');
  wrapper.className = 'rounded-2xl bg-white p-5 shadow-soft fade-in-up flex flex-col gap-3';
  const meta = item.type === 'research' ? 'Research Card' : 'Signal';
  const title = item.title || 'Untitled';
  const description = item.summary || item.hook || item.analysis || 'No description available.';
  const mission = item.mission || '—';
  const link = item.url || item.link || '';

  wrapper.innerHTML = `
    <div>
      <p class="text-xs uppercase tracking-widest text-slate-400">${meta}</p>
      <h4 class="text-lg font-semibold text-nesta-navy brand-font">${title}</h4>
    </div>
    <p class="text-sm text-slate-600">${description}</p>
    <div class="text-xs text-slate-500">
      <span>Typology: ${item.typology || 'EMERGING'}</span>
      <span class="ml-3">Growth: ${item.growth_metric ?? item.score_novelty ?? 5}</span>
      <span class="ml-3">Magnitude: ${item.magnitude_metric ?? item.score_impact ?? 5}</span>
    </div>
    <canvas class="sparkline" width="120" height="32"></canvas>
    <div class="flex items-center justify-between text-xs text-slate-500">
      <span>Mission: ${mission}</span>
      ${link ? `<a class="font-semibold text-nesta-blue" href="${link}" target="_blank" rel="noopener">Source →</a>` : ''}
    </div>
    <div class="flex items-center gap-2 text-xs">
      <button class="btn-secondary" data-feedback="up">👍 Relevant</button>
      <button class="btn-secondary" data-feedback="down">👎 Not Relevant</button>
    </div>
  `;

  const actionBar = createActionBar({ url: link, card: wrapper });
  wrapper.appendChild(actionBar);
  renderSparkline(wrapper.querySelector('.sparkline'));
  const feedbackButtons = wrapper.querySelectorAll('[data-feedback]');
  feedbackButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      sendFeedback(link || title, btn.dataset.feedback === 'up');
    });
  });
  return wrapper;
}

function renderDatabase(items) {
  databaseGrid.innerHTML = '';
  if (!items.length) {
    databaseGrid.innerHTML = '<div class="text-sm text-slate-500">No saved items found.</div>';
    return;
  }
  items.forEach((item) => {
    databaseGrid.appendChild(buildDatabaseCard(item));
  });
}

function applyDatabaseFilters(items) {
  const missionFilter = databaseMission.value;
  const typeFilter = databaseType.value;

  return items.filter((item) => {
    const matchesMission = missionFilter === 'all' || item.mission === missionFilter;
    const matchesType = typeFilter === 'all' || item.type === typeFilter;
    return matchesMission && matchesType;
  });
}

function renderDatabaseSkeletons(count = 6) {
  const template = `
    <div class="animate-pulse bg-white p-6 rounded-2xl border border-gray-100">
      <div class="flex justify-between mb-4">
        <div class="h-4 bg-gray-200 rounded w-1/4"></div>
        <div class="h-4 bg-gray-200 rounded w-8"></div>
      </div>
      <div class="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
      <div class="space-y-2">
        <div class="h-3 bg-gray-100 rounded"></div>
        <div class="h-3 bg-gray-100 rounded"></div>
        <div class="h-3 bg-gray-100 rounded w-5/6"></div>
      </div>
      <div class="mt-6 h-32 bg-gray-50 rounded border border-gray-100"></div>
    </div>
  `;
  databaseGrid.innerHTML = Array.from({ length: count }, () => template).join('');
}

async function loadDatabase() {
  renderDatabaseSkeletons();
  try {
    const response = await fetch(`${API_BASE_URL}/api/saved`);
    const data = await response.json();
    const signals = (data.signals || []).map((item) => ({
      type: 'signal',
      title: item.Title || item.title,
      hook: item.Hook || item.hook,
      mission: item.Mission || item.mission,
      url: item.URL || item.url,
      typology: item.Typology || item.typology,
      growth_metric: item.Growth_Metric || item.growth_metric,
      magnitude_metric: item.Magnitude_Metric || item.magnitude_metric,
    }));
    state.databaseItems = signals;
    const filtered = applyDatabaseFilters(state.databaseItems);
    renderDatabase(filtered);
  } catch (error) {
    databaseGrid.innerHTML = '<div class="text-sm text-red-600">Failed to load database.</div>';
  }
}

async function runPolicy() {
  const mission = policyMission.value;
  const topic = policyTopic.value.trim();
  policyStatus.textContent = 'Searching policy sources...';
  setButtonLoading(policyButton, true);
  try {
    const response = await fetch(`${API_BASE_URL}/api/mode/policy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mission, topic }),
    });
    const data = await response.json();
    if (data.status === 'error') {
      policyStatus.textContent = data.msg;
      return;
    }
    policyStatus.textContent = 'Policy scan complete.';
    policyFeed.innerHTML = `<pre class=\"whitespace-pre-wrap text-sm text-slate-600\">${JSON.stringify(
      data.data,
      null,
      2
    )}</pre>`;
  } catch (error) {
    policyStatus.textContent = 'Policy request failed.';
  } finally {
    setButtonLoading(policyButton, false);
  }
}

function setWelcomeSeen() {
  localStorage.setItem('scout_welcome_seen', 'true');
  welcomeModal.classList.add('hidden');
}

function startTutorial() {
  setWelcomeSeen();
  state.tutorialIndex = 0;
  tutorialSpotlight.classList.remove('hidden');
  tutorialTooltip.classList.remove('hidden');
  showTutorialStep();
}

function endTutorial() {
  tutorialSpotlight.classList.add('hidden');
  tutorialTooltip.classList.add('hidden');
}

function showTutorialStep() {
  const step = tutorialSteps[state.tutorialIndex];
  if (!step) {
    endTutorial();
    return;
  }
  step.action();
  const target = document.getElementById(step.id);
  if (!target) return;
  const rect = target.getBoundingClientRect();
  tutorialSpotlight.style.top = `${rect.top - 8}px`;
  tutorialSpotlight.style.left = `${rect.left - 8}px`;
  tutorialSpotlight.style.width = `${rect.width + 16}px`;
  tutorialSpotlight.style.height = `${rect.height + 16}px`;

  tutorialText.textContent = step.text;
  tutorialTooltip.style.top = `${rect.bottom + 16}px`;
  tutorialTooltip.style.left = `${Math.min(rect.left, window.innerWidth - 340)}px`;
}

welcomeStart.addEventListener('click', setWelcomeSeen);
welcomeSkip.addEventListener('click', setWelcomeSeen);
welcomeTutorial.addEventListener('click', startTutorial);

if (localStorage.getItem('scout_welcome_seen') === 'true') {
  welcomeModal.classList.add('hidden');
}

tutorialNext.addEventListener('click', () => {
  state.tutorialIndex += 1;
  showTutorialStep();
});

tutorialSkip.addEventListener('click', endTutorial);

window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    endTutorial();
  }
});

databaseMission.addEventListener('change', loadDatabase);
databaseType.addEventListener('change', loadDatabase);

researchButton.addEventListener('click', runResearch);
radarButton.addEventListener('click', runRadar);
policyButton.addEventListener('click', runPolicy);

if (perspectiveButton) {
  perspectiveButton.addEventListener('click', () => {
    if (state.activeTab === 'research' && state.lastResearch) {
      runResearch({ frictionMode: true, perspective: true });
    }
    if (state.activeTab === 'radar' && state.lastRadar) {
      runRadar({ frictionMode: true, perspective: true });
    }
  });
}
