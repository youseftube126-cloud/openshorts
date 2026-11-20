import google.generativeai as genai

def analyze_logs_and_content(logs, transcript, api_key):
    if not api_key: return "مفتاح API غير موجود."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Analyze logs: {logs[-2000:]}\nTranscript: {transcript[:2000]}\nReturn analysis in Arabic."
    try:
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        return str(e)