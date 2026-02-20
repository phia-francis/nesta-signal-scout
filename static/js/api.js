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

async function triggerScan(query, mission, mode) {
  const endpointMap = {
    radar: "/scan/radar",
    research: "/scan/research",
    governance: "/scan/governance",
  };

  const url = endpointMap[mode] ?? endpointMap.radar;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mission }),
  });

  return response.json();
}

export { triggerScan };

export async function runRadarScan(payload, onMessage) {
  const response = await fetch('/scan/radar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

export async function runGovernanceScan(payload, onMessage) {
  const response = await fetch('/scan/governance', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

export async function runResearchScan(payload) {
  const response = await fetch('/scan/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
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
    const response = await fetch('/cluster', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signals }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } catch (error) {
    console.error('[API] Clustering failed:', error);
    return [];
  }
}
