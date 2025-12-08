import os
import json
import asyncio
import random
import httpx
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# --- SETUP ---
load_dotenv()

# API KEYS
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GOOGLE SHEETS CONFIG
SHEET_ID = os.getenv("SHEET_ID")
SHEET_URL = os.getenv("SHEET_URL", "#")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")

# GOOGLE SEARCH CONFIG
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")
GOOGLE_SEARCH_CX = os.getenv("GOOGLE_SEARCH_CX")

# --- CLIENT INIT ---
client = OpenAI(
    api_key=OPENAI_API_KEY,
    default_headers={"OpenAI-Beta": "assistants=v2"}
)

app = FastAPI()

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
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        g_client = gspread.authorize(creds)
        return g_client.open_by_key(SHEET_ID).sheet1
    except Exception as e:
        print(f"❌ Google Sheets Auth Error: {e}")
        return None

async def perform_google_search(query):
    """Performs a real web search using Google Custom Search API."""
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_CX:
        print("❌ CONFIG ERROR: Missing Google Search Keys")
        return "System Error: Search is not configured. Proceed with internal knowledge but flag as unverified."
    
    print(f"🔍 Searching Google for: '{query}'...")
    
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": GOOGLE_SEARCH_KEY,
        "cx": GOOGLE_SEARCH_CX,
        "q": query,
        "num": 3 # Fetch top 3 results
    }
    
    async with httpx.AsyncClient() as http_client:
        try:
            resp = await http_client.get(url, params=params)
            
            if resp.status_code != 200:
                print(f"❌ Google API Error: {resp.text}")
                return f"Search Failed: {resp.status_code}."

            data = resp.json()
            
            if "items" not in data:
                print("⚠️ No results found.")
                return "No search results found."
            
            # Format results for the AI
            results = []
            for item in data["items"]:
                results.append(f"Title: {item.get('title')}\nLink: {item.get('link')}\nSnippet: {item.get('snippet', '')}")
            
            output = "\n\n".join(results)
            print("✅ Search Successful.")
            return output

        except Exception as e:
            print(f"❌ Exception during search: {e}")
            return f"Search Exception: {str(e)}"

def craft_widget_response(tool_args):
    """Standardizes the card data for the frontend."""
    # Ensure URL is present
    url = tool_args.get("sourceURL") or tool_args.get("url")
    if not url:
        # Fallback if AI fails to provide URL (should be rare with new instructions)
        query = tool_args.get("title", "").replace(" ", "+")
        url = f"https://www.google.com/search?q={query}"
    
    tool_args["final_url"] = url
    tool_args["ui_type"] = "signal_card"
    return tool_args

# --- DATA MODELS ---

class ChatRequest(BaseModel):
    message: str
    time_filter: str = "Past Year"
    source_types: List[str] = []
    tech_mode: bool = False

class SaveSignalRequest(BaseModel):
    title: str
    score: int
    archetype: str
    hook: str
    url: str
    mission: Optional[str] = ""
    lenses: Optional[str] = ""
    score_evocativeness: Optional[int] = 0
    score_novelty: Optional[int] = 0
    score_evidence: Optional[int] = 0

# --- API ENDPOINTS ---

@app.get("/api/config")
def get_config():
    """Returns public config like the Sheet URL."""
    return {"sheet_url": SHEET_URL}

@app.get("/api/saved")
def get_saved_signals():
    """Fetches saved signals from Google Sheets."""
    try:
        sheet = get_google_sheet()
        if not sheet: return []
        
        records = sheet.get_all_records()
        return records[::-1] # Newest first
    except Exception as e:
        print(f"Read Error: {e}")
        return [] 

@app.post("/api/save")
def save_signal(signal: SaveSignalRequest):
    """Saves a signal to Google Sheets."""
    try:
        sheet = get_google_sheet()
        if not sheet:
            raise HTTPException(status_code=500, detail="Could not connect to Google Sheets")
        
        # Row format: Title, Score, Archetype, Hook, URL, Mission, Lenses, Evo, Nov, Evi
        row = [
            signal.title,
            signal.score,
            signal.archetype,
            signal.hook,
            signal.url,
            signal.mission,
            signal.lenses,
            signal.score_evocativeness,
            signal.score_novelty,
            signal.score_evidence
        ]
        
        sheet.append_row(row)
        return {"status": "success"}
    except Exception as e:
        print(f"Save Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/saved/{signal_id}")
