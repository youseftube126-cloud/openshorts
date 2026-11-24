import React, { useState } from 'react';
export default function CampaignWizard({ onAnalyze, geminiApiKey }) {
  const [rules, setRules] = useState('Clippers with fitness, running, sports pages. US, UK audiences.');
  const [country, setCountry] = useState('USA (UTC-5)');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const handleAnalyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const key = geminiApiKey || localStorage.getItem('geminiKey_v1') || localStorage.getItem('gemini_key');
      const res = await fetch('/api/vexxo/campaign_analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Gemini-Key': key || '' },
        body: JSON.stringify({ campaign_rules: rules, target_country_tz: country, transcript_text: 'Sample fitness motivation transcript.' })
      });
      const data = await res.json();
      if (data.error) setError(data.error);
      else { setResult(data); if (onAnalyze) onAnalyze(data); }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="card p-4 space-y-3 mt-4">
      <h3 className="text-sm font-semibold text-ink">AI Campaign Setup</h3>
      <textarea className="input-field w-full text-xs" rows={3} placeholder="Campaign rules..." value={rules} onChange={(e) => setRules(e.target.value)} />
      <select className="input-field w-full text-xs" value={country} onChange={(e) => setCountry(e.target.value)}>
        <option value="USA (UTC-5)">USA (UTC-5)</option>
        <option value="UK (UTC+0)">UK (UTC+0)</option>
        <option value="Saudi Arabia (UTC+3)">Saudi Arabia (UTC+3)</option>
        <option value="Egypt (UTC+2)">Egypt (UTC+2)</option>
        <option value="Australia (UTC+10)">Australia (UTC+10)</option>
      </select>
      <button onClick={handleAnalyze} disabled={loading} className="btn-primary w-full text-xs py-2">
        {loading ? 'Analyzing...' : 'Analyze Campaign'}
      </button>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {result && (
        <div className="text-xs space-y-1 bg-paper2 p-3 rounded-card">
          <p><strong>Audience:</strong> {result.target_audience}</p>
          <p><strong>Titles:</strong> {result.best_titles?.join(' | ')}</p>
          <p><strong>Hashtags:</strong> {result.best_hashtags?.join(' ')}</p>
          <p><strong>Best Time:</strong> {result.best_publish_hour_local}:00 local</p>
        </div>
      )}
    </div>
  );
}

  return (
    <div className="card p-4 space-y-3 mt-4">
      <h3 className="text-sm font-semibold text-ink">AI Campaign Setup</h3>
      <textarea
        className="input-field w-full text-xs"
        rows={3}
        placeholder="Campaign rules..."
        value={rules}
        onChange={(e) => setRules(e.target.value)}
      />
      <select
        className="input-field w-full text-xs"
        value={country}
        onChange={(e) => setCountry(e.target.value)}
      >
        <option value="USA (UTC-5)">USA (UTC-5)</option>
        <option value="UK (UTC+0)">UK (UTC+0)</option>
        <option value="Saudi Arabia (UTC+3)">Saudi Arabia (UTC+3)</option>
        <option value="Egypt (UTC+2)">Egypt (UTC+2)</option>
        <option value="Australia (UTC+10)">Australia (UTC+10)</option>
      </select>
      <button
        onClick={handleAnalyze}
        disabled={loading}
        className="btn-primary w-full text-xs py-2"
      >
        {loading ? 'Analyzing...' : 'Analyze Campaign'}
      </button>
      {error && <p className="text-xs text-red-500">{error}</p>}
      {result && (
        <div className="text-xs space-y-2 bg-paper2 p-3 rounded-card">
          <p><strong>Audience:</strong> {result.target_audience}</p>
          <p><strong>Titles:</strong> {result.best_titles?.join(' | ')}</p>
          <p><strong>Hashtags:</strong> {result.best_hashtags?.join(' ')}</p>
          <p><strong>Best Time:</strong> {result.best_publish_hour_local}:00 local</p>
          <p><strong>Publish UTC:</strong> {result.publish_time_utc}</p>
        </div>
      )}
    </div>
  );
}