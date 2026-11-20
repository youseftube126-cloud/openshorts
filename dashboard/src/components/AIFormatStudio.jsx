import React, { useState } from 'react';
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
}