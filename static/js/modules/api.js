import { state } from './state.js';

export async function wakeServer() {
  await fetch(`${state.apiBaseUrl}/`);
}

export async function fetchSavedSignals() {
  const response = await fetch(`${state.apiBaseUrl}/api/saved`);
  const payload = await response.json();
  return payload.signals || [];
}

export async function triggerScan(query, mission, mode) {
  const endpointMap = {
    radar: "/scan/radar",
    research: "/scan/research",
    governance: "/scan/governance",
  };

  const url = `${state.apiBaseUrl}${endpointMap[mode] ?? endpointMap.radar}`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, mission }),
  });

  return response.json();
}

export async function runRadarScan(body, onMessage) {
  const response = await fetch(`${state.apiBaseUrl}/scan/radar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}

export async function clusterSignals(signals) {
  const response = await fetch(`${state.apiBaseUrl}/cluster`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signals }),
  });
  return response.json();
}

export async function updateSignalStatus(url, status) {
  await fetch(`${state.apiBaseUrl}/api/update_signal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, status }),
  });
}
