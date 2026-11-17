import os
import json
import google.generativeai as genai
from datetime import datetime, timezone, timedelta

def analyze_campaign(transcript_text, campaign_rules, target_countries):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: raise ValueError("GEMINI_API_KEY missing")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert YouTube and TikTok strategist.
    Campaign Rules: {campaign_rules}
    Target Countries: {', '.join(target_countries)}
    Video Transcript (Sample): {transcript_text[:1000]}
    
    Respond strictly in valid JSON:
    {{
        "target_audience": "Detailed description",
        "best_titles": ["Title 1", "Title 2"],
        "best_hashtags": ["#tag1", "#tag2"],
        "best_publish_hour_local": 18
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(text)
    except Exception as e:
        data = {"target_audience": "General", "best_titles": ["Check this out"], "best_hashtags": ["#viral"], "best_publish_hour_local": 18}
    
    local_hour = data.get("best_publish_hour_local", 18)
    utc_now = datetime.now(timezone.utc)
    target_time_utc = utc_now.replace(hour=(local_hour - 2) % 24, minute=0, second=0, microsecond=0)
    if target_time_utc < utc_now: target_time_utc += timedelta(days=1)
    data["publish_time_utc"] = target_time_utc.isoformat()
    return data