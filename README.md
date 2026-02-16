# Nesta Signal Scout - Production Refactor

**Version:** 2.0.0  
**Date:** February 2026  
**Status:** Production-Ready

## Overview

Signal Scout is a production-grade AI-powered horizon scanning agent for Nesta's Discovery Hub. It combines Google Search, OpenAlex, UKRI GtR, and OpenAI synthesis to discover emerging innovations across Nesta's mission areas.

## What Was Fixed

### 1. Configuration (CRITICAL)
- ✅ **Fail-fast validation**: App now fails loudly if environment variables are missing
- ✅ **Proper error messages**: Clear guidance on what's misconfigured
- ✅ **Startup summary**: Logs configuration status without leaking secrets

### 2. Agent Logic
- ✅ **Research mode synthesis**: Now properly aggregates many sources → one AI-synthesised card
- ✅ **International policy mode**: Removed UK-only bias, now includes global government sources (.gov, .gov.uk, .gov.au, .gov.ca, .int, .org)
- ✅ **Real LLM integration**: Replaced stub with actual OpenAI synthesis using `gpt-4o`
- ✅ **Proper caching**: 24-hour cache for expensive API calls

### 3. Frontend Architecture
- ✅ **Complete modular structure**: All missing modules created (state.js, api.js, ui.js, triage.js, vis.js)
- ✅ **Responsive design**: Mobile-first, works on all screen sizes
- ✅ **Nesta branding**: Strict adherence to Nesta visual identity (colors, fonts, styling)
- ✅ **Modern UX**: Hard-edge aesthetic, proper loading states, toast notifications
- ✅ **Keyboard-driven triage**: Efficient signal review workflow

### 4. Database Optimisation
- ✅ **Batch operations**: Prevents database OOM crashes
- ✅ **Async operations**: Non-blocking Google Sheets integration
- ✅ **Proper error handling**: Graceful degradation on failures

## Architecture

```
signal-scout-refactor/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── cron.py
│   │       ├── intelligence.py
│   │       ├── policy.py
│   │       ├── radar.py
│   │       ├── research.py (FIXED - now does synthesis)
│   │       └── system.py
│   ├── core/
│   │   ├── config.py (FIXED - fail-fast validation)
│   │   ├── logging.py
│   │   ├── prompts.py
│   │   └── resilience.py
│   ├── domain/
│   │   ├── models.py
│   │   └── taxonomy.py
│   └── services/
│       ├── analytics_svc.py
│       ├── cluster_svc.py
│       ├── crunchbase_svc.py (deprecated)
│       ├── gtr_svc.py
│       ├── llm_svc.py (FIXED - real OpenAI integration)
│       ├── openalex_svc.py
│       ├── scan_logic.py (FIXED - international policy)
│       ├── search_svc.py
│       └── sheet_svc.py
├── static/
│   ├── css/
│   │   └── styles.css (Nesta branding)
│   ├── js/
│   │   ├── api.js (NEW - API communication)
│   │   ├── app.js (entry point)
│   │   ├── main.js (NEW - orchestrator)
│   │   ├── state.js (NEW - state management)
│   │   ├── triage.js (NEW - keyboard triage)
│   │   ├── ui.js (NEW - rendering)
│   │   ├── vis.js (NEW - network visualisation)
│   │   └── tailwind-theme.js
│   └── fonts/
│       ├── Averta-Regular.otf
│       ├── Averta-Semibold.otf
│       └── Zosia-Display.woff2
└── templates/
    └── index.html (NEW - modern responsive UI)
```

## Environment Variables

Create a `.env` file with these **REQUIRED** variables:

```bash
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4o"
OPENAI_MAX_TOKENS=2000

# Google Search Configuration (REQUIRED)
GOOGLE_SEARCH_API_KEY="..."
GOOGLE_SEARCH_CX="..."

# Google Sheets Configuration (REQUIRED)
GOOGLE_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
SHEET_ID="..."
SHEET_URL="https://docs.google.com/spreadsheets/d/..."

# OpenAlex Configuration (OPTIONAL)
OPENALEX_API_KEY="..."  # Optional but recommended

# Application Settings
LOG_LEVEL="INFO"
ENVIRONMENT="production"
CRON_SECRET="..."  # Optional, for scheduled jobs
```

