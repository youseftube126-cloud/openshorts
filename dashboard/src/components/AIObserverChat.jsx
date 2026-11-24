import React, { useState } from 'react';
import { Bot, Loader2 } from 'lucide-react';
export default function AIObserverChat({ logs, transcript, geminiApiKey }) {
    const [analysis, setAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const handleAnalyze = async () => {
        setLoading(true);
        const key = geminiApiKey || localStorage.getItem('geminiKey_v1') || localStorage.getItem('gemini_key');
        const res = await fetch('/api/vexxo/observer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Gemini-Key': key || '' },
            body: JSON.stringify({ logs, transcript })
        });
        const data = await res.json();
        setAnalysis(data.analysis);
        setLoading(false);
    };
    return (
        <div className="card p-4 mt-4">
            <button onClick={handleAnalyze} disabled={loading} className="btn-quiet w-full flex justify-center items-center gap-2">
                {loading ? <Loader2 className="animate-spin" size={16} /> : <Bot size={16} />}
                AI Observer (تحليل الأخطاء)
            </button>
            {analysis && <pre className="mt-4 p-3 bg-paper text-xs whitespace-pre-wrap">{analysis}</pre>}
        </div>
    );
}