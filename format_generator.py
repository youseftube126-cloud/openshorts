from google import genai
import json

def generate_format_from_text(description, api_key):
    if not api_key: return {"error": "No API key"}
    client = genai.Client(api_key=api_key)
    prompt = f"Convert this into JSON: name, font, font_size, primary_color, highlight_color, animation, split_screen. Desc: {description}. Return ONLY JSON."
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return json.loads(res.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"error": str(e)}