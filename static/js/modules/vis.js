export function generateSparklineElement(dataPoints) {
  if (!dataPoints || dataPoints.length === 0) return null;

  const width = 100;
  const height = 30;
  const maxVal = Math.max(...dataPoints);
  const minVal = Math.min(...dataPoints);
  const range = maxVal - minVal || 1;

  const points = dataPoints
    .map((value, index) => {
      const x = (index / (dataPoints.length - 1 || 1)) * width;
      const y = height - ((value - minVal) / range) * height;
      return `${x},${y}`;
    })
    .join(' ');

  const [lastX, lastY] = points.split(' ').pop().split(',');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '30');
  svg.setAttribute('viewBox', '0 0 100 30');

  const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
  polyline.setAttribute('points', points);
  polyline.setAttribute('fill', 'none');
  polyline.setAttribute('stroke', '#0000FF');
  polyline.setAttribute('stroke-width', '2');

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
      value: signal.score_activity || 1,
      group: signal.mission || 'General',
      shape: 'dot',
    }))
  );

  const edgesArray = [];
  for (let index = 0; index < signals.length; index += 1) {
    for (let innerIndex = index + 1; innerIndex < signals.length; innerIndex += 1) {
      if (signals[index].typology === signals[innerIndex].typology) {
        edgesArray.push({ from: index, to: innerIndex });
      }
    }
  }

  const edges = new window.vis.DataSet(edgesArray);
  window.networkGraph = new window.vis.Network(container, { nodes, edges }, { interaction: { hover: true } });
}
