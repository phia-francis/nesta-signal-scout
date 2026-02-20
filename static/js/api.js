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

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60_000);

    try {
        const response = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query, mission }),
            signal: controller.signal,
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();

        if (!data.signals || data.signals.length === 0) {
            console.warn("Agent discarded all sources — try a broader query.");
        }

        return data;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === "AbortError") {
            console.error("Scan timed out after 60 seconds.");
        }
        throw error;
    }
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
