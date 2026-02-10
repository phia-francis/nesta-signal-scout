const TOUR_STEPS = [
  {
    target: 'aside',
    title: 'Primary Navigation',
    description: 'Navigate between Radar (Live Scan) and Database (Saved Signals).',
    position: 'right',
  },
  {
    target: '#search-panel',
    title: 'Mode Selector',
    description:
      "Choose your lens: 'Radar' for broad trends, 'Research' for academic rigour, or 'Policy' for government strategy.",
    position: 'bottom',
  },
  {
    target: 'input[type="text"]',
    title: 'Search Input',
    description:
      'Enter a topic. The agent automatically applies friction terms to find novel, edge-case signals.',
    position: 'bottom',
  },
  {
    target: '#radar-feed',
    title: 'Results Grid',
    description: 'Real-time results appear here with Activity and Attention scores.',
    position: 'top',
  },
];

class MissionDiscoveryTour {
  constructor() {
    this.currentStepIndex = 0;
    this.overlay = null;
    this.card = null;
    this.activeTarget = null;
    this.handleResize = this.renderStep.bind(this);
    this.handleKeydown = this.onKeydown.bind(this);
  }

  start() {
    if (this.overlay) {
      this.end();
    }

    this.overlay = document.createElement('div');
    this.overlay.className = 'fixed inset-0 bg-[#0F294A]/75 z-[60]';

    this.card = document.createElement('div');
    this.card.className =
      'fixed z-[70] w-[min(92vw,360px)] bg-[#0F294A] text-white border-2 border-[#0000FF] shadow-[8px_8px_0_0_#E6007C] p-4 md:p-5';

    document.body.append(this.overlay, this.card);
    window.addEventListener('resize', this.handleResize);
    window.addEventListener('scroll', this.handleResize, true);
    document.addEventListener('keydown', this.handleKeydown);

    this.renderStep();
  }

  end() {
    if (this.activeTarget) {
      this.activeTarget.classList.remove('tour-highlight');
      this.activeTarget = null;
    }

    this.overlay?.remove();
    this.card?.remove();
    this.overlay = null;
    this.card = null;

    window.removeEventListener('resize', this.handleResize);
    window.removeEventListener('scroll', this.handleResize, true);
    document.removeEventListener('keydown', this.handleKeydown);
  }

  onKeydown(event) {
    if (event.key === 'Escape') {
      this.end();
    }
  }

  goNext() {
    this.currentStepIndex += 1;
    if (this.currentStepIndex >= TOUR_STEPS.length) {
      this.end();
      return;
    }
    this.renderStep();
  }

  goPrevious() {
    this.currentStepIndex = Math.max(0, this.currentStepIndex - 1);
    this.renderStep();
  }

  resolveTarget(selector) {
    if (selector === 'aside') {
      return document.querySelector('aside');
    }
    return document.querySelector(selector);
  }

  positionCard(targetRect, position) {
    const cardRect = this.card.getBoundingClientRect();
    const gap = 16;
    let top = targetRect.bottom + gap;
    let left = targetRect.left;

    if (position === 'right') {
      top = targetRect.top;
      left = targetRect.right + gap;
    } else if (position === 'top') {
      top = targetRect.top - cardRect.height - gap;
      left = targetRect.left;
    }

    const maxLeft = window.innerWidth - cardRect.width - 12;
    const maxTop = window.innerHeight - cardRect.height - 12;

    this.card.style.left = `${Math.max(12, Math.min(left, maxLeft))}px`;
    this.card.style.top = `${Math.max(12, Math.min(top, maxTop))}px`;
  }

  renderStep() {
    if (!this.card) {
      return;
    }

    if (this.activeTarget) {
      this.activeTarget.classList.remove('tour-highlight');
      this.activeTarget = null;
    }

    const step = TOUR_STEPS[this.currentStepIndex];
    const target = this.resolveTarget(step.target);

    if (!target) {
      this.goNext();
      return;
    }

    target.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    target.classList.add('tour-highlight');
    this.activeTarget = target;

    const isFirst = this.currentStepIndex === 0;
    const isLast = this.currentStepIndex === TOUR_STEPS.length - 1;

    this.card.innerHTML = `
      <p class="text-xs uppercase tracking-widest text-[#E6007C]">Mission Discovery Walkthrough</p>
      <h3 class="text-lg md:text-xl font-display mt-2">${step.title}</h3>
      <p class="text-sm mt-2 text-white/90 leading-relaxed">${step.description}</p>
      <p class="text-xs mt-4 text-[#E6007C]">Step ${this.currentStepIndex + 1} of ${TOUR_STEPS.length}</p>
      <div class="mt-4 flex flex-wrap gap-2">
        <button type="button" data-tour="previous" class="px-3 py-2 text-xs font-bold border border-white/40 text-white hover:bg-white/10 ${isFirst ? 'opacity-50 cursor-not-allowed' : ''}">Previous</button>
        <button type="button" data-tour="next" class="px-3 py-2 text-xs font-bold bg-[#0000FF] text-white hover:brightness-110">${isLast ? 'Finish' : 'Next'}</button>
        <button type="button" data-tour="end" class="ml-auto px-3 py-2 text-xs font-bold bg-[#E6007C] text-white hover:brightness-110">End Tour</button>
      </div>
    `;

    const previousButton = this.card.querySelector('[data-tour="previous"]');
    const nextButton = this.card.querySelector('[data-tour="next"]');
    const endButton = this.card.querySelector('[data-tour="end"]');

    if (isFirst) {
      previousButton.setAttribute('disabled', 'disabled');
    }

    previousButton?.addEventListener('click', () => this.goPrevious());
    nextButton?.addEventListener('click', () => this.goNext());
    endButton?.addEventListener('click', () => this.end());

    const targetRect = target.getBoundingClientRect();
    this.positionCard(targetRect, step.position);
  }
}

export function startTour() {
  const tour = new MissionDiscoveryTour();
  tour.start();
}

export { TOUR_STEPS };
