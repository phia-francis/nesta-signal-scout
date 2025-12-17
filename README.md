-----

# 📡 Nesta Signal Scout

**The Automated Horizon Scanning Agent for the Discovery Hub.**

Signal Scout is an AI-powered research assistant designed to identify "Weak Signals"—obscure, high-potential indicators of change—across the web. It operates as a relentless research engine, using the "Friction Method" to bypass mainstream hype and find evidence-based innovation signals aligned with Nesta’s missions.

-----

## 🚀 Key Features

  * **AI Research Agent:** Powered by OpenAI `gpt-4.1 mini`, acting as a Lead Foresight Researcher.
  * **The "Friction Method":** Generates high-entropy search queries (e.g., *Topic + "unregulated"*, *Topic + "homebrew"*) to find non-obvious results.
  * **Live Web Access:** Performs real-time Google Searches; it does not hallucinate signals from memory.
  * **Strict Verification:** The "Kill Committee" protocol rejects generic opinion pieces and ensures every signal has a direct source URL.
  * **Nesta Brand aligned:** Fully styled UI using the official Nesta colour palette and custom typography (*Zosia Display* & *Averta*).
  * **Mission Intelligence:** Automatically tags signals with Nesta Missions (e.g., *A Fairer Start*, *A Sustainable Future*) and applies the correct brand theming.
  * **Google Sheets Database:** Auto-saves findings to a shared Google Sheet with deduplication and safe-merge logic to prevent data loss.

-----

## 🛠️ Tech Stack

  * **Frontend:** Vanilla HTML5 / JavaScript (ES6+)
      * Styling: Tailwind CSS (via CDN)
      * Hosting: GitHub Pages
  * **Backend:** Python 3.9+
      * Framework: **FastAPI** (Async, High-performance)
      * Server: Uvicorn / Gunicorn
      * Hosting: Render.com
  * **AI & Data:**
      * **OpenAI API:** Assistants API (Beta v2)
      * **Google Custom Search JSON API:** For live web results.
      * **Google Sheets API:** `gspread` & `oauth2client` for persistence.

-----

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
      * Renders the structured signals into Nesta-branded cards.
      * *Hosted on GitHub Pages.*

-----

## 🔌 Setup & Deployment

### 1\. Prerequisites (API Keys)

You need the following secrets to run the backend:

  * `OPENAI_API_KEY`: A standard OpenAI API key.
  * `ASSISTANT_ID`: The ID of your pre-configured OpenAI Assistant.
  * `Google Search_KEY`: API Key for Google Custom Search.
  * `Google Search_CX`: The Search Engine ID (Context) for Google.
  * `GOOGLE_CREDENTIALS`: The **full JSON content** of your Google Service Account key (for Sheets access).

### 2\. Backend Deployment (Render)

1.  Create a new **Web Service** on [Render](https://render.com/).
2.  Connect this GitHub repository.
3.  **Build Command:** `pip install -r requirements.txt`
4.  **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
5.  **Environment Variables:** Add all the keys listed in Prerequisites.
      * *Note:* For `GOOGLE_CREDENTIALS`, paste the entire JSON object string.

### 3\. Frontend Deployment (GitHub Pages)

1.  Ensure the following font files are in your root directory:
      * `Zosia-Display.woff2`
      * `Averta-Regular.otf`
      * `Averta-Semibold.otf`
2.  Open `index.html` and verify the `API_BASE_URL` matches your Render URL:
    ```javascript
    const API_BASE_URL = "https://your-app-name.onrender.com";
    ```
3.  Go to **GitHub Repo Settings** -\> **Pages**.
4.  Select `main` branch as the source and click **Save**.

-----

## 🧠 The AI Protocol (How it Thinks)

The agent follows a strict **System Prompt** designed to eliminate "hallucinations" and "corporate fluff".

**The Friction Method:**
Instead of searching for *"Future of AI"*, the agent is instructed to search for:

  * *AI AND "lawsuit"*
  * *AI AND "unregulated"*
  * *AI AND "black market"*

**Scoring Rubric:**
Every signal is scored (0-100) based on three dimensions:

1.  **Novelty:** Distance from the mainstream (BBC = Low, arXiv/Reddit = High).
2.  **Evidence:** Reality factor (Concept = Low, Pilot/Law = High).
3.  **Evocativeness:** The "What the hell?" factor.

-----

## 📂 Project Structure

```text
.
├── main.py              # The FastAPI Backend (The Brain)
├── keywords.py          # Mission & Cross-cutting keyword lists
├── index.html           # The Frontend UI (The Face)
├── requirements.txt     # Python dependencies
├── render.yaml          # Render Infrastructure-as-Code config
├── Zosia-Display.woff2  # Custom Nesta Font
├── Averta-Regular.otf   # Custom Nesta Font
└── Averta-Semibold.otf  # Custom Nesta Font
```

-----

## 🔒 Security Note

  * **Never commit API keys** to GitHub.
  * The `GOOGLE_CREDENTIALS` variable contains sensitive private keys. Always manage this via the Render Dashboard, never in code files.
  * The Frontend performs no authentication; it is intended for internal usage.

-----

**© 2025 Nesta Discovery Hub**
