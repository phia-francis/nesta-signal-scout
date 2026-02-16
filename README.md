# Signal Scout

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)
[![Build](https://img.shields.io/badge/build-pytest%20passing-brightgreen.svg)](tests)

**Signal Scout is an AI-powered intelligence agent that helps Nesta discover weak signals, emerging research, and policy shifts across priority missions.**

---

## Overview

Signal Scout (formerly *Nesta Horizon Scanning Agent*) combines a FastAPI backend with a modular JavaScript frontend to run live horizon scans, persist insights, and support rapid analyst triage.

The platform is designed for maintainability and handover readiness, with a refactored Domain-Driven Design (DDD) architecture and clear separation of concerns.

---

## Architecture: “Brain” and “Face”

### The Brain (FastAPI + Python)
The backend handles:
- API routing and orchestration
- External data retrieval (Google Search, GtR, Crunchbase)
- Taxonomy-driven query construction
- Scoring, clustering, and persistence workflows

### The Face (GitHub Pages + Modular JavaScript)
The frontend handles:
- Real-time scan visualisation
- Interactive cards and toasts
- Narrative clustering and signal mapping
- Keyboard-driven triage workflows

This split keeps the service layer robust while allowing fast interface iteration.

---

## Key Features

### 1) Multi-Mode Scanning
- **Radar Mode**: broad weak-signal discovery
- **Research Mode**: targeted academic and evidence-led discovery
- **Policy Mode**: policy and regulation scanning

### 2) The Friction Method
Signal Scout supports friction-enabled search expansion, applying entropy-style terms (for example *unregulated*, *black market*, and *workaround*) to surface less visible signals.

### 3) Live Intelligence
The application streams NDJSON updates during scans for responsive user feedback while data is fetched, scored, and stored.

### 4) Visual Analytics
- **Auto-Cluster Engine**: TF-IDF + MiniBatch K-Means narrative grouping
- **Network Graph**: Vis.js graphing for signal relationships
- **Sparklines**: compact activity/attention trend visuals on signal cards

### 5) Triage Mode (“War Room”)
A rapid review workflow with keyboard shortcuts for high-throughput analyst triage.

### 6) Taxonomy Integration
Expert-curated mission and topic taxonomy powers mission-aware query expansion and consistent scan quality.

---

## Installation and Setup

### Prerequisites
- Python **3.10+**
- Node.js (optional, useful for frontend development tooling)
- Google Cloud service account credentials (for Sheets integration)

### Installation

```bash
git clone https://github.com/phia-francis/nesta-signal-scout.git
cd nesta-signal-scout
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the repository root and provide the required environment variables.

#### Core variables
- `OPENAI_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_CX`
- `GOOGLE_CREDENTIALS` (JSON service account payload as a string)
- `SHEET_ID`

#### Optional/extended variables
- `CRUNCHBASE_API_KEY`
- `GTR_API_KEY`
- `CHAT_MODEL`

> Note: some legacy aliases are supported in settings, but the canonical variable names above are recommended.

### Run the application

```bash
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000`.

---

## Usage Guide

### Running a scan
1. Choose a mode (Radar, Research, or Policy).
2. Select mission/topic inputs.
3. Run scan and monitor live streaming updates.

### Using Triage Mode
- Open **War Room / Triage** from the UI.
- Use shortcuts for rapid decisions:
  - **A** → Archive
  - **S** → Star
  - **ESC** → Exit triage

### Using Network Graph
- Switch from grid view to map view.
- Inspect clusters and linked signals to identify narrative convergence.

---

## Project Structure

```plaintext
app/
├── api/           # Routes and endpoints
├── core/          # Configuration, logging, security, prompts
├── domain/        # Models and taxonomy
└── services/      # Business logic (search, sheets, ML, analytics)

static/
├── js/
│   └── modules/   # ES6 frontend modules
└── css/           # Stylesheets
```

---

## Contributing

Contributions are welcome.

Please read:
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

## Licence

This project is licensed under the MIT Licence. See [LICENSE](LICENSE).
