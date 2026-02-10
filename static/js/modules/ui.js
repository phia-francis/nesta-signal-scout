export function showToast(message) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const node = document.createElement('div');
  node.className = 'bg-nesta-navy text-white px-4 py-2 rounded shadow-hard';
  node.textContent = message;
  container.appendChild(node);
  setTimeout(() => node.remove(), 3000);
}

export function renderSignals(signals, container) {
  container.innerHTML = '';
  signals.forEach((signal) => {
    const card = document.createElement('article');
    card.className = 'bg-white border border-slate-200 p-4 space-y-2';

    const title = document.createElement('h3');
    title.className = 'font-display text-lg text-nesta-blue';
    title.textContent = signal.title || 'Untitled Signal';

    const summary = document.createElement('p');
    summary.className = 'text-sm text-slate-700';
    summary.textContent = signal.summary || '';

    const link = document.createElement('a');
    link.href = signal.url || '#';
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'text-xs text-nesta-navy underline';
    link.textContent = 'Open source';

    card.append(title, summary, link);
    container.appendChild(card);
  });
}
