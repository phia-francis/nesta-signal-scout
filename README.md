# Signal Scout Pro Max

> Next-generation AI strategic foresight and horizon scanning agent

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?logo=tailwind-css&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai&logoColor=white)
[![Licence: MIT](https://img.shields.io/badge/licence-MIT-green.svg)](LICENSE)

---

## Overview

**Signal Scout Pro Max** is the advanced evolution of Nesta's AI-powered foresight agent. It automates the discovery, synthesis, and governance of emerging trends by combining real-time web scanning with academic deep-dives.

Analysts can generate Master Research Syntheses for complex topics, visualise trends via interactive network graphs, and triage signals through a human-in-the-loop Accept/Reject workflow that syncs directly to a secure Vault.

The platform uses a decoupled architecture: a **FastAPI backend** (Render) handles agents, clustering, and database sync, while a **Vanilla JS + Tailwind** frontend (GitHub Pages) provides a responsive, modal-driven interface.

---

## Core Features

### Scanning Modes
- **Mini Radar** — Rapid horizon scanning of web, news, and social signals.
- **Deep Dive Research** — Generates a single Master Research Card synthesising insights from academic papers, grey literature, and expert blogs.
- **Horizon Scan** — Broad environmental scanning for weak signals and early indicators.

### Analyst Tools
- **Interactive Network Graph** — Visualise connections between signals and cluster themes in a dynamic node-link diagram.
- **Governance Queue** — A dedicated triage inbox to Keep, Archive, or Star signals with custom reasoning.
- **Smart Clustering** — Auto-group raw signals into coherent narrative themes using LLM analysis.

### Data Persistence
- **Strict-Append Database** — All accepted signals and research cards are appended to the Signal Vault (Google Sheets), creating an immutable audit trail.
- **Real-time Sync** — Decisions made in the UI are instantly recorded in the backend.

---

## System Architecture

```
┌─────────────────────────┐          ┌──────────────────────────────┐
│  Frontend (GitHub Pages) │          │  Backend (Render)             │
│                         │   REST   │                              │
│  • Modular ES6 JS       │ ◄──────► │  • FastAPI Orchestrator      │
│  • Tailwind CSS         │          │  • LLM Orchestration & Agents│
│  • Vis.js Network Graph │          │                              │
│                         │          │  ┌────────────────────────┐  │
└─────────────────────────┘          │  │ Integration Layer      │  │
                                     │  │ • Google Search API    │  │
                                     │  │ • OpenAlex (Academic)  │  │
                                     │  │ • OpenAI GPT-4o        │  │
                                     │  │ • Google Sheets API    │  │
                                     │  └────────────────────────┘  │
                                     └──────────────────────────────┘
```

---

## Prerequisites

- Python 3.10+
- OpenAI API key (GPT-4o recommended)
- Google Custom Search JSON API key and Custom Search Engine ID (`GOOGLE_SEARCH_CX`)
- Google Service Account (for Sheets integration)

---

## Local Setup

### Backend

```bash
git clone https://github.com/phia-francis/nesta-signal-scout.git
cd nesta-signal-scout
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Fill in your keys in .env
uvicorn app.main:app --reload
```

API runs at `http://127.0.0.1:8000`.

### Frontend

```bash
# Option 1: Python
python -m http.server 8080

# Option 2: VS Code — right-click index.html → "Open with Live Server"
```

---

## Usage

1. **Launch** — Open the frontend. The system wakes the backend and fetches recent database items automatically.
2. **Scan** — Select Mini Radar for a list of signals, or Deep Dive to generate a synthesised research card.
3. **Visualise** — Toggle between Grid View and Network View to explore cluster relationships.
4. **Triage** — Open the Triage Queue to process results: Keep (Accepted), Archive (Rejected), or add a comment.

---

## Project Structure

```
nesta-signal-scout/
├── app/
│   ├── api/routes/       # Endpoints: radar, research, governance, cluster, cron
│   ├── core/             # Configuration, prompts, security, resilience
│   ├── domain/           # Data models and taxonomy
│   ├── services/         # Logic: search_svc, sheet_svc, llm_svc, cluster_svc
│   ├── storage/          # Scan persistence
│   └── main.py           # Application entry point
├── static/
│   ├── js/modules/       # Modular frontend: main, api, ui, triage
│   ├── css/              # Tailwind styles
│   └── fonts/            # Custom typefaces
├── tests/                # pytest test suite
├── index.html            # Main UI entry point
├── render.yaml           # Deployment config
└── requirements.txt      # Python dependencies
```

---

## Licence

MIT Licence.

---

*Built by the Mission Discovery Team at Nesta.*
