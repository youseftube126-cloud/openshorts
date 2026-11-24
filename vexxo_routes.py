from fastapi import APIRouter, Request
from campaign_ai import analyze_campaign
from ai_observer import analyze_logs_and_content
from format_generator import generate_format_from_text
import os

router = APIRouter()

@router.post("/api/vexxo/campaign_analyze")
async def campaign_analyze(request: Request):
    body = await request.json()
    api_key = request.headers.get("X-Gemini-Key") or os.environ.get("GEMINI_API_KEY", "")
    os.environ["GEMINI_API_KEY"] = api_key
    result = analyze_campaign(
        body.get("transcript_text", ""),
        body.get("campaign_rules", ""),
        [body.get("target_country_tz", "UTC")]
    )
    return result

@router.post("/api/vexxo/observer")
async def observer(request: Request):
    body = await request.json()
    api_key = request.headers.get("X-Gemini-Key") or os.environ.get("GEMINI_API_KEY", "")
    result = analyze_logs_and_content(
        body.get("logs", []),
        body.get("transcript", ""),
        api_key
    )
    return {"analysis": result}

@router.post("/api/vexxo/format_generate")
async def format_generate(request: Request):
    body = await request.json()
    api_key = request.headers.get("X-Gemini-Key") or os.environ.get("GEMINI_API_KEY", "")
    result = generate_format_from_text(body.get("description", ""), api_key)
    return result
