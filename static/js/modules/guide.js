const TOUR_STEPS = [
  {
    target: 'nav',
    title: 'Primary Navigation',
    description: 'Access the Signal Database to view saved signals or open the User Guide.',
    position: 'bottom',
  },
  {
    target: '.scan-module',
    title: 'Scan Configuration',
    description:
      "Choose your lens: 'Mini Radar' for broad trends, 'Deep Research' for academic rigour, or 'Governance Radar' for policy.",
    position: 'bottom',
  },
  {
    target: '#query-input',
    title: 'Search Input',
    description:
      'Enter a topic and select a mission context. The agent automatically applies friction terms to find novel, edge-case signals.',
    position: 'bottom',
  },
  {
    target: '#radar-feed',
    title: 'Results Grid',
    description: 'Real-time results appear here, scored for Activity and Attention.',
    position: 'top',
  },
];

class MissionDiscoveryTour {
  constructor() {
    this.currentStepIndex = 0;
    this.activeTarget = null;
    this.isActive = false;

    this.handleResize = this.onResize.bind(this);
    this.handleScroll = this.onScroll.bind(this);
    this.handleKeydown = this.onKeydown.bind(this);

    this.createUi();
  }

  createUi() {
    this.overlay = document.createElement('div');
    this.overlay.className = 'fixed inset-0 bg-[#0F294A]/75 z-[60]';

    this.card = document.createElement('div');
    this.card.className =
      'fixed z-[70] w-[min(92vw,360px)] bg-[#0F294A] text-white border-2 border-[#0000FF] shadow-[8px_8px_0_0_#E6007C] p-4 md:p-5';

    this.kicker = document.createElement('p');
    this.kicker.className = 'text-xs uppercase tracking-widest text-[#E6007C]';
    this.kicker.textContent = 'Mission Discovery Walkthrough';

    this.title = document.createElement('h3');
    this.title.className = 'text-lg md:text-xl font-display mt-2';

    this.description = document.createElement('p');
    this.description.className = 'text-sm mt-2 text-white/90 leading-relaxed';

    this.counter = document.createElement('p');
    this.counter.className = 'text-xs mt-4 text-[#E6007C]';

    this.buttonRow = document.createElement('div');
    this.buttonRow.className = 'mt-4 flex flex-wrap gap-2';

    this.previousButton = document.createElement('button');
    this.previousButton.type = 'button';
    this.previousButton.dataset.tour = 'previous';
    this.previousButton.className = 'px-3 py-2 text-xs font-bold border border-white/40 text-white hover:bg-white/10';
    this.previousButton.textContent = 'Previous';

    this.nextButton = document.createElement('button');
    this.nextButton.type = 'button';
    this.nextButton.dataset.tour = 'next';
    this.nextButton.className = 'px-3 py-2 text-xs font-bold bg-[#0000FF] text-white hover:brightness-110';
    this.nextButton.textContent = 'Next';

    this.endButton = document.createElement('button');
    this.endButton.type = 'button';
    this.endButton.dataset.tour = 'end';
    this.endButton.className = 'ml-auto px-3 py-2 text-xs font-bold bg-[#E6007C] text-white hover:brightness-110';
    this.endButton.textContent = 'End Tour';

    this.buttonRow.append(this.previousButton, this.nextButton, this.endButton);
    this.card.append(this.kicker, this.title, this.description, this.counter, this.buttonRow);

    this.card.addEventListener('click', (event) => {
      const action = event.target.closest('[data-tour]')?.dataset.tour;
      if (!action) {
        return;
      }

      if (action === 'previous') {
        this.goPrevious();
      } else if (action === 'next') {
        this.goNext();
      } else if (action === 'end') {
        this.end();
      }
    });
  }

  ensureRadarMode() {
    if (typeof window.setTab === 'function') {
      window.setTab('radar');
      return;
    }

    const radarButton = document.getElementById('nav-radar');
    radarButton?.click();
  }

  resolveTarget(selector) {
    return document.querySelector(selector);
  }

  isTargetVisible(target) {
    return Boolean(target && target.offsetParent !== null);
  }