### How to Get Environment Variables

1. **OPENAI_API_KEY**: Get from https://platform.openai.com/api-keys
2. **GOOGLE_SEARCH_API_KEY**: Create at https://console.cloud.google.com/apis/credentials
3. **GOOGLE_SEARCH_CX**: Create Custom Search Engine at https://programmablesearchengine.google.com/
4. **GOOGLE_CREDENTIALS**: Create service account at https://console.cloud.google.com/iam-admin/serviceaccounts
5. **SHEET_ID**: Extract from your Google Sheet URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`

## Deployment on Render

### Step 1: Push to GitHub

```bash
cd signal-scout-refactor
git init
git add .
git commit -m "Production-ready Signal Scout v2.0"
git remote add origin https://github.com/nesta/signal-scout.git
git push -u origin main
```

### Step 2: Create Web Service on Render

1. Go to https://dashboard.render.com/
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `signal-scout`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: At least `Standard` (need sufficient memory for OpenAI/Sheets)

### Step 3: Set Environment Variables

In Render dashboard, go to "Environment" tab and add ALL required variables from `.env` above.

**CRITICAL**: Ensure `GOOGLE_CREDENTIALS` is a single-line JSON string (remove newlines from private_key).

### Step 4: Deploy

Click "Create Web Service" - Render will automatically deploy.

## Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY="..."
export GOOGLE_SEARCH_API_KEY="..."
export GOOGLE_SEARCH_CX="..."
export GOOGLE_CREDENTIALS='{"type":"service_account",...}'
export SHEET_ID="..."

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open browser
open http://localhost:8000
```

## Usage Guide

### Scan Modes

1. **Radar Mode** (Discovery)
   - Discovers emerging signals from multiple sources
   - Scores by activity, attention, and recency
   - Classifies into typologies: Nascent, Hidden Gem, Hype, Established

2. **Research Mode** (Synthesis)
   - Aggregates 10-20 sources
   - Uses OpenAI to synthesise one comprehensive Signal Card
   - Best for deep-dive analysis

3. **Policy Mode** (Targeted)
   - Searches global government sources (.gov, .gov.uk, .gov.au, etc.)
   - Focuses on policy documents and official publications
   - High-trust filtering

### Triage Workflow

1. Run a scan to populate signals
2. Click "Triage" button
3. Use keyboard shortcuts:
   - **←** Archive (not relevant)
   - **↑** Star (high priority)
   - **→** Keep (relevant, review later)
4. Signals are automatically saved to database

### Auto-Clustering

1. After scanning, click "Auto-cluster"
2. AI groups signals into narrative themes
3. View themes in side drawer
4. Useful for identifying patterns across signals

## Monitoring

- **Logs**: All operations logged with structured JSON
- **Errors**: Critical errors send 503 status with sanitised messages
- **Performance**: API calls cached for 24 hours
- **Database**: Background sync prevents blocking

## Maintenance

### Updating Mission Areas

Edit `app/keywords.py` to add new mission areas or expand topic keywords.

### Modifying Scoring

Edit `app/services/analytics_svc.py` to adjust scoring weights and thresholds.

### Customising LLM Prompts

Edit `app/core/prompts.py` for system prompts and synthesis instructions.

## Troubleshooting

### App Won't Start

**Symptom**: "ValidationError" on startup  
**Solution**: Check that ALL required environment variables are set correctly

### Research Mode Returns Empty

**Symptom**: No synthesis card generated  
**Solution**: Check OpenAI API key is valid and has credits

### Policy Mode Only Returns UK Results

**Symptom**: Only seeing .gov.uk sources  
**Solution**: This was fixed - update to latest code

### Database OOM Crashes

**Symptom**: Server crashes when loading database  
**Solution**: Use `get_rows_by_mission()` instead of `get_all()` in sheet_svc.py

## Support

For issues or questions:
1. Check logs in Render dashboard
2. Verify environment variables are set correctly
3. Ensure Google Sheets service account has editor permissions
4. Contact: [Your Team Email]

## Licence

Copyright © 2026 Nesta. All rights reserved.
