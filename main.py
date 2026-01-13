import os
import json
import asyncio
import random
import re
import httpx
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse
from typing import Optional, List, Dict, Any, Set
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials
from bs4 import BeautifulSoup
from keywords import MISSION_KEYWORDS, CROSS_CUTTING_KEYWORDS

# --- SETUP ---
load_dotenv()

# API KEYS
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# CONFIG
SHEET_ID = os.getenv("SHEET_ID")
SHEET_URL = os.getenv("SHEET_URL", "#")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")
GOOGLE_SEARCH_KEY = os.getenv("Google_Search_API_KEY") or os.getenv("GOOGLE_SEARCH_KEY")
GOOGLE_SEARCH_CX = os.getenv("Google_Search_CX") or os.getenv("GOOGLE_SEARCH_CX")

# --- CLIENT INIT ---
client = OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

app = FastAPI()

# ✅ STRONG CORS CONFIGURATION
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- HELPERS ---

def get_google_sheet():
    """Authenticates and returns the Google Sheet object."""
    try:
        if not GOOGLE_CREDENTIALS_JSON or not SHEET_ID:
            print("⚠️ Google Sheets credentials missing.")
            return None
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        g_client = gspread.authorize(creds)
        return g_client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Google Sheets Auth Error: {e}")
        return None

def ensure_sheet_headers(sheet):
    expected_headers = [
        "Title", "Score", "Hook", "URL", "Mission", "Lenses",
        "Score_Evocativeness", "Score_Novelty", "Score_Evidence",
        "User_Rating", "User_Status", "User_Comment", "Shareable", "Feedback", "Source_Date"
    ]
    try:
        existing_headers = sheet.row_values(1)
        if existing_headers != expected_headers:
            sheet.update([expected_headers], 'A1')
    except Exception as e:
        print(f"⚠️ Header Check Failed: {e}")

