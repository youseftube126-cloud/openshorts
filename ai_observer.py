from google import genai

def analyze_logs_and_content(logs, transcript, api_key):
    if not api_key: return "مفتاح API غير موجود."
    client = genai.Client(api_key=api_key)
    prompt = f"Analyze logs: {logs[-2000:]}\nTranscript: {transcript[:2000]}\nReturn analysis in Arabic."
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return res.text
    except Exception as e:
        return str(e)