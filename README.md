# Signal Scout

> AI-powered strategic foresight and horizon scanning agent

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?logo=tailwind-css&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991?logo=openai&logoColor=white)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

---

## Overview

**Signal Scout** is an AI-powered strategic foresight agent built for [Nesta's](https://www.nesta.org.uk/) mission teams. It automates horizon scanning by discovering, verifying, and scoring *signals* — early indicators of emerging trends, innovations, and policy shifts — across the web, academic literature, and government sources.

Researchers and analysts can run structured scans, receive real-time streaming results synthesised by GPT-4, and archive high-value signals to a shared Google Sheets database. Signal Scout replaces hours of manual desk research with a repeatable, auditable scanning workflow.

The platform uses a fully decoupled architecture: a **FastAPI backend** deployed on Render handles data retrieval and AI synthesis, while a **vanilla JavaScript + Tailwind CSS frontend** hosted on GitHub Pages provides a responsive, SaaS-style interface.

---

## Core Features

- **Three scan modes**
  - ⚡ **Mini Radar** — rapid web and social media trend discovery
  - 🧠 **Deep Research** — AI synthesis of academic papers, blogs, and reports
  - 🌍 **Governance Radar** — government and international policy monitoring
- **Real-time streaming results** via Server-Sent Events (SSE)
- **Mission-based taxonomy filtering** aligned to Nesta's priority missions
- **Google Sheets integration** for collaborative signal archiving and review
- **Dynamic theme switching** with a polished, responsive UI
- **Confidence scoring** with low-confidence warnings on each signal
- **Source credibility badges** for at-a-glance quality assessment
- **Filter chips** with mission and score dropdowns for rapid triage

---

## System Architecture

Signal Scout uses a decoupled frontend/backend architecture:

```
┌─────────────────────────┐         ┌──────────────────────────────┐
│   Frontend (GitHub Pages)│         │   Backend (Render)           │
│                         │  REST   │                              │
│  Vanilla JS + Tailwind  │ ◄─────► │  FastAPI + Python            │
│  index.html             │   SSE   │                              │
│                         │         │  ┌────────────────────────┐  │
└─────────────────────────┘         │  │ External APIs          │  │
                                    │  │ • Google Custom Search │  │
                                    │  │ • OpenAlex             │  │
                                    │  │ • UKRI GtR             │  │
                                    │  │ • OpenAI GPT-4         │  │
                                    │  │ • Google Sheets        │  │
                                    │  └────────────────────────┘  │
                                    └──────────────────────────────┘
```

- The **frontend** sends scan requests via REST and receives results as a real-time SSE stream.
- The **backend** orchestrates multi-source data retrieval, AI-powered synthesis, scoring, and storage.
- Signals are persisted to **Google Sheets** for collaborative review.

---

## Prerequisites

- Python **3.10+**
- API keys (see [Environment Variables](#environment-variables) below):
  - [OpenAI API key](https://platform.openai.com/api-keys)
  - [Google Custom Search API key](https://developers.google.com/custom-search/v1/overview)
  - Google Custom Search Engine ID
  - Google Sheets credentials (service account JSON)

---

## Local Setup & Installation

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/phia-francis/nesta-signal-scout.git
cd nesta-signal-scout

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your API keys (see below)

# Run the backend server
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

### Environment Variables

Create a `.env` file in the repository root with the following values:

```plaintext
# Required
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o
GOOGLE_SEARCH_API_KEY=AIza...
GOOGLE_SEARCH_CX=017...
GOOGLE_CREDENTIALS={"type":"service_account", ...}
SHEET_ID=1abc...

# Optional
OPENALEX_API_KEY=
LOG_LEVEL=INFO
ENVIRONMENT=production
```

> ⚠️ **Security warning:** Never commit your `.env` file or API keys to version control. The `.gitignore` file is already configured to exclude `.env`.

> 💡 **Rate limits:** Free tiers of Google Custom Search (100 queries/day) and OpenAI have usage limits. Monitor your consumption during development.

### Frontend Setup

The frontend is a static site served from the repository root. To run it locally:

```bash
# Option 1: Python HTTP server
python -m http.server 8080
# Visit http://localhost:8080

# Option 2: VS Code Live Server extension
# Right-click index.html → "Open with Live Server"
```

> ⚠️ **Important:** The backend must be running for the frontend to function. The frontend communicates with the backend API for all scan and data operations.

---

## Usage

1. **Select a scan mode** — Mini Radar, Deep Research, or Governance Radar
2. **Choose a mission focus** — pick a Nesta mission or "Cross-cutting / Any"
3. **Enter your research query** — e.g. "Alternative Proteins" or "AI in early years education"
4. **Click RUN SCAN** — results stream in real-time as they are discovered and scored
5. **Review and filter** — use mission and score filter chips to narrow results
6. **Star signals** — save high-value signals to the shared Google Sheets database

---

## Project Structure

```
nesta-signal-scout/
├── app/
│   ├── api/              # FastAPI routes (radar, research, policy, cron)
│   │   └── routes/       # Endpoint modules
│   ├── core/             # Configuration, prompts, security, resilience
│   ├── domain/           # Data models and taxonomy
│   ├── services/         # Business logic (search, LLM, clustering, sheets)
│   └── storage/          # Scan persistence
├── static/
│   ├── css/              # Tailwind styles
│   ├── js/               # Frontend application code
│   │   └── modules/      # ES6 frontend modules
│   └── fonts/            # Custom typefaces
├── tests/                # pytest test suite
├── index.html            # Frontend entry point (GitHub Pages)
├── requirements.txt      # Python dependencies
├── render.yaml           # Render deployment configuration
├── .env.example          # Environment variable template
└── README.md
```

---

## Contributing

Contributions are welcome! Please read the following before submitting a pull request:

- [CONTRIBUTING.md](CONTRIBUTING.md) — development workflow, coding standards, and PR process
- [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — community expectations
- [SECURITY.md](SECURITY.md) — reporting security vulnerabilities

---

## Licence

This project is licensed under the [MIT Licence](LICENSE).

## Acknowledgements

Built by the Mission Discovery team at [Nesta](https://www.nesta.org.uk/), the UK's innovation agency for social good.
