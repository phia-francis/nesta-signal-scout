# 📡 Nesta Signal Scout

**The Automated Horizon Scanning Agent for the Discovery Hub.**

Signal Scout is an AI-powered research assistant designed to identify obscure signals, high-potential indicators of change, across the web. It operates as a relentless research engine, using the "Friction Method" to bypass mainstream hype and find evidence-based innovation signals aligned with Nesta’s missions.

---

## 🚀 Key Features

* **AI Research Agent:** Powered by OpenAI `gpt-4.1 mini`, acting as a Lead Foresight Researcher.
* **The "Friction Method":** Generates high-entropy search queries (e.g., *Topic + "unregulated"*, *Topic + "homebrew"*) to find non-obvious results.
* **Live Web Access:** Performs real-time Google Searches; it does not hallucinate signals from memory.
* **Strict Verification:** The "Kill Committee" protocol rejects generic opinion pieces and ensures every signal has a direct source URL.
* **Nesta Brand Aligned:** Fully styled UI using the official Nesta colour palette and custom typography (*Zosia Display* & *Averta*).
* **Mission Intelligence:** Automatically tags signals with Nesta Missions (e.g., *A Fairer Start*, *A Sustainable Future*) and applies the correct brand theming.
* **Interactive Visualisations:** Radar charts and network graphs to map "Golden Signals" vs. "Early Noise."
* **Google Sheets Database:** Auto-saves findings to a shared Google Sheet with deduplication and safe-merge logic to prevent data loss.

---

## 🛠️ Tech Stack

* **Frontend:** HTML5, Vanilla JavaScript (ES6+)
    * **Styling:** Tailwind CSS (Hosted locally for security compliance)
    * **Visualisation:** Chart.js (UMD), Vis-Network (UMD)
    * **Hosting:** GitHub Pages
* **Backend:** Python 3.9+
    * **Framework:** **FastAPI** (Async, High-performance)
    * **Server:** Uvicorn
    * **Hosting:** Render.com
* **AI & Data:**
    * **OpenAI API:** Assistants API (Beta v2)
    * **Google Custom Search JSON API:** For live web results.
    * **Google Sheets API:** `gspread` & `oauth2client` for persistence.

---

## ⚙️ Architecture

The system consists of two distinct parts:

1.  **The "Brain" (Backend):**
    * Orchestrates the OpenAI Assistant.
    * Executes Google Searches when the AI requests them (Tool Calling).
    * Parses AI responses into structured JSON.
    * Manages the connection to the Google Sheet database.
    * *Hosted on Render.*

2.  **The "Face" (Frontend):**
    * A static, single-page application.
    * Sends user topics to the Backend via API.
    * Renders structured signals into Nesta-branded cards.
    * **Security Focused:** Implements Subresource Integrity (SRI) hashes and local script hosting to meet strict security standards.
    * *Hosted on GitHub Pages.*

---

## 🔌 Setup & Deployment

### 1. Prerequisites (API Keys)

You need the following secrets to run the backend:

* `OPENAI_API_KEY`: A standard OpenAI API key.
* `ASSISTANT_ID`: The ID of your pre-configured OpenAI Assistant.
* `Google Search_KEY`: API Key for Google Custom Search.
* `Google Search_CX`: The Search Engine ID (Context) for Google.
* `GOOGLE_CREDENTIALS`: The **full JSON content** of your Google Service Account key (for Sheets access).

### 2. Backend Deployment (Render)

1.  Create a new **Web Service** on [Render](https://render.com/).
2.  Connect this GitHub repository.
3.  **Build Command:** `pip install -r requirements.txt`
4.  **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables:** Add all the keys listed in Prerequisites.
    * *Note:* For `GOOGLE_CREDENTIALS`, paste the entire JSON object string.

### 3. Frontend Deployment (GitHub Pages)

1.  **Local Resources:** Ensure `static/js/tailwind.js` exists in your repository. This is required to satisfy security policies (CodeQL) and maintain styling without a build step.
2.  **Fonts:** Ensure the following font files are in your root directory:
    * `Zosia-Display.woff2`
    * `Averta-Regular.otf`
    * `Averta-Semibold.otf`
3.  **Configuration:** Open `static/js/app.js` and verify the `API_BASE_URL` logic handles both localhost and production:
    ```javascript
    const API_BASE_URL = (window.location.hostname === 'localhost') 
        ? '[http://127.0.0.1:8000](http://127.0.0.1:8000)' 
        : '[https://nesta-signal-scout.onrender.com](https://nesta-signal-scout.onrender.com)';
    ```
4.  Go to **GitHub Repo Settings** -> **Pages**.
5.  Select `main` branch as the source and click **Save**.

---

## 🔒 Security & Compliance

This project enforces strict Content Security Policy (CSP) best practices:

* **Subresource Integrity (SRI):** All external CDNs (Chart.js, jsPDF, Vis-Network) must use `integrity` hashes to verify that the scripts have not been tampered with.
* **Local Resources:** Dynamic scripts that do not support stable hashes (specifically Tailwind Play CDN) are downloaded and hosted locally in `/static/js/` to avoid "Untrusted Source" warnings.
* **Rate Limiting:** The UI enforces a strict maximum of **5 signals** per scan request. This prevents users from triggering memory exhaustion (OOM) events on the backend server.

---

## 🧠 The AI Protocol (How it Thinks)

The agent follows a strict **System Prompt** designed to eliminate "hallucinations" and "corporate fluff".

**The Friction Method:**
Instead of searching for *"Future of AI"*, the agent is instructed to search for:
* *AI AND "lawsuit"*
* *AI AND "unregulated"*
* *AI AND "black market"*

**Scoring Rubric:**
Every signal is scored (0-10) based on three dimensions:
1.  **Novelty:** Distance from the mainstream (BBC = Low, arXiv/Reddit = High).
2.  **Evidence:** Reality factor (Concept = Low, Pilot/Law = High).
3.  **Impact:** Potential scale of systemic change.

---

## 📂 Project Structure

```text
.
├── main.py                  # The FastAPI Backend (The Brain)
├── keywords.py              # Mission & Cross-cutting keyword lists
├── index.html               # The Frontend UI (The Face)
├── static/
│   ├── css/
│   │   └── styles.css       # Custom animations & overrides
│   └── js/
│       ├── app.js           # Core frontend logic
│       ├── tailwind.js      # Local Tailwind engine (Security)
│       └── friction-config.js # Search modifier configuration
├── requirements.txt         # Python dependencies
├── render.yaml              # Render Infrastructure-as-Code config
├── Zosia-Display.woff2      # Custom Nesta Font
├── Averta-Regular.otf       # Custom Nesta Font
└── Averta-Semibold.otf      # Custom Nesta Font
