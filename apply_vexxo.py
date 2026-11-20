import os

files = {
    "ai_observer.py": """import google.generativeai as genai

def analyze_logs_and_content(logs, transcript, api_key):
    if not api_key: return "مفتاح API غير موجود."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"Analyze logs: {logs[-2000:]}\\nTranscript: {transcript[:2000]}\\nReturn analysis in Arabic."
    try:
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        return str(e)""",
    "format_generator.py": """import google.generativeai as genai
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
        return {"error": str(e)}""",
    "vexxo_routes.py": """from fastapi import APIRouter, Request
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
    return generate_format_from_text(req.description, api_key)""",
    "dashboard/src/components/AIObserverChat.jsx": """import React, { useState } from 'react';
import { Bot, Loader2 } from 'lucide-react';
export default function AIObserverChat({ logs, transcript }) {
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const handleAnalyze = async () => {
        setLoading(true);
        const res = await fetch('/api/vexxo/observer', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Gemini-Key': localStorage.getItem('gemini_key') }, body: JSON.stringify({ logs, transcript }) });
        const data = await res.json();
        setAnalysis(data.analysis);
        setLoading(false);
    };
    return (
        <div className="card p-4 mt-4">
            <button onClick={handleAnalyze} disabled={loading} className="btn-quiet w-full flex justify-center items-center gap-2">
                {loading ? <Loader2 className="animate-spin" /> : <Bot size={16} />} AI Observer (تحليل الأخطاء)
            </button>
            {analysis && <pre className="mt-4 p-3 bg-paper text-xs whitespace-pre-wrap">{analysis}</pre>}
        </div>
    );
}""",
    "dashboard/src/components/AIFormatStudio.jsx": """import React, { useState } from 'react';
export default function AIFormatStudio() {
    const [desc, setDesc] = useState('');
    const [loading, setLoading] = useState(false);
    const handleGenerate = async () => {
        setLoading(true);
        const res = await fetch('/api/vexxo/format_generate', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Gemini-Key': localStorage.getItem('gemini_key') }, body: JSON.stringify({ description: desc }) });
        const data = await res.json();
        alert("Format: " + JSON.stringify(data));
        setLoading(false);
    };
    return (
        <div className="card p-4 mt-4">
            <textarea className="input-field text-xs w-full mb-2" rows={2} placeholder="عايز فورمات..." value={desc} onChange={e => setDesc(e.target.value)} />
            <button onClick={handleGenerate} disabled={loading || !desc} className="btn-primary w-full text-xs py-2">Create Format</button>
        </div>
    );
}"""
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

# تعديل app.py
with open("app.py", "r", encoding="utf-8") as f:
    code = f.read()
if "from vexxo_routes import router" not in code:
    code = "from vexxo_routes import router as vexxo_router\n" + code
    code += "\n\napp.include_router(vexxo_router)\n"
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(code)

# تعديل App.jsx
with open("dashboard/src/App.jsx", "r", encoding="utf-8") as f:
    app_jsx = f.read()
if "import AIObserverChat" not in app_jsx:
    app_jsx = app_jsx.replace("import FormatSelector from './components/FormatSelector';", "import AIObserverChat from './components/AIObserverChat';\nimport AIFormatStudio from './components/AIFormatStudio';\nimport FormatSelector from './components/FormatSelector';")
    app_jsx = app_jsx.replace("<MediaInput onProcess={handleProcess} isProcessing={status === 'processing'} />", "<MediaInput onProcess={handleProcess} isProcessing={status === 'processing'} />\n                <AIObserverChat logs={logs} transcript={results?.transcript} />\n                <AIFormatStudio />")
    with open("dashboard/src/App.jsx", "w", encoding="utf-8") as f:
        f.write(app_jsx)

print("✅ Done! All features applied successfully.")