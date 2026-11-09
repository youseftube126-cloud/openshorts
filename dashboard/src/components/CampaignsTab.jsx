import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Plus, ArrowLeft, Trash2, Loader2, ImagePlus, Send, Star, Link2, MessageSquare,
  ListVideo, ScrollText, Sparkles, X,
} from 'lucide-react';
import { apiFetch, apiJson } from '../lib/api';
import { getApiUrl } from '../config';

// Campaigns: one workspace per campaign (e.g. a Whop clipping campaign) with its
// rules, its videos, the analytics screenshots of each posted video, and an AI
// coach that reads all of it and says what went wrong and what to improve.

const errText = (e) => e?.detail?.detail || e?.detail || e?.message || 'Something went wrong';

const jsonOpts = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

// Tiny markdown: **bold**, "- " bullets, blank-line paragraphs. The coach answers
// in plain text with a little structure; no need for a full renderer.
function Rich({ text }) {
  const inline = (line) => line.split(/(\*\*[^*]+\*\*)/g).map((part, i) => (
    part.startsWith('**') && part.endsWith('**')
      ? <strong key={i} className="text-ink">{part.slice(2, -2)}</strong>
      : <React.Fragment key={i}>{part}</React.Fragment>
  ));
  return (
    <div dir="auto" className="space-y-1.5 text-sm leading-relaxed">
      {text.split('\n').map((raw, i) => {
        const line = raw.trimEnd();
        if (!line.trim()) return <div key={i} className="h-1" />;
        const bullet = line.match(/^\s*[-*]\s+(.*)$/);
        if (bullet) return <div key={i} className="flex gap-2"><span className="text-muted">•</span><span>{inline(bullet[1])}</span></div>;
        return <div key={i}>{inline(line)}</div>;
      })}
    </div>
  );
}

// ---------------------------------------------------------------- video card

