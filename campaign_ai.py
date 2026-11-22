import os
import json
from datetime import datetime, timezone, timedelta
from google import genai

def analyze_campaign(transcript_text, campaign_rules, target_countries):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: 
        return {"error": "GEMINI_API_KEY is missing in the environment."}
    
    client = genai.Client(api_key=api_key)
    
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
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
        )
        text = response.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(text)
    except Exception as e:
        print(f"Gemini Error: {e}")
        return {"error": str(e)}
    
    local_hour = data.get("best_publish_hour_local", 18)
    utc_now = datetime.now(timezone.utc)
    target_time_utc = utc_now.replace(hour=(local_hour - 2) % 24, minute=0, second=0, microsecond=0)
    if target_time_utc < utc_now: 
        target_time_utc += timedelta(days=1)
    data["publish_time_utc"] = target_time_utc.isoformat()
    return data