def delete_signal(signal_id: int):
    return {"status": "ignored", "message": "Please delete directly from Google Sheets"}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        print(f"Incoming Query: {req.message} | Filters: {req.time_filter}, TechMode: {req.tech_mode}")
        
        # 1. DEDUPLICATION (Fetch recent titles to avoid repeats)
        existing_titles = []
        try:
            sheet = get_google_sheet()
            if sheet:
                # Fetch Column A (Titles), limit to last 50
                titles_col = sheet.col_values(1)
                existing_titles = titles_col[-50:] 
        except Exception as e:
            print(f"Dedup Warning: {e}")

        # 2. PROMPT CONSTRUCTION
        prompt = req.message
        
        # INJECT "SEARCH FIRST" BEHAVIOR
        prompt += "\n\nSYSTEM INSTRUCTION: You currently have 0 verified signals. You MUST use the 'perform_web_search' tool to find real articles before generating any cards. Do not generate cards from memory."

        if req.tech_mode:
            prompt += "\n\nCONSTRAINT: This is a TECHNICAL HORIZON SCAN. Search ONLY for Hard Tech (Hardware, Biotech, Materials, Code). Ignore policy/social trends."
        
        if req.source_types:
            sources_str = ", ".join(req.source_types)
            prompt += f"\n\nCONSTRAINT: Prioritize findings from these source types: {sources_str}."

        prompt += f"\n\nCONSTRAINT: Time Horizon is '{req.time_filter}'. Ensure signals are recent."
        
        # Add Salt for randomness
        prompt += f"\n\n[System Note: Random Seed {random.randint(1000, 9999)}]"
        
        # Add Blocklist
        clean_titles = [t for t in existing_titles if t.lower() != "title" and t.strip() != ""]
        if clean_titles:
            blocklist_str = ", ".join([f'"{t}"' for t in clean_titles])
            prompt += f"\n\nIMPORTANT: Do NOT return these titles (user already has them): {blocklist_str}"

        # 3. RUN ASSISTANT
        run = await asyncio.to_thread(
            client.beta.threads.create_and_run,
            assistant_id=ASSISTANT_ID,
            thread={"messages": [{"role": "user", "content": prompt}]}
        )

        while True:
            run_status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve, thread_id=run.thread_id, run_id=run.id
            )

            if run_status.status == 'requires_action':
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                signals_found = []
                tool_outputs = []

                for tool in tool_calls:
                    # A. HANDLE SEARCH TOOL
                    if tool.function.name == "perform_web_search":
                        args = json.loads(tool.function.arguments)
                        search_query = args.get("query")
                        
                        # Execute Search
                        search_result = await perform_google_search(search_query)
                        
                        tool_outputs.append({
                            "tool_call_id": tool.id,
                            "output": search_result
                        })

                    # B. HANDLE SIGNAL CARD TOOL
                    elif tool.function.name == "display_signal_card":
                        args = json.loads(tool.function.arguments)
                        processed_card = craft_widget_response(args)
                        signals_found.append(processed_card)
                        
                        # Success response to AI
                        tool_outputs.append({
                            "tool_call_id": tool.id,
                            "output": json.dumps({"status": "displayed"})
                        })

                # SUBMIT ALL OUTPUTS
                if tool_outputs:
                    await asyncio.to_thread(
                        client.beta.threads.runs.submit_tool_outputs,
                        thread_id=run.thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                
                # If we have signals, return them to UI immediately
                # (The AI might keep running in background, but we want to show results fast)
                if signals_found:
                    return {"ui_type": "signal_list", "items": signals_found}
                        
            if run_status.status == 'completed':
                messages = await asyncio.to_thread(
                    client.beta.threads.messages.list, thread_id=run.thread_id
                )
                if messages.data:
                    text = messages.data[0].content[0].text.value
                    return {"ui_type": "text", "content": text}
                else:
                    return {"ui_type": "text", "content": "Scan complete."}
            
            if run_status.status in ['failed', 'cancelled', 'expired']:
                print(f"Run Status: {run_status.status}")
                return {"ui_type": "text", "content": "I encountered an error processing that signal."}

            await asyncio.sleep(1)

    except Exception as e:
        print(f"Critical Backend Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
