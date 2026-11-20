import google.generativeai as genai
import json

def generate_format_from_text(description, api_key):
    if not api_key: return {"error": "No API key"}
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Convert this into JSON: name, font, font_size, primary_color, highlight_color, animation, split_screen. Desc: {description}. Return ONLY JSON."
    try:
        res = model.generate_content(prompt)
        return json.loads(res.text.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        return {"error": str(e)}