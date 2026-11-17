import React from 'react';
const FORMATS = [
  { id: 'podcast_vertical', name: 'Podcast' }, { id: 'cinematic_kinetic', name: 'Cinematic' },
  { id: 'minimalist_word', name: 'Minimalist' }, { id: 'deep_quote', name: 'Deep Quote' },
  { id: 'raw_motivational', name: 'Raw Motivational' }, { id: 'two_speaker', name: '2 Speakers' },
];
export default function FormatSelector({ selected, onSelect }) {
  return (
    <div className="w-full mt-4">
      <label className="block text-sm font-medium text-ink2 mb-2">Video Format</label>
      <div className="grid grid-cols-3 gap-2">
        {FORMATS.map((f) => (
          <button key={f.id} onClick={() => onSelect(f.id)} className={`p-2 text-xs rounded-lg border ${selected === f.id ? 'border-brass bg-brass/10 text-ink font-semibold' : 'border-rule text-muted'}`}>{f.name}</button>
        ))}
      </div>
    </div>
  );
}