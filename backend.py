from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ai_agent import chat_with_agent, toolbox
from logger_utils import log_audit, LOG_FILE
import uvicorn
from langchain_core.messages import HumanMessage, AIMessage
import json
import os
import re
import uuid
import asyncio

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Blender MCP Agentic Chatbot")

# Serve the renders directory
app.mount("/renders", StaticFiles(directory="c:/blundai"), name="renders")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[dict]] = []
    image: Optional[str] = None  # Base64 encoded or URL
    settings: Optional[dict] = {}
    mode: Optional[str] = "cnc"

class ChatResponse(BaseModel):
    response: str
    trace: Optional[List[str]] = []

class JobStartResponse(BaseModel):
    request_id: str

class JobStatusResponse(BaseModel):
    status: str
    trace: List[str] = []
    response: Optional[str] = None
    error: Optional[str] = None
    segment_current: Optional[int] = None
    segment_total: Optional[int] = None
    plan_preview: Optional[str] = None

JOB_STORE: Dict[str, Dict[str, Any]] = {}

SEGMENT_RE = re.compile(r"Segment\s+(\d+)\s*/\s*(\d+)")
PLAN_PREVIEW_PREFIX = "PLAN_PREVIEW:"


def derive_status_extras(trace: List[str]) -> Dict[str, Any]:
    seg_current: Optional[int] = None
    seg_total: Optional[int] = None
    plan_preview: Optional[str] = None
    for entry in trace:
        m = SEGMENT_RE.search(entry)
        if m:
            seg_current = int(m.group(1))
            seg_total = int(m.group(2))
        if entry.startswith(PLAN_PREVIEW_PREFIX):
            plan_preview = entry[len(PLAN_PREVIEW_PREFIX):].strip()
    return {
        "segment_current": seg_current,
        "segment_total": seg_total,
        "plan_preview": plan_preview,
    }

def read_audit_entries() -> List[dict]:
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def dict_to_messages(history):
    msgs = []
    for m in history:
        if m['role'] == 'user':
            msgs.append(HumanMessage(content=m['content']))
        elif m['role'] == 'assistant':
            msgs.append(AIMessage(content=m['content']))
    return msgs

async def run_chat_job(request_id: str, request: ChatRequest):
    try:
        if request.settings is None:
            request.settings = {}
        request.settings["mode"] = request.mode

        log_audit("API_REQUEST", {"request_id": request_id, "message": request.message, "settings": request.settings})
        audit_before = read_audit_entries()
        audit_start_idx = len(audit_before)
        history = dict_to_messages(request.history)

        def progress_logger(msg: str):
            JOB_STORE[request_id]["trace"].append(msg)
            log_audit("PIPELINE_TRACE", {"request_id": request_id, "step": msg})

        result = await chat_with_agent(
            request.message,
            history,
            request.image,
            request.settings,
            progress_callback=progress_logger
        )
        if isinstance(result, dict):
            response_text = result.get("response", "")
            trace = result.get("trace", []) or JOB_STORE[request_id]["trace"]
        else:
            response_text = str(result)
            trace = JOB_STORE[request_id]["trace"]

        if not trace:
            audit_after = read_audit_entries()
            new_entries = audit_after[audit_start_idx:]
            fallback_trace = []
            for entry in new_entries[-80:]:
                action = entry.get("action", "UNKNOWN")
                details = entry.get("details", {})
                detail_str = json.dumps(details, ensure_ascii=True)[:240]
                fallback_trace.append(f"{action}: {detail_str}")
            trace = fallback_trace

        JOB_STORE[request_id]["trace"] = trace
        JOB_STORE[request_id]["response"] = response_text
        JOB_STORE[request_id]["status"] = "completed"
        log_audit("API_RESPONSE", {"request_id": request_id, "response_preview": response_text[:100], "trace_steps": len(trace)})
    except Exception as e:
        JOB_STORE[request_id]["status"] = "failed"
        JOB_STORE[request_id]["error"] = str(e)
        log_audit("API_ERROR", {"request_id": request_id, "error": str(e)})

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    request_id = str(uuid.uuid4())
    JOB_STORE[request_id] = {"status": "running", "trace": [], "response": None, "error": None}
    await run_chat_job(request_id, request)
    job = JOB_STORE[request_id]
    if job["status"] == "failed":
        raise HTTPException(status_code=500, detail=job["error"])
    return ChatResponse(response=job["response"] or "", trace=job["trace"])

@app.post("/chat/start", response_model=JobStartResponse)
async def chat_start(request: ChatRequest):
    request_id = str(uuid.uuid4())
    JOB_STORE[request_id] = {"status": "running", "trace": [], "response": None, "error": None}
    asyncio.create_task(run_chat_job(request_id, request))
    return JobStartResponse(request_id=request_id)

@app.get("/chat/status/{request_id}", response_model=JobStatusResponse)
async def chat_status(request_id: str):
    job = JOB_STORE.get(request_id)
    if not job:
        raise HTTPException(status_code=404, detail="Request not found")
    trace = job.get("trace", [])
    extras = derive_status_extras(trace)
    return JobStatusResponse(
        status=job["status"],
        trace=trace,
        response=job.get("response"),
        error=job.get("error"),
        **extras,
    )

@app.on_event("shutdown")
async def shutdown_event():
    await toolbox.disconnect()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