function VideoCard({ campaignId, video, onChanged, onDeleted }) {
  const [form, setForm] = useState({
    title: video.title, hook: video.hook, posted_url: video.posted_url, notes: video.notes,
  });
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef(null);

  const save = async (field) => {
    if (form[field] === video[field]) return;
    try {
      const updated = await apiJson(`/api/campaigns/${campaignId}/videos/${video.id}`,
        jsonOpts('PATCH', { [field]: form[field] }));
      onChanged(updated);
    } catch (e) { setError(errText(e)); }
  };

  const upload = async (files) => {
    const images = Array.from(files).filter((f) => f.type.startsWith('image/'));
    if (!images.length) return;
    setUploading(true); setError('');
    try {
      for (const file of images) {
        const fd = new FormData();
        fd.append('file', file);
        const res = await apiFetch(`/api/campaigns/${campaignId}/videos/${video.id}/shots`, { method: 'POST', body: fd });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Upload failed');
      }
      onChanged();
    } catch (e) { setError(errText(e)); }
    setUploading(false);
  };

  // Ctrl+V of a screenshot anywhere on the card attaches it.
  const onPaste = (e) => {
    const files = Array.from(e.clipboardData?.files || []);
    if (files.some((f) => f.type.startsWith('image/'))) { e.preventDefault(); upload(files); }
  };

  const removeShot = async (id) => {
    try { await apiJson(`/api/campaigns/shots/${id}`, { method: 'DELETE' }); onChanged(); }
    catch (e) { setError(errText(e)); }
  };

  const remove = async () => {
    if (!window.confirm('Remove this video from the campaign? Its screenshots are deleted too.')) return;
    try { await apiJson(`/api/campaigns/${campaignId}/videos/${video.id}`, { method: 'DELETE' }); onDeleted(video.id); }
    catch (e) { setError(errText(e)); }
  };

  const field = 'input-field w-full text-sm';
  return (
    <div className="card p-4 flex flex-col sm:flex-row gap-4" onPaste={onPaste} tabIndex={-1}>
      {video.video_url ? (
        <video src={getApiUrl(video.video_url)} controls preload="metadata"
          className="w-full sm:w-36 aspect-[9/16] object-cover rounded-input bg-black shrink-0" />
      ) : (
        <div className="hidden sm:flex w-36 aspect-[9/16] rounded-input bg-paper3 items-center justify-center text-muted shrink-0">
          <ListVideo size={22} />
        </div>
      )}

      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-start gap-2">
          <input dir="auto" className={`${field} font-medium`} value={form.title} placeholder="title"
            onChange={(e) => setForm({ ...form, title: e.target.value })} onBlur={() => save('title')} />
          {video.score != null && (
            <span className="text-micro font-mono uppercase text-brass shrink-0 pt-2" title="virality score">{video.score}</span>
          )}
          <button onClick={remove} className="p-2 text-muted hover:text-ink shrink-0" aria-label="remove video"><Trash2 size={15} /></button>
        </div>
        <input dir="auto" className={field} value={form.hook} placeholder="hook (first line of the video)"
          onChange={(e) => setForm({ ...form, hook: e.target.value })} onBlur={() => save('hook')} />
        <div className="flex items-center gap-2">
          <Link2 size={14} className="text-muted shrink-0" />
          <input className={field} value={form.posted_url} placeholder="posted link (YouTube / TikTok / ...) — fill it when you post"
            onChange={(e) => setForm({ ...form, posted_url: e.target.value })} onBlur={() => save('posted_url')} />
        </div>
        <textarea dir="auto" rows={2} className={field} value={form.notes} placeholder="your notes (what you changed, what you noticed)"
          onChange={(e) => setForm({ ...form, notes: e.target.value })} onBlur={() => save('notes')} />

        <div>
          <div className="flex flex-wrap gap-2 items-center">
            {video.shots.map((s) => (
              <div key={s.id} className="relative group">
                <a href={getApiUrl(`/api/campaigns/shots/${s.id}/image`)} target="_blank" rel="noreferrer">
                  <img src={getApiUrl(`/api/campaigns/shots/${s.id}/image`)} alt="analytics"
                    className="h-16 w-24 object-cover rounded-input border border-rule" />
                </a>
                <button onClick={() => removeShot(s.id)} aria-label="remove screenshot"
                  className="absolute -top-1.5 -right-1.5 bg-paper2 border border-rule rounded-full p-0.5 text-muted hover:text-ink opacity-0 group-hover:opacity-100">
                  <X size={11} />
                </button>
              </div>
            ))}
            <button onClick={() => fileRef.current?.click()} disabled={uploading}
              className="btn-quiet px-3 py-1.5 text-xs">
              {uploading ? <Loader2 size={13} className="animate-spin" /> : <ImagePlus size={13} />}
              analytics screenshot
            </button>
            <input ref={fileRef} type="file" accept="image/*" multiple className="hidden"
              onChange={(e) => { upload(e.target.files); e.target.value = ''; }} />
          </div>
          <p className="text-micro text-muted mt-1.5">tip: click the card and press Ctrl+V to paste a screenshot</p>
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- panes

function VideosPane({ campaign, reload, setCampaign }) {
  const [postedOnly, setPostedOnly] = useState(false);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({ title: '', posted_url: '' });
  const [error, setError] = useState('');

  const videos = campaign.videos.filter((v) => !postedOnly || v.posted_url);

  const addManual = async () => {
    try {
      await apiJson(`/api/campaigns/${campaign.id}/videos`, jsonOpts('POST', draft));
      setDraft({ title: '', posted_url: '' }); setAdding(false); reload();
    } catch (e) { setError(errText(e)); }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setPostedOnly(false)} className={`btn-quiet px-3 py-1.5 text-xs ${!postedOnly ? 'text-ink' : ''}`}>
          all ({campaign.videos.length})
        </button>
        <button onClick={() => setPostedOnly(true)} className={`btn-quiet px-3 py-1.5 text-xs ${postedOnly ? 'text-ink' : ''}`}>
          posted ({campaign.videos.filter((v) => v.posted_url).length})
        </button>
        <button onClick={() => setAdding(!adding)} className="btn-quiet px-3 py-1.5 text-xs ml-auto">
          <Plus size={13} /> add a video by hand
        </button>
      </div>

      {adding && (
        <div className="card p-3 flex flex-col sm:flex-row gap-2">
          <input dir="auto" className="input-field text-sm flex-1" placeholder="title" value={draft.title}
            onChange={(e) => setDraft({ ...draft, title: e.target.value })} />
          <input className="input-field text-sm flex-1" placeholder="posted link (optional)" value={draft.posted_url}
            onChange={(e) => setDraft({ ...draft, posted_url: e.target.value })} />
          <button onClick={addManual} className="btn-primary px-4 py-2 text-sm">add</button>
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {campaign.videos.length === 0 ? (
        <div className="card p-8 text-center text-muted text-sm">
          No videos yet. Pick this campaign as active (the star above), then generate clips in the
          Clip Generator: every finished clip lands here automatically.
        </div>
      ) : videos.length === 0 ? (
        <div className="card p-6 text-center text-muted text-sm">No posted videos yet. Paste a posted link on a video to mark it as posted.</div>
      ) : videos.map((v) => (
        <VideoCard key={v.id} campaignId={campaign.id} video={v} onChanged={reload}
          onDeleted={(id) => setCampaign({ ...campaign, videos: campaign.videos.filter((x) => x.id !== id) })} />
      ))}
    </div>
  );
}

function RulesPane({ campaign, onSaved }) {
  const [rules, setRules] = useState(campaign.rules);
  const [state, setState] = useState('');
  const save = async () => {
    setState('saving');
    try { await apiJson(`/api/campaigns/${campaign.id}`, jsonOpts('PATCH', { rules })); onSaved(rules); setState('saved'); }
    catch (e) { setState(errText(e)); }
  };
  return (
    <div className="card p-4 space-y-3">
      <p className="text-sm text-muted">Paste the campaign rules exactly as the brand wrote them (length, content allowed, hashtags,
        payout conditions, banned content). The AI coach checks every video against this text.</p>
      <textarea dir="auto" rows={14} className="input-field w-full text-sm" value={rules} onChange={(e) => setRules(e.target.value)}
        placeholder="e.g. Videos must be 30-60 seconds. No copyrighted music. Tag @brand. Pay: $1 per 1000 views..." />
      <div className="flex items-center gap-3">
        <button onClick={save} className="btn-primary px-5 py-2 text-sm">save rules</button>
        {state === 'saved' && <span className="text-xs text-muted">saved</span>}
        {state && state !== 'saved' && state !== 'saving' && <span className="text-xs text-red-400">{state}</span>}
      </div>
    </div>
  );
}

const REVIEW_PROMPT = 'Review this whole campaign now. Check each video against the rules, compare the analytics '
  + 'screenshots, and list the mistakes I made and the improvements I should apply on the next videos, most important first.';

function ChatPane({ campaign, apiKey }) {
  const [messages, setMessages] = useState(null);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    apiJson(`/api/campaigns/${campaign.id}/chat`).then((d) => setMessages(d.messages)).catch((e) => setError(errText(e)));
  }, [campaign.id]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, sending]);

  const send = async (message) => {
    const q = (message ?? text).trim();
    if (!q || sending) return;
    setSending(true); setError(''); setText('');
    setMessages((m) => [...(m || []), { role: 'user', content: q }]);
    try {
      const headers = { 'Content-Type': 'application/json', ...(apiKey ? { 'X-Gemini-Key': apiKey } : {}) };
      const d = await apiJson(`/api/campaigns/${campaign.id}/chat`, { method: 'POST', headers, body: JSON.stringify({ message: q }) });
      setMessages((m) => [...m, { role: 'assistant', content: d.reply }]);
    } catch (e) {
      setError(errText(e));
      setMessages((m) => m.slice(0, -1)); setText(q);
    }
    setSending(false);
  };

  const clear = async () => {
    if (!window.confirm('Clear this conversation?')) return;
    await apiJson(`/api/campaigns/${campaign.id}/chat`, { method: 'DELETE' }); setMessages([]);
  };

  const shots = campaign.videos.reduce((n, v) => n + v.shots.length, 0);
  return (
    <div className="card p-4 flex flex-col" style={{ minHeight: '60vh' }}>
      <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-rule">
        <p className="text-xs text-muted flex-1">
          The coach sees: the rules, {campaign.videos.length} video{campaign.videos.length === 1 ? '' : 's'}
          {' '}and {shots} analytics screenshot{shots === 1 ? '' : 's'} (the newest 12).
        </p>
        <button onClick={() => send(REVIEW_PROMPT)} disabled={sending} className="btn-primary px-4 py-1.5 text-xs">
          <Sparkles size={13} /> review campaign
        </button>
        {messages?.length > 0 && <button onClick={clear} className="btn-quiet px-3 py-1.5 text-xs">clear</button>}
      </div>

      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages === null && <Loader2 className="animate-spin text-muted mx-auto" />}
        {messages?.length === 0 && (
          <p className="text-sm text-muted text-center py-10">
            Add the rules, your videos and their analytics screenshots, then press “review campaign” or ask anything.
          </p>
        )}
        {messages?.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'flex justify-end' : 'flex'}>
            <div className={`max-w-[90%] rounded-card px-4 py-3 ${m.role === 'user' ? 'bg-paper3 text-ink' : 'border border-rule text-ink2'}`}>
              <Rich text={m.content} />
            </div>
          </div>
        ))}
        {sending && <div className="flex"><Loader2 size={16} className="animate-spin text-muted" /></div>}
        <div ref={endRef} />
      </div>

      {error && <p className="text-xs text-red-400 pb-2">{error}</p>}
      <div className="flex gap-2 items-end pt-3 border-t border-rule">
        <textarea dir="auto" rows={2} className="input-field flex-1 text-sm" value={text} placeholder="ask about a video, the rules, what to fix..."
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }} />
        <button onClick={() => send()} disabled={sending || !text.trim()} className="btn-primary px-4 py-2" aria-label="send"><Send size={15} /></button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- campaign page

