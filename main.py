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

def get_learning_examples():
    try:
        sheet = get_google_sheet()
        if not sheet: return ""
        records = sheet.get_all_records()
        good_signals = [r for r in records if str(r.get('user_status', '')).lower() == "accepted" or int(r.get('user_rating', 0) or 0) >= 4]
        if not good_signals: return ""
        examples = random.sample(good_signals, k=min(3, len(good_signals)))
        example_str = "### USER'S GOLD STANDARD EXAMPLES (EMULATE THESE):\n"
        for i, ex in enumerate(examples, 1):
            title = ex.get('Title') or ex.get('title')
            hook = ex.get('Hook') or ex.get('hook')
            comment = ex.get('user_comment') or ""
            example_str += f"{i}. Title: {title}\n   Hook: {hook}\n"
            if comment: example_str += f"   User Note: {comment}\n"
            example_str += "\n"
        return example_str
    except Exception as e:
        print(f"Learning Error: {e}")
        return ""

async def perform_google_search(query):
    if not GOOGLE_SEARCH_KEY or not GOOGLE_SEARCH_CX:
        return "System Error: Search is not configured."
    print(f"🔍 Searching Google for: '{query}'...")
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_SEARCH_KEY, "cx": GOOGLE_SEARCH_CX, "q": query, "num": 3}
    async with httpx.AsyncClient() as http_client:
        try:
            resp = await http_client.get(url, params=params)
            if resp.status_code != 200: return f"Search Failed: {resp.status_code}."
            data = resp.json()
            if "items" not in data: return "No search results found."
            results = []
            for item in data["items"]:
                results.append(f"Title: {item.get('title')}\nLink: {item.get('link')}\nSnippet: {item.get('snippet', '')}")
            return "\n\n".join(results)
        except Exception as e: return f"Search Exception: {str(e)}"

def craft_widget_response(tool_args):
    url = tool_args.get("sourceURL") or tool_args.get("url")
    if not url:
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
    user_rating: Optional[int] = 0
    user_status: Optional[str] = "Pending"
    user_comment: Optional[str] = ""

# --- ENDPOINTS ---

@app.get("/api/config")
def get_config():
    return {"sheet_url": SHEET_URL}

@app.get("/api/saved")
def get_saved_signals():
    try:
        sheet = get_google_sheet()
        if not sheet: return []
        records = sheet.get_all_records()
        return records[::-1]
    except Exception: return [] 

@app.post("/api/save")
def save_signal(signal: SaveSignalRequest):
    try:
        sheet = get_google_sheet()
        if not sheet: raise HTTPException(status_code=500, detail="No Sheet")
        row = [
            signal.title, signal.score, signal.archetype, signal.hook, signal.url,
            signal.mission, signal.lenses, signal.score_evocativeness,
            signal.score_novelty, signal.score_evidence,
            signal.user_rating, signal.user_status, signal.user_comment
        ]
        sheet.append_row(row)
        return {"status": "success"}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/saved/{signal_id}")
def delete_signal(signal_id: int):
    return {"status": "ignored", "message": "Delete from Google Sheets directly"}

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        print(f"Query: {req.message} | Filters: {req.time_filter}, Tech: {req.tech_mode}")
        
        # 1. Fetch Context
        existing_titles = []
        learning_prompt = ""
        try:
            sheet = get_google_sheet()
            if sheet:
                existing_titles = sheet.col_values(1)[-50:]
                learning_prompt = get_learning_examples()
        except Exception: pass

        # 2. Prompt Construction
        prompt = req.message
        if learning_prompt: prompt += f"\n\n{learning_prompt}\nINSTRUCTION: Match this taste profile."
        prompt += "\n\nSYSTEM INSTRUCTION: You currently have 0 verified signals. You MUST use 'perform_web_search' first."
        if req.tech_mode: prompt += "\n\nCONSTRAINT: TECHNICAL HORIZON SCAN ONLY."
        if req.source_types: prompt += f"\n\nCONSTRAINT: Prioritize: {', '.join(req.source_types)}."
        prompt += f"\n\nCONSTRAINT: Time Horizon '{req.time_filter}'."
        prompt += f"\n\n[System Note: Random Seed {random.randint(1000, 9999)}]"
        clean_titles = [t for t in existing_titles if t.lower() != "title"]
        if clean_titles: prompt += f"\n\nIMPORTANT: Do NOT return these: {', '.join(clean_titles)}"
        prompt += "\n\nCRITICAL: If the user asked for a specific number (e.g. 5), keep searching until you have exactly that many verified hits."

        # 3. Run Assistant
        run = await asyncio.to_thread(
            client.beta.threads.create_and_run,
            assistant_id=ASSISTANT_ID,
            thread={"messages": [{"role": "user", "content": prompt}]}
        )

        # ✅ NEW: Accumulator for signals
        accumulated_signals = []

        while True:
            run_status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve, thread_id=run.thread_id, run_id=run.id
            )

            if run_status.status == 'requires_action':
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []

                for tool in tool_calls:
                    if tool.function.name == "perform_web_search":
                        args = json.loads(tool.function.arguments)
                        search_result = await perform_google_search(args.get("query"))
                        tool_outputs.append({"tool_call_id": tool.id, "output": search_result})

                    elif tool.function.name == "display_signal_card":
                        args = json.loads(tool.function.arguments)
                        processed_card = craft_widget_response(args)
                        
                        # ✅ STORE SIGNAL, DO NOT RETURN YET
                        accumulated_signals.append(processed_card)
                        
                        tool_outputs.append({"tool_call_id": tool.id, "output": json.dumps({"status": "displayed"})})

                if tool_outputs:
                    await asyncio.to_thread(
                        client.beta.threads.runs.submit_tool_outputs,
                        thread_id=run.thread_id, run_id=run.id, tool_outputs=tool_outputs
                    )
                
                # ❌ REMOVED THE EARLY RETURN HERE
                # We continue the loop to let the AI find more signals.
                        
            if run_status.status == 'completed':
                # ✅ RETURN EVERYTHING AT THE END
                if accumulated_signals:
                    return {"ui_type": "signal_list", "items": accumulated_signals}
                
                messages = await asyncio.to_thread(client.beta.threads.messages.list, thread_id=run.thread_id)
                if messages.data:
                    return {"ui_type": "text", "content": messages.data[0].content[0].text.value}
                return {"ui_type": "text", "content": "Scan complete."}
            
            if run_status.status in ['failed', 'cancelled', 'expired']:
                return {"ui_type": "text", "content": "Error processing signal."}

            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