  findStepIndex(startIndex, direction) {
    let index = startIndex;

    while (index >= 0 && index < TOUR_STEPS.length) {
      const target = this.resolveTarget(TOUR_STEPS[index].target);
      if (this.isTargetVisible(target)) {
        return index;
      }
      index += direction;
    }

    return -1;
  }

  start() {
    this.ensureRadarMode();
    this.currentStepIndex = 0;

    if (!this.isActive) {
      document.body.append(this.overlay, this.card);
      window.addEventListener('resize', this.handleResize);
      window.addEventListener('scroll', this.handleScroll, { passive: true, capture: true });
      document.addEventListener('keydown', this.handleKeydown);
      this.isActive = true;
    }

    this.setStep(0, 1, true);
  }

  end() {
    if (!this.isActive) {
      return;
    }

    this.clearHighlight();
    this.overlay.remove();
    this.card.remove();

    window.removeEventListener('resize', this.handleResize);
    window.removeEventListener('scroll', this.handleScroll, true);
    document.removeEventListener('keydown', this.handleKeydown);
    this.isActive = false;
  }

  clearHighlight() {
    if (!this.activeTarget) {
      return;
    }

    this.activeTarget.classList.remove('tour-highlight');
    this.activeTarget = null;
  }

  onResize() {
    if (this.isActive) {
      this.updateCardPosition();
    }
  }

  onScroll() {
    if (this.isActive) {
      this.updateCardPosition();
    }
  }

  onKeydown(event) {
    if (event.key === 'Escape') {
      this.end();
    }
  }

  setStep(requestedIndex, direction, shouldScroll) {
    const nextIndex = this.findStepIndex(requestedIndex, direction);
    if (nextIndex === -1) {
      this.end();
      return;
    }

    this.currentStepIndex = nextIndex;
    this.renderStep(shouldScroll);
  }

  goNext() {
    this.setStep(this.currentStepIndex + 1, 1, true);
  }

  goPrevious() {
    this.setStep(this.currentStepIndex - 1, -1, true);
  }

  updateCardPosition() {
    if (!this.activeTarget) {
      return;
    }

    const step = TOUR_STEPS[this.currentStepIndex];
    const targetRect = this.activeTarget.getBoundingClientRect();
    const cardRect = this.card.getBoundingClientRect();
    const gap = 16;

    let top = targetRect.bottom + gap;
    let left = targetRect.left;

    if (step.position === 'right') {
      top = targetRect.top;
      left = targetRect.right + gap;
    } else if (step.position === 'top') {
      top = targetRect.top - cardRect.height - gap;
      left = targetRect.left;
    }

    const maxLeft = window.innerWidth - cardRect.width - 12;
    const maxTop = window.innerHeight - cardRect.height - 12;

    this.card.style.left = `${Math.max(12, Math.min(left, maxLeft))}px`;
    this.card.style.top = `${Math.max(12, Math.min(top, maxTop))}px`;
  }

  renderStep(shouldScroll) {
    const step = TOUR_STEPS[this.currentStepIndex];
    const target = this.resolveTarget(step.target);

    if (!this.isTargetVisible(target)) {
      this.setStep(this.currentStepIndex + 1, 1, shouldScroll);
      return;
    }

    this.clearHighlight();
    target.classList.add('tour-highlight');
    this.activeTarget = target;

    if (shouldScroll) {
      target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
      window.setTimeout(() => this.updateCardPosition(), 220);
    } else {
      this.updateCardPosition();
    }

    const isFirst = this.currentStepIndex === 0;
    const isLast = this.currentStepIndex === TOUR_STEPS.length - 1;

    this.title.textContent = `${step.title}`;
    this.description.textContent = `${step.description}`;
    this.counter.textContent = `Step ${this.currentStepIndex + 1} of ${TOUR_STEPS.length}`;

    this.previousButton.disabled = isFirst;
    this.previousButton.classList.toggle('opacity-50', isFirst);
    this.previousButton.classList.toggle('cursor-not-allowed', isFirst);
    this.nextButton.textContent = isLast ? 'Finish' : 'Next';
  }
}

const tour = new MissionDiscoveryTour();

export function startTour() {
  tour.start();
}

// Expose globally so non-module scripts (main.js) can call it
window.startTour = startTour;

export { TOUR_STEPS, tour };
