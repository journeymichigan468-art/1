from __future__ import annotations

import os
import json
import asyncio
from typing import Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials


# -----------------------------
# Config
# -----------------------------
APP_NAME = os.getenv("APP_NAME", "MA-13-Agents-Proxy")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_BASE = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com")
MOCK_MODE = (GEMINI_API_KEY.strip() == "")

# Firebase Admin credentials (choose ONE approach)
# A) Path to service account json file:
FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "").strip()
# B) Service account json content in env:
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()

# If you want to allow unauthenticated calls temporarily (dev only):
ALLOW_ANON = os.getenv("ALLOW_ANON", "false").lower() == "true"


# -----------------------------
# Firebase Admin Init
# -----------------------------
def init_firebase_admin() -> None:
    if firebase_admin._apps:
        return  # already initialized

    cred_obj = None

    if FIREBASE_SERVICE_ACCOUNT_PATH:
        cred_obj = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
    elif FIREBASE_SERVICE_ACCOUNT_JSON:
        cred_dict = json.loads(FIREBASE_SERVICE_ACCOUNT_JSON)
        cred_obj = credentials.Certificate(cred_dict)

    if cred_obj is None:
        # You can still run server, but auth verify will fail
        # (useful when you want mock mode + ALLOW_ANON in dev)
        return

    firebase_admin.initialize_app(cred_obj)

init_firebase_admin()


# -----------------------------
# FastAPI App + CORS
# -----------------------------
app = FastAPI(title=APP_NAME)

# DEV: allow all. PROD: restrict to your Mino/web domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Auth Dependency
# -----------------------------
bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
) -> Optional[Dict[str, Any]]:
    """
    Verifies Firebase ID token from: Authorization: Bearer <token>
    Returns decoded token (contains uid, claims).
    """
    if creds is None:
        if ALLOW_ANON:
            return None
        raise HTTPException(status_code=401, detail="Missing Authorization Bearer token")

    token = creds.credentials.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty Bearer token")

    if not firebase_admin._apps:
        raise HTTPException(
            status_code=500,
            detail="Firebase Admin not initialized. Set FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_SERVICE_ACCOUNT_JSON"
        )

    try:
        decoded = fb_auth.verify_id_token(token)  # verifies signature, exp, aud, iss
        return decoded
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Firebase ID token: {str(e)}")


# -----------------------------
# Models
# -----------------------------
class AgentRunRequest(BaseModel):
    agentName: str = Field(..., min_length=2, max_length=40)
    subtask: str = Field(..., min_length=2, max_length=5000)
    userTask: str = Field("", max_length=20000)

class AgentRunResponse(BaseModel):
    text: str

class WhoAmIResponse(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    claims: Optional[dict] = None


# -----------------------------
# Agent prompts
# -----------------------------
AGENT_SYSTEM_PROMPTS: Dict[str, str] = {
    "CodeAI": "You are CodeAI, an advanced programmer. Return concise, runnable code. Use markdown code fences.",
    "DesignAI": "You are DesignAI, a UI/UX expert. Provide a concise design concept, colors (hex), layout strategy.",
    "SecurityAI": "You are SecurityAI. Identify key risks and provide mitigation steps. Be specific and concise.",
    "BusinessAI": "You are BusinessAI. Provide revenue potential, pricing tiers, and GTM notes concisely.",
    "ResearchAI": "You are ResearchAI. Provide up-to-date insights with bullet points.",
    "NetworkAI": "You are NetworkAI. Provide API endpoints, payload models, auth approach, and integration notes.",
    "MarketingAI": "You are MarketingAI. Suggest a compelling name/value proposition, target audience, and tagline.",
    "AnalyticsAI": "You are AnalyticsAI. Provide KPIs and measurement plan.",
    "TestingAI": "You are TestingAI. Provide high-priority test cases (input/expected).",
    "CreativeAI": "You are CreativeAI. Provide creative mission/brand voice snippets.",
    "HackerAI": "You are HackerAI. Describe one realistic exploit scenario and how to defend.",
    "DeepSeekAI": "You are DeepSeekAI. Explain ML enhancement ideas (RAG, embeddings, personalization).",
    "CopilotAI": "You are CopilotAI. Produce a clean 5-step deployment/integration plan in Markdown.",
    "Lovable": "You are Lovable, a product-focused AI engineer. Design and explain polished MVP features with clear UX details and implementation-ready steps.",
    "@Lovable": "You are Lovable, a product-focused AI engineer. Design and explain polished MVP features with clear UX details and implementation-ready steps.",
}

def build_system_prompt(agent_name: str) -> str:
    return AGENT_SYSTEM_PROMPTS.get(agent_name, "You are a specialized agent. Complete the task concisely.")

def build_user_prompt(req: AgentRunRequest, user: Optional[dict]) -> str:
    uid_line = f"Firebase UID: {user.get('uid')}\n" if user else "Firebase UID: (anonymous dev)\n"
    return (
        uid_line +
        f"Agent: {req.agentName}\n\n"
        f"User main task:\n{req.userTask}\n\n"
        f"Subtask:\n{req.subtask}\n\n"
        "Return only the final answer."
    )

def mock_response(req: AgentRunRequest, user: Optional[dict]) -> str:
    uid = user.get("uid") if user else "(anonymous dev)"
    return (
        f"[MOCK MODE]\nuid: {uid}\nagentName: {req.agentName}\n\n"
        f"Subtask:\n- {req.subtask}\n\n"
        "Set GEMINI_API_KEY to enable real LLM output."
    )

async def call_gemini(system_prompt: str, user_prompt: str) -> str:
    url = f"{GEMINI_API_BASE}/v1beta/models/{GEMINI_MODEL}:generateContent"
    params = {"key": GEMINI_API_KEY}
    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
    }

    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        last_err: Optional[str] = None
        delay = 1.0
        for _ in range(4):
            try:
                r = await client.post(url, params=params, json=payload)
                if r.status_code == 200:
                    data = r.json()
                    candidates = data.get("candidates") or []
                    parts = (((candidates[0] or {}).get("content") or {}).get("parts")) or []
                    text = (parts[0].get("text") if parts else "") or ""
                    return text.strip() or "Empty response text."
                last_err = f"{r.status_code} {r.text}"
            except Exception as e:
                last_err = str(e)

            await asyncio.sleep(delay)
            delay *= 2

        raise RuntimeError(f"Gemini call failed: {last_err}")


# -----------------------------
# Routes
# -----------------------------
@app.get("/health")
def health():
    return {
        "ok": True,
        "app": APP_NAME,
        "mock_mode": MOCK_MODE,
        "firebase_admin_initialized": bool(firebase_admin._apps),
        "model": GEMINI_MODEL,
    }

@app.get("/whoami", response_model=WhoAmIResponse)
async def whoami(user=Depends(get_current_user)):
    if user is None:
        return WhoAmIResponse(uid=None, email=None, claims=None)
    return WhoAmIResponse(
        uid=user.get("uid"),
        email=user.get("email"),
        claims={k: v for k, v in user.items() if k not in ("iat", "exp")}
    )

@app.post("/agent-run", response_model=AgentRunResponse)
async def agent_run(req: AgentRunRequest, user=Depends(get_current_user)):
    system_prompt = build_system_prompt(req.agentName)
    user_prompt = build_user_prompt(req, user)

    try:
        if MOCK_MODE:
            return AgentRunResponse(text=mock_response(req, user))

        text = await call_gemini(system_prompt, user_prompt)
        return AgentRunResponse(text=text)

    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
