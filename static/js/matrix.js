/**
 * Horizon Matrix Visualization
 * 2x2 scatter plot showing signals by Activity vs Attention
 */

let matrixChart = null;

/**
 * Get mission color for a signal
 */
function getMissionColorForMatrix(mission) {
  const colors = {
    'A Sustainable Future': '#18A48C',  // Green
    'A Healthy Life': '#F6A4B7',        // Pink
    'A Fairer Start': '#FDB633',        // Yellow
  };
  return colors[mission] || '#0000FF';  // Default to Nesta blue
}

/**
 * Render Horizon Matrix scatter plot
 */
export function renderHorizonMatrix(signals) {
  const canvas = document.getElementById('horizonCanvas');
  if (!canvas) {
    console.error('Canvas element #horizonCanvas not found');
    return;
  }
  
  const ctx = canvas.getContext('2d');
  
  // Destroy existing chart if any
  if (matrixChart) {
    matrixChart.destroy();
  }
  
  // Prepare data for Chart.js
  const chartData = signals.map((signal, index) => ({
    x: signal.score_attention || 0,
    y: signal.score_activity || 0,
    signalIndex: index,
    title: signal.title || 'Unknown',
    mission: signal.mission || 'General',
    source: signal.source || '',
    finalScore: signal.final_score || 0
  }));
  
  // Group by mission for different colors
  const missions = ['A Sustainable Future', 'A Healthy Life', 'A Fairer Start', 'General'];
  const datasets = missions.map(mission => {
    const missionData = chartData.filter(d => d.mission === mission);
    return {
      label: mission,
      data: missionData,
      backgroundColor: getMissionColorForMatrix(mission),
      borderColor: '#0F294A',
      borderWidth: 2,
      pointRadius: 8,
      pointHoverRadius: 12,
      pointHoverBorderWidth: 3,
    };
  }).filter(ds => ds.data.length > 0);  // Only include missions with data
  
  // Create chart with quadrant backgrounds
  matrixChart = new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: {
            display: true,
            text: 'Attention →',
            font: {
              size: 14,
              family: "'Noto Serif', serif",
              weight: 'bold'
            },
            color: '#0F294A'
          },
          min: 0,
          max: 10,
          ticks: {
            stepSize: 2,
            color: '#0F294A'
          },
          grid: {
            color: '#E2E8F0',
            lineWidth: 1
          }
        },
        y: {
          title: {
            display: true,
            text: '↑ Activity',
            font: {
              size: 14,
              family: "'Noto Serif', serif",
              weight: 'bold'
            },
            color: '#0F294A'
          },
          min: 0,
          max: 10,
          ticks: {
            stepSize: 2,
            color: '#0F294A'
          },
          grid: {
            color: '#E2E8F0',
            lineWidth: 1
          }
        }
      },
      plugins: {
        tooltip: {
          enabled: true,
          callbacks: {
            title: (context) => {
              const point = context[0].raw;
              return point.title;
            },
            label: (context) => {
              const point = context.raw;
              return [
                `Activity: ${point.y.toFixed(1)}`,
                `Attention: ${point.x.toFixed(1)}`,
                `Score: ${point.finalScore.toFixed(1)}`,
                `Source: ${point.source}`
              ];
            }
          },
          backgroundColor: '#0F294A',
          titleColor: '#FFFFFF',
          bodyColor: '#FFFFFF',
          borderColor: '#0000FF',
          borderWidth: 2,
          padding: 12,
          displayColors: false,
          titleFont: {
            size: 14,
            family: "'Noto Serif', serif",
            weight: 'bold'
          },
          bodyFont: {
            size: 12,
            family: "-apple-system, sans-serif"
          }
        },
        legend: {
          display: true,
          position: 'top',
          labels: {
            font: {
              size: 12,
              family: "-apple-system, sans-serif"
            },
            color: '#0F294A',
            padding: 15,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        }
      },
      onClick: (event, elements) => {
        if (elements.length > 0) {
          const element = elements[0];
          const datasetIndex = element.datasetIndex;
          const dataIndex = element.index;
          const signal = matrixChart.data.datasets[datasetIndex].data[dataIndex];
          
          // Open detail panel if function exists
          if (typeof window.openDetailPanel === 'function') {
            window.openDetailPanel({
              title: signal.title,
              mission: signal.mission,
              score_activity: signal.y,
              score_attention: signal.x,
              final_score: signal.finalScore,
              source: signal.source
            });
          } else {
            console.log('Signal clicked:', signal.title);
          }
        }
      }
    },
    plugins: [{
      id: 'quadrantBackgrounds',
      beforeDraw: (chart) => {
        const ctx = chart.ctx;
        const chartArea = chart.chartArea;
        const xMid = (chartArea.left + chartArea.right) / 2;
        const yMid = (chartArea.top + chartArea.bottom) / 2;
        
        // Save context
        ctx.save();
        
        // Top-left quadrant (Hidden) - Light blue
        ctx.fillStyle = '#E3F2FD';
        ctx.fillRect(chartArea.left, chartArea.top, xMid - chartArea.left, yMid - chartArea.top);
        
        // Top-right quadrant (Established) - Light green
        ctx.fillStyle = '#E8F5E9';
        ctx.fillRect(xMid, chartArea.top, chartArea.right - xMid, yMid - chartArea.top);
        
        // Bottom-left quadrant (Weak) - Light grey
        ctx.fillStyle = '#F5F5F5';
        ctx.fillRect(chartArea.left, yMid, xMid - chartArea.left, chartArea.bottom - yMid);
        
        // Bottom-right quadrant (Hype) - Light yellow
        ctx.fillStyle = '#FFF9E6';
        ctx.fillRect(xMid, yMid, chartArea.right - xMid, chartArea.bottom - yMid);
        
        // Restore context
        ctx.restore();
      }
    }, {
      id: 'quadrantLabels',
      afterDraw: (chart) => {
        const ctx = chart.ctx;
        const chartArea = chart.chartArea;
        const xMid = (chartArea.left + chartArea.right) / 2;
        const yMid = (chartArea.top + chartArea.bottom) / 2;
        
        ctx.save();
        ctx.font = 'bold 12px -apple-system, sans-serif';
        ctx.fillStyle = '#64748B';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        
        // Top-left
        ctx.fillText('Hidden Gems', chartArea.left + (xMid - chartArea.left) / 2, chartArea.top + 10);
        
        // Top-right
        ctx.fillText('Established', xMid + (chartArea.right - xMid) / 2, chartArea.top + 10);
        
        // Bottom-left
        ctx.fillText('Weak Signals', chartArea.left + (xMid - chartArea.left) / 2, yMid + 10);
        
        // Bottom-right
        ctx.fillText('Hype Cycle', xMid + (chartArea.right - xMid) / 2, yMid + 10);
        
        ctx.restore();
      }
    }]
  });
  
  console.log(`Horizon Matrix rendered with ${chartData.length} signals`);
}

/**
 * Clear the matrix chart
 */
export function clearMatrix() {
  if (matrixChart) {
    matrixChart.destroy();
    matrixChart = null;
  }
}
