import React, { useState } from 'react';
export default function CampaignWizard({ onAnalyze }) {
  const [rules, setRules] = useState('');
  const [country, setCountry] = useState('Egypt');
  const [loading, setLoading] = useState(false);

  const handleAnalyze = () => {
    setLoading(true);
    onAnalyze({ target_countries: [country], campaign_rules: rules }).finally(() => setLoading(false));
  };

  return (
    <div className="card p-4 space-y-3 mt-4">
      <h3 className="text-sm font-semibold text-ink">AI Campaign Setup</h3>
      <textarea className="input-field w-full text-xs" rows={2} placeholder="Campaign rules (e.g., Target youth...)" value={rules} onChange={(e) => setRules(e.target.value)} />
      <select className="input-field w-full text-xs" value={country} onChange={(e) => setCountry(e.target.value)}>
        <option value="Egypt">Egypt (UTC+2)</option>
        <option value="Saudi Arabia">Saudi Arabia (UTC+3)</option>
        <option value="United States">USA (UTC-5)</option>
      </select>
      <button onClick={handleAnalyze} disabled={loading} className="btn-primary w-full text-xs py-2">
        {loading ? 'Analyzing...' : 'Generate Metadata & Schedule'}
      </button>
    </div>
  );
}