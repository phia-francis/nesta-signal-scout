/**
 * API communication layer
 */

const API_BASE = '/api';

export async function wakeServer() {
  try {
    await fetch(`${API_BASE}/saved`);
    console.log('[API] Server wake successful');
  } catch (error) {
    console.warn('[API] Server wake failed:', error);
  }
}

export async function fetchSavedSignals() {
  try {
    const response = await fetch(`${API_BASE}/saved`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    return data.signals || [];
  } catch (error) {
    console.error('[API] Failed to fetch saved signals:', error);
    throw error;
  }
}

export async function runRadarScan(payload, onMessage) {
  const response = await fetch(`${API_BASE}/mode/radar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (line.trim()) {
        try {
          const message = JSON.parse(line);
          onMessage(message);
        } catch (e) {
          console.warn('[API] Parse error:', e);
        }
      }
    }
  }

  if (buffer.trim()) {
    try {
      onMessage(JSON.parse(buffer));
    } catch (e) {
      console.warn('[API] Final buffer parse error:', e);
    }
  }
}

export async function runPolicyScan(payload, onMessage) {
  const response = await fetch(`${API_BASE}/mode/policy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);

  const data = await response.json();
  
  if (data.status === 'success' && data.data?.results) {
    onMessage({ status: 'info', msg: 'Fetching policy sources...' });
    
    for (const result of data.data.results) {
      onMessage({ status: 'blip', blip: result });
    }
    
    onMessage({ status: 'complete', msg: 'Policy scan complete' });
  } else {
    onMessage({ status: 'error', msg: data.message || 'Policy scan failed' });
  }
}

export async function runResearchScan(payload) {
  const response = await fetch(`${API_BASE}/mode/research`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  return data.data?.results || [];
}

export async function updateSignalStatus(url, status) {
  const response = await fetch(`${API_BASE}/update_signal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, status }),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

export async function clusterSignals(signals) {
  try {
    const response = await fetch(`${API_BASE}/intelligence/cluster`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(signals),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('[API] Clustering failed:', error);
    return [];
  }
}
