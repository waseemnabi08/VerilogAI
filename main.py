# main.py
import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx


# ========= Config =========
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY not set in .env file")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
FRONTEND_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

# VerilogAI system prompts
SYSTEM_BASE = (
    "You are VerilogAI — an expert assistant for hardware design, Verilog/SystemVerilog, "
    "FPGA development, and testbench generation. Be precise and follow synthesizable best practices."
)

SYSTEM_GENERATE = (
    SYSTEM_BASE +
    "\nRules:\n"
    "- Target Verilog-2001 (synthesizable).\n"
    "- Use non-blocking (<=) in sequential always blocks; blocking (=) in combinational where appropriate.\n"
    "- Avoid latches; use complete sensitivity lists or always @(*) for combinational logic.\n"
    "- Provide concise comments.\n"
    "- No $display/$monitor unless explicitly requested.\n"
)

SYSTEM_DEBUG = (
    SYSTEM_BASE +
    "\nTask: Review and fix the user's Verilog. Identify syntax, latch inference, reset/timing issues, and non-synthesizable constructs. "
    "Return a short list of issues, then the corrected code."
)

SYSTEM_EXPLAIN = (
    SYSTEM_BASE +
    "\nTask: Explain the given Verilog for a learner. Describe module I/O, regs/wires, always blocks, and behavior step-by-step."
)

# ========= FastAPI app =========
app = FastAPI(title="VerilogAI - Backend (OpenRouter)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= Request models =========
class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Dict[str, str]]] = None  # Fixed syntax here

class GenerateRequest(BaseModel):
    spec: str  # natural language spec of the module you want

class CodeRequest(BaseModel):
    code: str  # raw Verilog code

import json
# ========= Helper to call Gemini =========
async def call_gemini(messages: List[Dict[str, str]]) -> str:
    # Gemini expects a list of content blocks, each with a role and parts
    contents = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    payload = {"contents": contents}
    url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(url, headers=headers, data=json.dumps(payload))
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Malformed response: {e}\nRaw: {data}")

# ========= Routes =========
@app.get("/health")
async def health():
    return {"status": "ok"}

# General chat with conversation history support
@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        messages = [{"role": "system", "content": SYSTEM_BASE}]

        # Add conversation history if provided
        if req.history:
            messages.extend(req.history)

        # Add current user message
        messages.append({"role": "user", "content": req.prompt})

        reply = await call_gemini(messages=messages)
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate synthesizable Verilog from a natural-language spec
@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        user_msg = (
            "Generate a synthesizable Verilog-2001 module from this spec.\n"
            "Include: clear module/ports, parameters if relevant, proper resets, and brief comments.\n\n"
            f"Spec:\n{req.spec}"
        )
        reply = await call_gemini(
            messages=[
                {"role": "system", "content": SYSTEM_GENERATE},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Debug/fix user-provided Verilog code
@app.post("/debug")
async def debug(req: CodeRequest):
    try:
        user_msg = (
            "Analyze and correct the following Verilog. "
            "First list issues; then provide corrected code in a single fenced block.\n\n"
            f"Code:\n{req.code}"
        )
        reply = await call_gemini(
            messages=[
                {"role": "system", "content": SYSTEM_DEBUG},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Explain user-provided Verilog code
@app.post("/explain")
async def explain(req: CodeRequest):
    try:
        user_msg = (
            "Explain clearly for a beginner. Cover ports, signals, always blocks, and overall behavior.\n\n"
            f"Code:\n{req.code}"
        )
        reply = await call_gemini(
            messages=[
                {"role": "system", "content": SYSTEM_EXPLAIN},
                {"role": "user", "content": user_msg},
            ]
        )
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))