async def fetch_article_text(url: str) -> str:
    """Scrapes the URL to get the actual content for better hooks/validation."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code >= 400:
                return f"Error: Could not read page (Status {resp.status_code})"
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text[:2500] + "..."
    except Exception as e:
        return f"Error reading article: {str(e)}"

TIME_FILTER_OFFSETS = {
    "Past Month": relativedelta(months=1),
    "Past 3 Months": relativedelta(months=3),
    "Past 6 Months": relativedelta(months=6),
    "Past Year": relativedelta(years=1)
}

def parse_source_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    cleaned = date_str.strip()
    if not cleaned or cleaned.lower() in {"recent", "unknown", "n/a", "na"}:
        return None
    cleaned = re.sub(r"[|•]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    iso_match = re.search(r"\d{4}-\d{2}-\d{2}", cleaned)
    if iso_match:
        cleaned = iso_match.group(0)
    else:
        slash_match = re.search(r"\d{1,2}/\d{1,2}/\d{4}", cleaned)
        if slash_match:
            cleaned = slash_match.group(0)

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y"
    ]
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    month_year_formats = ["%B %Y", "%b %Y"]
    for fmt in month_year_formats:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(day=1)
        except ValueError:
            continue

    if re.fullmatch(r"\d{4}", cleaned):
        return datetime(int(cleaned), 1, 1)
    return None

def is_date_within_time_filter(source_date: Optional[str], time_filter: str, request_date: datetime) -> bool:
    parsed = parse_source_date(source_date)
    if not parsed:
        logging.warning(f'⚠️ Date Rejected (Unparsable): {source_date}')
        return False
    if parsed > request_date:
        return False
    offset = TIME_FILTER_OFFSETS.get(time_filter, TIME_FILTER_OFFSETS["Past Month"])
    cutoff_date = request_date - offset
    return parsed >= cutoff_date

def get_sheet_records(include_rejected: bool = False) -> List[Dict[str, Any]]:
    sheet = get_google_sheet()
    if not sheet: return []
    ensure_sheet_headers(sheet)
    try:
        rows = sheet.get_all_values()
        if not rows: return []
        headers = rows[0]
        records = []
        for idx, row in enumerate(rows[1:], start=2):
            if all(cell == "" for cell in row): continue
            while len(row) < len(headers): row.append("")
            record = {headers[i]: row[i] for i in range(len(headers))}
            record["_row"] = idx
            status = str(record.get("User_Status", "")).lower()
            if not include_rejected and status == "rejected": continue
            records.append(record)
        return records
    except Exception as e:
        print(f"Read Error: {e}")
        return []

def upsert_signal(signal: Dict[str, Any]) -> None:
    sheet = get_google_sheet()
    if not sheet: return
    ensure_sheet_headers(sheet)
    
    row_data = [
        signal.get("title", ""), 
        signal.get("score", 0),
        signal.get("hook", ""), 
        signal.get("url", ""), 
        signal.get("mission", ""),
        signal.get("lenses", ""), 
        signal.get("score_evocativeness", 0),
        signal.get("score_novelty", 0), 
        signal.get("score_evidence", 0),
        signal.get("user_rating", 3), 
        signal.get("user_status", "Pending"),
        signal.get("user_comment", "") or signal.get("feedback", ""), 
        signal.get("shareable", "Maybe"),
        signal.get("feedback", ""),
        signal.get("source_date", "Recent")
    ]

    try:
        records = get_sheet_records(include_rejected=True)
        match_row = None
        incoming_url = str(signal.get("url", "")).strip().lower()
        
        for rec in records:
            if str(rec.get("URL", "")).strip().lower() == incoming_url:
                match_row = rec.get("_row")
                break
        
        if match_row:
            sheet.update(f"A{match_row}:O{match_row}", [row_data])
        else:
            sheet.append_row(row_data)
    except Exception as e:
        print(f"Upsert Error: {e}")

async def perform_google_search(query, date_restrict="m1", requested_results: int = 15):
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_CX: return "System Error: Search Config Missing"
    target_results = max(1, min(20, requested_results))
    exclusions = "-site:reddit.com -site:quora.com -site:twitter.com -site:facebook.com -site:instagram.com"
    final_query = f"{query} {exclusions}"
    print(f"🔍 Searching: '{final_query}' ({date_restrict})...")
    url = "https://www.googleapis.com/customsearch/v1"
    results = []
    start_index = 1
    async with httpx.AsyncClient() as http_client:
        try:
            while len(results) < target_results:
                params = {
                    "key": GOOGLE_SEARCH_KEY, "cx": GOOGLE_SEARCH_CX,
                    "q": final_query, "num": 10, "start": start_index, "dateRestrict": date_restrict
                }
                resp = await http_client.get(url, params=params)
                if resp.status_code != 200: break
                items = resp.json().get("items", [])
                if not items: break
                for item in items:
                    results.append(f"Title: {item.get('title')}\nLink: {item.get('link')}\nSnippet: {item.get('snippet', '')}")
                if len(items) < 10: break
                start_index += 10
            return "\n\n".join(results[:target_results])
        except Exception as e: return f"Search Exception: {str(e)}"

# --- ENDPOINTS ---
class ChatRequest(BaseModel):
    message: str
    time_filter: str = "Past Month"
    source_types: List[str] = Field(default_factory=list)
    tech_mode: bool = False
    mission: str = "All Missions" # Added mission field to request

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    run = None
    try:
        # 1. Get Current Date
        request_date = datetime.now()
        today_str = request_date.strftime("%Y-%m-%d")
        print(f"Incoming: {req.message} | Mission: {req.mission} | Date: {today_str}")
        
        # 2. Select Keywords based on Mission
        relevant_keywords_set = set()
        if req.mission in MISSION_KEYWORDS:
            relevant_keywords_set.update(MISSION_KEYWORDS[req.mission])
        elif req.mission == "All Missions":
             for key in MISSION_KEYWORDS:
                 relevant_keywords_set.update(MISSION_KEYWORDS[key])
        
        # Always include cross-cutting
        relevant_keywords_set.update(CROSS_CUTTING_KEYWORDS)
        
        # Convert to list for random.sample
        relevant_keywords_list = list(relevant_keywords_set)
        
        # Random sample to keep prompt size manageable and varied
        selected_keywords = random.sample(relevant_keywords_list, min(len(relevant_keywords_list), 15))
        keywords_str = ", ".join(selected_keywords)

        # 3. Construct Prompt
        prompt_parts = [
            req.message,
            f"CURRENT DATE: {today_str}",
            "ROLE: You are the Lead Foresight Researcher for Nesta's 'Discovery Hub.' Your goal is to identify 'Weak Signals'—obscure, high-potential indicators of change.",
            "LANGUAGE PROTOCOL (CRITICAL): You must strictly use British English spelling and terminology.",
            "- Use: Colour, Centre, Programme, Minimise, Behaviour, Organisation, Labour.",
            "- Avoid: Color, Center, Program, Minimize, Behavior, Organization, Labor.",
            f"SUGGESTED KEYWORDS: {keywords_str}",
            "Core Directive: YOU ARE A RESEARCH ENGINE, NOT A WRITER.",
            "- NO MEMORY: You know nothing. You must search `perform_web_search` to find every signal.",
            "- NO SEARCH = NO SIGNAL: If you cannot find a direct URL, the signal does not exist.",
            "- QUALITY CONTROL (CRITICAL): ",
            "  1. DIRECT LINKS ONLY: You must output the URL to the primary study, startup, or press release. NEVER output an aggregator link (Yahoo, MSN, Newsletters).",
            "  2. NO UGC: Do not rely on Reddit, Quora, or Social Media. If a signal is found there, you must trace it to a reputable primary source.",
            "1. THE SCORING RUBRIC (Strict Calculation):",
            "A. NOVELTY (0-10): 'Distance from the Mainstream'",
            "   0-3 (Low): Covered by major outlets (BBC, NYT). Allow ONLY if Evidence score is High (8+).",
            "   4-6 (Mid): Trade press, industry journals, niche blogs.",
            "   7-8 (High): Local/non-English news, GitHub Repos, Specialist Substack, Patents.",
            "   9-10 (Peak): Academic pre-prints (arXiv), Leaked policy docs, Hard Tech Whitepapers.",
            "B. EVIDENCE (0-10): 'Reality vs. Rumour'",
            "   0-2: Concept art, rumours.",
            "   3-5: Startup launch, proposed bill.",
            "   6-8: Physical pilot, beta test, published paper.",
            "   9-10: Passed legislation, widespread adoption, failed large-scale experiment.",
            "C. EVOCATIVENESS (0-10): 'The What!? Factor'",
            "   0-3: Incremental update.",
            "   4-6: Logical evolution.",
            "   7-8: Unintended consequence.",
            "   9-10: Shocking/Visual (Biological computers, Sand Theft).",
            "2. THE 'DEEP HOOK' PROTOCOL:",
            "The hook field is a Strategic Briefing (75-100 words) written in British English. Use this 3-sentence structure:",
            "- The Signal (The What): What specifically happened?",
            "- The Twist (The Context): Why is this weird, novel, or counter-intuitive?",
            "- The Implication (The Nesta Angle): What makes it interesting for Nesta? Why should Nesta care?",
            "3. OPERATIONAL ALGORITHM:",
            "STEP 1: QUERY ENGINEERING (The Friction Method)",
            "Generate 3-5 queries. Avoid generic topics.",
            "- Underground: [Topic] AND ('unregulated' OR 'black market' OR 'off-label use')",
            "- Failure: [Topic] AND ('lawsuit' OR 'banned' OR 'ethical outcry' OR 'recall')",
            "- Edge: [Topic] AND ('open source' OR 'repository' OR 'citizen science' -site:reddit.com)",
            "STEP 2: EXECUTION & DEEP VERIFICATION (Mandatory)",
            "1. Call `perform_web_search`.",
            "2. FILTER: Ignore aggregators. Select the most promising result.",
            "3. TRACE THE SOURCE: If your result is a news summary, you MUST call `fetch_article_text` to find the link to the *original* source.",
            "4. DEEP READ: Call `fetch_article_text` on the PRIMARY URL.",
            "5. VERIFY: Does the full text confirm the signal? If it's a 'Top 10' list or opinion piece, DISCARD and search again.",
            "STEP 3: GENERATE CARD (Data Extraction)",
            "If the signal passes Deep Verification, call `display_signal_card`.",
            "- Assign Mission (Strict Enum): 'A Fairer Start', 'A Healthy Life', 'A Sustainable Future', 'Mission Adjacent'.",
            "LOOPING LOGIC: Continue searching, tracing, and verifying until you have exactly N validated signals.",
            "SEARCH RULE: Do NOT include specific years or 'since:' operators. The tool handles time filtering.",
            "URL SAFETY: NEVER fabricate URLs.",
            "TOOL CONTRACT: You MUST call 'fetch_article_text' on a URL before calling 'display_signal_card'. Never display a card based solely on a Google snippet.",
            "VALIDATION: Only display sources with published dates within the user's time horizon relative to CURRENT DATE."
        ]
        prompt = "\n\n".join(prompt_parts)
        
        if req.tech_mode: prompt += "\nCONSTRAINT: Hard Tech / Emerging Tech ONLY."
        
        # Explicit instruction for Gateway to Research
        bias_sources = req.source_types
        if "Gateway to Research" in bias_sources:
            prompt += "\nCONSTRAINT: User selected 'Gateway to Research'. You MUST include searches using 'site:gtr.ukri.org' to find relevant projects."
        
        prompt += f"\nCONSTRAINT: Time Horizon {req.time_filter}. Bias Source Types: {', '.join(bias_sources)}."
        
        run = await asyncio.to_thread(
            client.beta.threads.create_and_run,
            assistant_id=ASSISTANT_ID,
            thread={"messages": [{"role": "user", "content": prompt}]}
        )

        accumulated_signals = []
        seen_urls = set()

        # Polling Loop with Cancellation Support
        while True:
            try:
                run_status = await asyncio.to_thread(client.beta.threads.runs.retrieve, thread_id=run.thread_id, run_id=run.id)
                
                if run_status.status == 'requires_action':
                    tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool in tool_calls:
                        if tool.function.name == "perform_web_search":
                            args = json.loads(tool.function.arguments)
                            d_map = {"Past Month": "m1", "Past 3 Months": "m3", "Past 6 Months": "m6", "Past Year": "y1"}
                            res = await perform_google_search(args.get("query"), d_map.get(req.time_filter, "m1"))
                            tool_outputs.append({"tool_call_id": tool.id, "output": res})
                        elif tool.function.name == "fetch_article_text":
                            args = json.loads(tool.function.arguments)
                            content = await fetch_article_text(args.get("url"))
                            tool_outputs.append({"tool_call_id": tool.id, "output": content})
                        elif tool.function.name == "display_signal_card":
                            args = json.loads(tool.function.arguments)
                            published_date = args.get("published_date", "")
                            if not is_date_within_time_filter(published_date, req.time_filter, request_date):
                                tool_outputs.append({"tool_call_id": tool.id, "output": "rejected_out_of_time_window"})
                                continue
                            card = {
                                "title": args.get("title"), "url": args.get("final_url") or args.get("url"),
                                "hook": args.get("hook"), "score": args.get("score"),
                                "mission": args.get("mission", "General"),
                                "lenses": args.get("lenses", ""),
                                "score_novelty": args.get("score_novelty", 0),
                                "score_evidence": args.get("score_evidence", 0),
                                "score_evocativeness": args.get("score_evocativeness", 0),
                                "source_date": published_date,
                                "ui_type": "signal_card"
                            }
                            if card["url"] and card["url"] not in seen_urls:
                                accumulated_signals.append(card)
                                seen_urls.add(card["url"])
                                # Upsert in thread to prevent blocking cancellation
                                try: await asyncio.to_thread(upsert_signal, card)
                                except: pass
                                tool_outputs.append({"tool_call_id": tool.id, "output": "displayed"})
                            else:
                                tool_outputs.append({"tool_call_id": tool.id, "output": "duplicate_skipped"})

                    await asyncio.to_thread(client.beta.threads.runs.submit_tool_outputs, thread_id=run.thread_id, run_id=run.id, tool_outputs=tool_outputs)

                elif run_status.status == 'completed':
                    if accumulated_signals:
                        return {"ui_type": "signal_list", "items": accumulated_signals}
                    else:
                        msgs = await asyncio.to_thread(client.beta.threads.messages.list, thread_id=run.thread_id)
                        return {"ui_type": "text", "content": msgs.data[0].content[0].text.value}
                
                elif run_status.status in ['failed', 'expired', 'cancelled']:
                    return {"ui_type": "text", "content": f"System Error: {run_status.last_error}"}
                
                await asyncio.sleep(1)

            except asyncio.CancelledError:
                print(f"🛑 Scan cancelled by user. Terminating Run {run.id}...")
                try:
                    await asyncio.to_thread(client.beta.threads.runs.cancel, thread_id=run.thread_id, run_id=run.id)
                except Exception as e:
                    print(f"Error cancelling run: {e}")
                raise # Re-raise to allow FastAPI to close the connection properly

    except Exception as e:
        print(f"Server Error: {e}")
        # Only check for cancellation if 'run' was created
        if isinstance(e, asyncio.CancelledError) and run:
            try:
                await asyncio.to_thread(client.beta.threads.runs.cancel, thread_id=run.thread_id, run_id=run.id)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/saved")
def get_saved(): return get_sheet_records()

@app.post("/api/update")
def update_sig(req: Dict[str, Any]): 
    try:
        upsert_signal(req)
        return {"status": "updated"}
    except Exception as e:
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- STATIC FILE SERVING ---
@app.get("/")
def serve_home():
    try:
        with open("index.html", "r") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except:
        return HTMLResponse(content="<h1>Backend Running</h1>", status_code=200)

@app.get("/Zosia-Display.woff2")
def serve_font1(): return FileResponse("Zosia-Display.woff2")

@app.get("/Averta-Regular.otf")
def serve_font2(): return FileResponse("Averta-Regular.otf")

@app.get("/Averta-Semibold.otf")
def serve_font3(): return FileResponse("Averta-Semibold.otf")