function CampaignPage({ id, apiKey, activeId, setActiveId, onBack }) {
  const [campaign, setCampaign] = useState(null);
  const [tab, setTab] = useState('videos');
  const [error, setError] = useState('');

  const reload = useCallback(() => {
    apiJson(`/api/campaigns/${id}`).then(setCampaign).catch((e) => setError(errText(e)));
  }, [id]);
  useEffect(() => { reload(); }, [reload]);

  if (error) return <p className="text-sm text-red-400 p-6">{error}</p>;
  if (!campaign) return <div className="p-10 flex justify-center"><Loader2 className="animate-spin text-muted" /></div>;

  const isActive = activeId === campaign.id;
  const tabs = [['videos', ListVideo, 'videos'], ['rules', ScrollText, 'rules'], ['chat', MessageSquare, 'AI coach']];
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={onBack} className="btn-quiet px-3 py-1.5 text-xs"><ArrowLeft size={13} /> campaigns</button>
        <h1 dir="auto" className="font-display text-xl text-ink flex-1 min-w-0 truncate">{campaign.name}</h1>
        <button onClick={() => setActiveId(isActive ? '' : campaign.id)}
          className={`btn-quiet px-3 py-1.5 text-xs ${isActive ? 'text-brass' : ''}`}
          title="New clips from the Clip Generator are added to the active campaign">
          <Star size={13} fill={isActive ? 'currentColor' : 'none'} />
          {isActive ? 'active in clip generator' : 'use in clip generator'}
        </button>
      </div>

      <div className="flex gap-2 border-b border-rule">
        {tabs.map(([key, Icon, label]) => (
          <button key={key} onClick={() => setTab(key)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm lowercase border-b-2 -mb-px ${tab === key ? 'border-brass text-ink' : 'border-transparent text-muted hover:text-ink2'}`}>
            <Icon size={14} /> {label}
          </button>
        ))}
      </div>

      {tab === 'videos' && <VideosPane campaign={campaign} reload={reload} setCampaign={setCampaign} />}
      {tab === 'rules' && <RulesPane campaign={campaign} onSaved={(rules) => setCampaign({ ...campaign, rules })} />}
      {tab === 'chat' && <ChatPane campaign={campaign} apiKey={apiKey} />}
    </div>
  );
}

// ---------------------------------------------------------------- list

export default function CampaignsTab({ apiKey, activeId, setActiveId }) {
  const [campaigns, setCampaigns] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [creating, setCreating] = useState(false);
  const [draft, setDraft] = useState({ name: '', rules: '' });
  const [error, setError] = useState('');

  const load = useCallback(() => {
    apiJson('/api/campaigns').then((d) => setCampaigns(d.campaigns)).catch((e) => setError(errText(e)));
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    try {
      const c = await apiJson('/api/campaigns', jsonOpts('POST', draft));
      setDraft({ name: '', rules: '' }); setCreating(false); setActiveId(c.id); load(); setOpenId(c.id);
    } catch (e) { setError(errText(e)); }
  };

  const remove = async (c) => {
    if (!window.confirm(`Delete the campaign “${c.name}” with all its videos and screenshots?`)) return;
    try {
      await apiJson(`/api/campaigns/${c.id}`, { method: 'DELETE' });
      if (activeId === c.id) setActiveId('');
      load();
    } catch (e) { setError(errText(e)); }
  };

  if (openId) {
    return (
      <div className="max-w-4xl mx-auto w-full p-4 sm:p-6">
        <CampaignPage id={openId} apiKey={apiKey} activeId={activeId} setActiveId={setActiveId}
          onBack={() => { setOpenId(null); load(); }} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto w-full p-4 sm:p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display lowercase text-2xl text-ink flex-1">campaigns</h1>
        <button onClick={() => setCreating(!creating)} className="btn-primary px-4 py-2 text-sm"><Plus size={14} /> new campaign</button>
      </div>

      {creating && (
        <div className="card p-4 space-y-3">
          <input dir="auto" className="input-field w-full" placeholder="campaign name" value={draft.name}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
          <textarea dir="auto" rows={6} className="input-field w-full text-sm" placeholder="rules (you can paste them now or later)"
            value={draft.rules} onChange={(e) => setDraft({ ...draft, rules: e.target.value })} />
          <button onClick={create} disabled={!draft.name.trim()} className="btn-primary px-5 py-2 text-sm">create</button>
        </div>
      )}
      {error && <p className="text-xs text-red-400">{error}</p>}

      {campaigns === null ? <Loader2 className="animate-spin text-muted mx-auto" /> : campaigns.length === 0 ? (
        <div className="card p-10 text-center text-muted text-sm">
          No campaigns yet. Create one per brand/campaign: it keeps the rules, the clips you made for it,
          their analytics and an AI coach in one place.
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {campaigns.map((c) => (
            <div key={c.id} className="card card-hover p-4 cursor-pointer" onClick={() => setOpenId(c.id)}>
              <div className="flex items-start gap-2">
                <p dir="auto" className="text-ink font-medium flex-1 min-w-0 truncate">{c.name}</p>
                {activeId === c.id && <Star size={14} className="text-brass shrink-0 mt-0.5" fill="currentColor" title="active in clip generator" />}
                <button onClick={(e) => { e.stopPropagation(); remove(c); }} className="text-muted hover:text-ink" aria-label="delete campaign"><Trash2 size={14} /></button>
              </div>
              <p className="text-xs text-muted mt-2">{c.video_count} video{c.video_count === 1 ? '' : 's'} · {c.posted_count} posted</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
