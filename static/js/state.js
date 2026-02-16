/**
 * Global application state management
 */
export const state = {
  currentMode: 'radar',
  radarSignals: [],
  researchSignals: [],
  policySignals: [],
  databaseItems: [],
  triageQueue: [],
  isScanning: false,
  currentView: 'grid',
  currentTopic: '',
  currentMission: 'All Missions',
  frictionMode: false,
  toasts: [],
};

export function setState(updates) {
  Object.assign(state, updates);
}

export function clearCurrentModeSignals() {
  if (state.currentMode === 'radar') {
    state.radarSignals = [];
  } else if (state.currentMode === 'research') {
    state.researchSignals = [];
  } else if (state.currentMode === 'policy') {
    state.policySignals = [];
  }
  state.triageQueue = [];
}

export function getCurrentModeSignals() {
  if (state.currentMode === 'radar') return state.radarSignals;
  if (state.currentMode === 'research') return state.researchSignals;
  if (state.currentMode === 'policy') return state.policySignals;
  return [];
}
