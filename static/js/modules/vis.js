import { state } from './state.js';

let currentThemes = [];
let currentThemeFilter = null;

export function generateSparklineElement(dataPoints) {
  if (!Array.isArray(dataPoints) || dataPoints.length === 0) return null;

  const width = 100;
  const height = 30;
  const maxValue = Math.max(...dataPoints);
  const minValue = Math.min(...dataPoints);
  const range = maxValue - minValue || 1;

  const points = dataPoints
    .map((value, index) => {
      const x = (index / Math.max(dataPoints.length - 1, 1)) * width;
      const y = height - ((value - minValue) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  const [lastX, lastY] = points.split(' ').pop().split(',');

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '30');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('points', points);
  polyline.setAttribute('fill', 'none');
  polyline.setAttribute('stroke', '#0000FF');
  polyline.setAttribute('stroke-width', '2');
  polyline.setAttribute('vector-effect', 'non-scaling-stroke');

  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', lastX);
  circle.setAttribute('cy', lastY);
  circle.setAttribute('r', '3');
  circle.setAttribute('fill', '#0000FF');

  svg.append(polyline, circle);
  return svg;
}

export function renderNetworkGraph(signals) {
  const container = document.getElementById('signal-network');
  if (!container || !window.vis) return;

  const nodes = new window.vis.DataSet(
    signals.map((signal, index) => ({
      id: index,
      label: `${(signal.title || 'Signal').substring(0, 15)}...`,
      title: signal.title || 'Signal',
      value: Number(signal.score_activity || 1),
      group: signal.mission || 'General',
      shape: 'dot',
    }))
  );

  const edgesArray = [];
  for (let leftIndex = 0; leftIndex < signals.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < signals.length; rightIndex += 1) {
      const sameTypology = signals[leftIndex].typology === signals[rightIndex].typology;
      const sameMission = signals[leftIndex].mission === signals[rightIndex].mission;
      if (sameTypology || sameMission) {
        edgesArray.push({ from: leftIndex, to: rightIndex });
      }
    }
  }

  const edges = new window.vis.DataSet(edgesArray);

  const options = {
    nodes: {
      font: { color: '#FFFFFF', face: 'Inter', size: 10 },
      borderWidth: 0,
      shadow: true,
    },
    edges: {
      color: { color: '#0000FF', highlight: '#18A48C' },
      width: 0.5,
      smooth: false,
    },
    groups: {
      'A Sustainable Future': { color: '#18A48C' },
      'A Healthy Life': { color: '#F6A4B7' },
      'A Fairer Start': { color: '#FDB633' },
      General: { color: '#0000FF' },
    },
    physics: {
      stabilization: false,
      barnesHut: { gravitationalConstant: -2000, springConstant: 0.04 },
    },
    interaction: { hover: true, tooltipDelay: 0 },
  };

  const networkGraph = new window.vis.Network(container, { nodes, edges }, options);
  networkGraph.on('click', (params) => {
    if (params.nodes.length > 0) {
      const signalUrl = signals[params.nodes[0]].url;
      if (signalUrl) {
        window.open(signalUrl, '_blank');
      }
    }
  });
}

function updateUrlWithScanId(scanId) {
  const newUrl = new URL(window.location.href);
  newUrl.searchParams.set('scan', scanId);
  window.history.pushState({ scanId }, '', newUrl.toString());
}

export function handleThemeFilter(theme) {
  currentThemeFilter = theme;

  const feed = document.getElementById('radar-feed');
  if (!feed) return;

  feed.innerHTML = '';

  let filteredSignals = state.globalSignalsArray;

  if (theme && theme.signal_ids) {
    filteredSignals = state.globalSignalsArray.filter((signal, index) => {
      return theme.signal_ids.includes(index);
    });
  }

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

export async function clusterAndRenderThemes(signals) {
  if (!signals || signals.length < 3) {
    console.log('Not enough signals for clustering (minimum 3 required)');
    return;
  }

  try {
    console.log(`Clustering ${signals.length} signals...`);

    const response = await fetch(`${state.apiBaseUrl}/cluster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signals: signals })
    });

    if (!response.ok) {
      throw new Error(`Clustering failed: ${response.status}`);
    }

    const result = await response.json();
    currentThemes = result.themes || [];

    if (result.scan_id) {
      state.currentScanId = result.scan_id;
      updateUrlWithScanId(result.scan_id);

      const shareBtn = document.getElementById('share-scan-btn');
      if (shareBtn) {
        shareBtn.style.display = 'inline-flex';
      }

      console.log(`Scan saved with ID: ${result.scan_id}`);
    }

    if (currentThemes.length > 0) {
      console.log(`Found ${currentThemes.length} themes`);

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

export function setupViewToggle() {
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
