import { state } from './state.js';

export async function wakeServer() {
  await fetch(`${state.apiBaseUrl}/`);
}

export async function fetchSavedSignals() {
  const response = await fetch(`${state.apiBaseUrl}/api/saved`);
  const payload = await response.json();
  return payload.signals || [];
}

export async function runRadarScan(body, onMessage) {
  const response = await fetch(`${state.apiBaseUrl}/api/mode/radar`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    lines.forEach((line) => {
      if (!line.trim()) {
        return;
      }
      onMessage(JSON.parse(line));
    });
  }
}
