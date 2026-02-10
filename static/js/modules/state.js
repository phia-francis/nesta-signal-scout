const hostname = window.location.hostname;

function resolveApiBaseUrl() {
  if (hostname.endsWith('.github.io')) {
    return 'https://nesta-signal-backend.onrender.com';
  }
  return window.location.origin;
}

export const state = {
  apiBaseUrl: resolveApiBaseUrl(),
  currentMode: 'radar',
  radarSignals: [],
  databaseItems: [],
};
