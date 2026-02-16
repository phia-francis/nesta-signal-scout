function buildTriageCard(signal) {
  return `
    <article class="bg-white shadow-hard p-8 border border-slate-200 space-y-4">
      <div class="flex items-center justify-between">
        <span class="text-[10px] uppercase tracking-widest font-bold text-nesta-blue">${signal.mission || 'General'}</span>
        <span class="text-[10px] uppercase tracking-widest font-bold text-nesta-navy">${signal.typology || 'Unsorted'}</span>
      </div>
      <h3 class="font-display text-2xl text-nesta-navy leading-tight">${signal.title || 'Untitled Signal'}</h3>
      <p class="text-sm text-nesta-dark-grey leading-relaxed">${signal.summary || ''}</p>
      <a href="${signal.url || '#'}" target="_blank" rel="noopener noreferrer" class="text-xs text-nesta-blue underline">Open source</a>
    </article>
  `;
}

export function initialiseTriage({
  getQueue,
  onArchive,
  onKeep,
  onStar,
}) {
  const modal = document.getElementById('triage-modal');
  const closeButton = document.getElementById('triage-close');
  const cardContainer = document.getElementById('triage-card-container');
  const progressBar = document.getElementById('triage-progress');
  const actionButtons = document.querySelectorAll('[data-triage-action]');

  let queue = [];
  let index = 0;

  function renderCurrent() {
    if (!cardContainer || !progressBar) return;
    if (!queue.length) {
      cardContainer.innerHTML = '<div class="text-white/80 text-center">No new signals to triage.</div>';
      progressBar.style.width = '0%';
      return;
    }

    const currentSignal = queue[index];
    cardContainer.innerHTML = buildTriageCard(currentSignal);
    const progress = ((index + 1) / queue.length) * 100;
    progressBar.style.width = `${progress}%`;
  }

  function close() {
    if (!modal) return;
    modal.classList.add('hidden');
    document.removeEventListener('keydown', handleKeyDown);
  }

  function advance() {
    index += 1;
    if (index >= queue.length) {
      close();
      return;
    }
    renderCurrent();
  }

  function applyAction(action) {
    const currentSignal = queue[index];
    if (!currentSignal) return;

    if (action === 'archive') {
      onArchive?.(currentSignal);
    } else if (action === 'star') {
      onStar?.(currentSignal);
    } else {
      onKeep?.(currentSignal);
    }

    advance();
  }

  function handleKeyDown(event) {
    if (!modal || modal.classList.contains('hidden')) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
      return;
    }
    if (event.key.toLowerCase() === 'a') {
      event.preventDefault();
      applyAction('archive');
      return;
    }
    if (event.key.toLowerCase() === 's') {
      event.preventDefault();
      applyAction('star');
      return;
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      applyAction('keep');
    }
  }

  function open() {
    queue = (getQueue?.() || []).slice();
    index = 0;
    if (!modal) return;
    modal.classList.remove('hidden');
    renderCurrent();
    document.addEventListener('keydown', handleKeyDown);
  }

  closeButton?.addEventListener('click', close);
  actionButtons.forEach((button) => {
    button.addEventListener('click', () => {
      applyAction(button.dataset.triageAction || 'keep');
    });
  });

  return { open, close };
}
