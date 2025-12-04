import os
import json
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
# Replace with your actual Assistant ID or set as env var
ASSISTANT_ID = os.getenv("ASSISTANT_ID", "asst_6AnFZkW7f6Jhns774D9GNWXr")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

# --- RADICAL IMPROVEMENT: CORS ---
# Allows your UI (hosted anywhere) to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace "*" with your specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

# --- LOGIC ---
def craft_widget_response(tool_args):
    """Refines the raw AI data into a frontend-ready JSON object."""
    # 1. Fallback URL Logic
    url = tool_args.get("sourceURL") or tool_args.get("url")
    if not url:
        query = tool_args.get("title", "").replace(" ", "+")
        url = f"https://www.google.com/search?q={query}"
    
    # 2. Add extra UI flags
    tool_args["final_url"] = url
    tool_args["ui_type"] = "signal_card" # Tells frontend to render a card
    return tool_args

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        print(f"User: {req.message}")
        
        # 1. Run Assistant
        run = await asyncio.to_thread(
            client.beta.threads.create_and_run,
            assistant_id=ASSISTANT_ID,
            thread={"messages": [{"role": "user", "content": req.message}]}
        )

        # 2. Poll Loop
        while True:
            run_status = await asyncio.to_thread(
                client.beta.threads.runs.retrieve, thread_id=run.thread_id, run_id=run.id
            )

            if run_status.status == 'requires_action':
                # Handle Tool Call (The Signal Card)
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                for tool in tool_calls:
                    if tool.function.name == "display_signal_card":
                        args = json.loads(tool.function.arguments)
                        # Immediately return the visual card data to frontend
                        return craft_widget_response(args)
                        
            if run_status.status == 'completed':
                # Handle Standard Text
                messages = await asyncio.to_thread(
                    client.beta.threads.messages.list, thread_id=run.thread_id
                )
                text = messages.data[0].content[0].text.value
                return {"ui_type": "text", "content": text}
            
            if run_status.status in ['failed', 'cancelled', 'expired']:
                return {"ui_type": "text", "content": "I encountered an error processing that signal."}

            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
