import React, { useState } from 'react';
export default function AIFormatStudio({ geminiApiKey }) {
    const [desc, setDesc] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const handleGenerate = async () => {
        setLoading(true);
        const key = geminiApiKey || localStorage.getItem('geminiKey_v1') || localStorage.getItem('gemini_key');
        const res = await fetch('/api/vexxo/format_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Gemini-Key': key || '' },
            body: JSON.stringify({ description: desc })
        });
        const data = await res.json();
        setResult(data);
        setLoading(false);
    };
    return (
        <div className="card p-4 mt-4">
            <textarea className="input-field text-xs w-full mb-2" rows={2} placeholder="عايز فورمات..." value={desc} onChange={e => setDesc(e.target.value)} />
            <button onClick={handleGenerate} disabled={loading || !desc} className="btn-primary w-full text-xs py-2">
                {loading ? 'Creating...' : 'Create Format'}
            </button>
            {result && !result.error && (
                <div className="mt-2 text-xs bg-paper2 p-2 rounded">
                    <p><strong>Name:</strong> {result.name}</p>
                    <p><strong>Font:</strong> {result.font} ({result.font_size}px)</p>
                    <p><strong>Colors:</strong> {result.primary_color} / {result.highlight_color}</p>
                </div>
            )}
        </div>
    );
}