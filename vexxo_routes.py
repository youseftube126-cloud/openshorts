from fastapi import APIRouter, Request
from pydantic import BaseModel
from ai_observer import analyze_logs_and_content
from format_generator import generate_format_from_text
import os

router = APIRouter()

class ObserverReq(BaseModel):
    logs: list
    transcript: str

@router.post("/api/vexxo/observer")
async def observer_endpoint(req: ObserverReq, request: Request):
    api_key = request.headers.get("X-Gemini-Key") or os.environ.get("GEMINI_API_KEY")
    return {"analysis": analyze_logs_and_content(req.logs, req.transcript, api_key)}

class FormatGenReq(BaseModel):
    description: str

@router.post("/api/vexxo/format_generate")
async def format_gen_endpoint(req: FormatGenReq, request: Request):
    api_key = request.headers.get("X-Gemini-Key") or os.environ.get("GEMINI_API_KEY")
    return generate_format_from_text(req.description, api_key)