"""Campaigns: one workspace per campaign, with its videos, analytics
screenshots, rules and an AI coach that reads all of it.

A campaign (e.g. a Whop clipping campaign) holds
  - its rules (pasted text),
  - the videos generated for it (linked to a job + clip of the clip generator,
    or added by hand), each with the posted URL and notes,
  - analytics screenshots attached to each video (YouTube Studio, etc.),
  - a chat with Gemini that sees the rules, the videos and the screenshots and,
    after a campaign, lists the mistakes and what to improve.

Storage is one SQLite file plus the screenshot files under ``data_dir``. This is
a single-user, self-hosted feature: ``create_router`` is not mounted in cloud
mode. Everything that touches the outside world (reading a job's clip metadata,
calling Gemini) is injected, so the module is testable without the pipeline.
"""

import asyncio
import io
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

MAX_SHOTS_IN_PROMPT = 12      # newest screenshots sent to the model per question
MAX_HISTORY = 20              # previous chat messages replayed to the model
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
CHAT_MODEL = "gemini-2.5-flash"


def _id():
    return uuid.uuid4().hex[:12]


class Store:
    """SQLite persistence. A fresh connection per call keeps it thread-safe."""

    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.shots_dir = os.path.join(data_dir, "campaign_shots")
        os.makedirs(self.shots_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "campaigns.db")
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS campaigns(
              id TEXT PRIMARY KEY, name TEXT NOT NULL, rules TEXT NOT NULL DEFAULT '',
              created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS videos(
              id TEXT PRIMARY KEY,
              campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
              job_id TEXT, clip_index INTEGER,
              title TEXT NOT NULL DEFAULT '', hook TEXT NOT NULL DEFAULT '',
              score REAL, posted_url TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
              video_url TEXT NOT NULL DEFAULT '', meta TEXT NOT NULL DEFAULT '{}',
              created_at REAL NOT NULL,
              UNIQUE(campaign_id, job_id, clip_index));
            CREATE TABLE IF NOT EXISTS shots(
              id TEXT PRIMARY KEY,
              video_id TEXT NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
              filename TEXT NOT NULL, label TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS messages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
              role TEXT NOT NULL, content TEXT NOT NULL, created_at REAL NOT NULL);
            """)

    @contextmanager
    def _db(self):
        db = sqlite3.connect(self.db_path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    # ---- campaigns ----
    def list_campaigns(self):
        with self._db() as db:
            rows = db.execute("""
                SELECT c.*, (SELECT COUNT(*) FROM videos v WHERE v.campaign_id = c.id) AS video_count,
                  (SELECT COUNT(*) FROM videos v WHERE v.campaign_id = c.id AND v.posted_url != '') AS posted_count
                FROM campaigns c ORDER BY c.created_at DESC""").fetchall()
        return [dict(r) for r in rows]

    def get_campaign(self, cid):
        with self._db() as db:
            row = db.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
        return dict(row) if row else None

    def create_campaign(self, name, rules=""):
        cid = _id()
        with self._db() as db:
            db.execute("INSERT INTO campaigns(id, name, rules, created_at) VALUES (?,?,?,?)",
                       (cid, name.strip(), rules or "", time.time()))
        return self.get_campaign(cid)

    def update_campaign(self, cid, name=None, rules=None):
        with self._db() as db:
            if name is not None:
                db.execute("UPDATE campaigns SET name = ? WHERE id = ?", (name.strip(), cid))
            if rules is not None:
                db.execute("UPDATE campaigns SET rules = ? WHERE id = ?", (rules, cid))
        return self.get_campaign(cid)

    def delete_campaign(self, cid):
        with self._db() as db:
            files = [r["filename"] for r in db.execute(
                "SELECT s.filename FROM shots s JOIN videos v ON v.id = s.video_id "
                "WHERE v.campaign_id = ?", (cid,))]
            db.execute("DELETE FROM campaigns WHERE id = ?", (cid,))
        self._remove_files(files)

    # ---- videos ----
    def list_videos(self, cid):
        with self._db() as db:
            vids = [dict(r) for r in db.execute(
                "SELECT * FROM videos WHERE campaign_id = ? ORDER BY created_at ASC, rowid ASC", (cid,))]
            shots = [dict(r) for r in db.execute(
                "SELECT s.* FROM shots s JOIN videos v ON v.id = s.video_id "
                "WHERE v.campaign_id = ? ORDER BY s.created_at ASC", (cid,))]
        by_video: Dict[str, List[dict]] = {}
        for s in shots:
            by_video.setdefault(s["video_id"], []).append(
                {"id": s["id"], "label": s["label"], "created_at": s["created_at"]})
        for v in vids:
            v["meta"] = json.loads(v["meta"] or "{}")
            v["shots"] = by_video.get(v["id"], [])
        return vids

    def get_video(self, cid, vid):
        with self._db() as db:
            row = db.execute("SELECT * FROM videos WHERE id = ? AND campaign_id = ?",
                             (vid, cid)).fetchone()
        return dict(row) if row else None

    def add_video(self, cid, *, title="", hook="", score=None, posted_url="", notes="",
                  video_url="", meta=None, job_id=None, clip_index=None):
        """Insert a video; returns ``(video_id, created)``. A clip already linked
        to this campaign (same job and index) is left alone."""
        with self._db() as db:
            if job_id is not None and clip_index is not None:
                row = db.execute(
                    "SELECT id FROM videos WHERE campaign_id = ? AND job_id = ? AND clip_index = ?",
                    (cid, job_id, clip_index)).fetchone()
                if row:
                    return row["id"], False
            vid = _id()
            db.execute(
                "INSERT INTO videos(id, campaign_id, job_id, clip_index, title, hook, score, "
                "posted_url, notes, video_url, meta, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (vid, cid, job_id, clip_index, title, hook, score, posted_url, notes,
                 video_url, json.dumps(meta or {}, ensure_ascii=False), time.time()))
        return vid, True

    def update_video(self, cid, vid, **fields):
        allowed = {"title", "hook", "posted_url", "notes"}
        sets = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if sets:
            with self._db() as db:
                db.execute("UPDATE videos SET " + ", ".join(f"{k} = ?" for k in sets)
                           + " WHERE id = ? AND campaign_id = ?", (*sets.values(), vid, cid))
        return self.get_video(cid, vid)

    def delete_video(self, cid, vid):
        with self._db() as db:
            files = [r["filename"] for r in db.execute(
                "SELECT filename FROM shots WHERE video_id = ?", (vid,))]
            db.execute("DELETE FROM videos WHERE id = ? AND campaign_id = ?", (vid, cid))
        self._remove_files(files)

    # ---- screenshots ----
    def add_shot(self, vid, jpeg_bytes, label=""):
        sid = _id()
        filename = f"{sid}.jpg"
        with open(os.path.join(self.shots_dir, filename), "wb") as f:
            f.write(jpeg_bytes)
        with self._db() as db:
            db.execute("INSERT INTO shots(id, video_id, filename, label, created_at) VALUES (?,?,?,?,?)",
                       (sid, vid, filename, label or "", time.time()))
        return sid

    def get_shot(self, sid):
        with self._db() as db:
            row = db.execute("SELECT * FROM shots WHERE id = ?", (sid,)).fetchone()
        return dict(row) if row else None

    def shot_path(self, shot):
        return os.path.join(self.shots_dir, shot["filename"])

    def delete_shot(self, sid):
        shot = self.get_shot(sid)
        if not shot:
            return
        with self._db() as db:
            db.execute("DELETE FROM shots WHERE id = ?", (sid,))
        self._remove_files([shot["filename"]])

    def newest_shots(self, cid, limit):
        """Newest screenshots of the campaign with their video, oldest first."""
        with self._db() as db:
            rows = db.execute(
                "SELECT s.*, v.title AS video_title FROM shots s JOIN videos v ON v.id = s.video_id "
                "WHERE v.campaign_id = ? ORDER BY s.created_at DESC LIMIT ?", (cid, limit)).fetchall()
        return [dict(r) for r in reversed(rows)]

    # ---- chat ----
    def messages(self, cid):
        with self._db() as db:
            rows = db.execute("SELECT role, content, created_at FROM messages "
                              "WHERE campaign_id = ? ORDER BY id ASC", (cid,)).fetchall()
        return [dict(r) for r in rows]

    def add_message(self, cid, role, content):
        with self._db() as db:
            db.execute("INSERT INTO messages(campaign_id, role, content, created_at) VALUES (?,?,?,?)",
                       (cid, role, content, time.time()))

    def clear_messages(self, cid):
        with self._db() as db:
            db.execute("DELETE FROM messages WHERE campaign_id = ?", (cid,))

    def _remove_files(self, filenames):
        for name in filenames:
            try:
                os.remove(os.path.join(self.shots_dir, name))
            except OSError:
                pass


# --------------------------------------------------------------------------
# Screenshots and the coach prompt
# --------------------------------------------------------------------------

def normalize_image(raw: bytes) -> bytes:
    """Any common image format to a JPEG no larger than 1600 px, so screenshots
    stay cheap to store and to send to the model."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except Exception:
        raise HTTPException(status_code=400, detail="That file is not a readable image.")
    img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


SYSTEM_PROMPT = """You are a short-form video coach for a clipper who makes clips for paid campaigns \
(for example Whop clipping campaigns) and posts them on YouTube Shorts and other platforms.

You are given: the campaign rules, the list of the clipper's videos for this campaign (title, hook, \
virality score, posted link, the clipper's notes) and screenshots of the analytics (views, watch time, \
retention, traffic sources, etc.) attached to each video. Read the screenshots carefully and quote the \
numbers you actually see.

How to answer:
- Ground every point in the rules, the videos or the screenshots. If something is not visible, say so \
and ask for the screenshot or number you need. Never invent numbers.
- Check each video against the campaign rules and point out anything that may break them.
- Compare the videos: what the best ones have in common (hook, length, topic, retention) and what the \
weak ones did wrong.
- Finish with a short, prioritised list of concrete improvements for the next videos.
- Reply in the language the clipper writes in (Egyptian Arabic if they write Arabic). Be direct and practical."""


def build_context(campaign, videos) -> str:
    lines = [f"CAMPAIGN: {campaign['name']}", "", "RULES:",
             campaign["rules"].strip() or "(no rules written yet)", "", f"VIDEOS ({len(videos)}):"]
    for i, v in enumerate(videos, 1):
        bits = [f"{i}. {v['title'] or '(untitled)'}"]
        if v["hook"]:
            bits.append(f"hook: {v['hook']}")
        if v["score"] is not None:
            bits.append(f"virality score: {v['score']}")
        bits.append(f"posted: {v['posted_url'] or 'not posted yet'}")
        if v["notes"]:
            bits.append(f"notes: {v['notes']}")
        bits.append(f"analytics screenshots: {len(v['shots'])}")
        lines.append(" | ".join(bits))
    return "\n".join(lines)


def gemini_generate(api_key, system, history, context, images, question, model=CHAT_MODEL):
    """One Gemini call. ``images`` is ``[(label, jpeg_bytes), ...]``."""
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    contents = []
    for m in history:
        contents.append(types.Content(
            role="user" if m["role"] == "user" else "model",
            parts=[types.Part.from_text(text=m["content"])]))
    parts = [types.Part.from_text(text=context)]
    for label, data in images:
        parts.append(types.Part.from_text(text=f"Analytics screenshot — {label}:"))
        parts.append(types.Part.from_bytes(data=data, mime_type="image/jpeg"))
    parts.append(types.Part.from_text(text="Clipper's question:\n" + question))
    contents.append(types.Content(role="user", parts=parts))
    response = client.models.generate_content(
        model=model, contents=contents,
        config=types.GenerateContentConfig(system_instruction=system))
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("The model returned no answer (it may have been blocked).")
    return text


# --------------------------------------------------------------------------
# HTTP API
# --------------------------------------------------------------------------

class CampaignIn(BaseModel):
    name: str
    rules: str = ""


class CampaignPatch(BaseModel):
    name: Optional[str] = None
    rules: Optional[str] = None


class VideoIn(BaseModel):
    title: str = ""
    posted_url: str = ""
    notes: str = ""
    job_id: Optional[str] = None
    clip_index: Optional[int] = None


class VideoPatch(BaseModel):
    title: Optional[str] = None
    hook: Optional[str] = None
    posted_url: Optional[str] = None
    notes: Optional[str] = None


class ImportJob(BaseModel):
    job_id: str


class ChatIn(BaseModel):
    message: str


def create_router(store: Store,
                  clip_loader: Callable[[str], List[Dict[str, Any]]],
                  resolve_key: Callable[[Request], Any],
                  generate: Callable = gemini_generate) -> APIRouter:
    """``clip_loader(job_id)`` returns the job's clips (dicts from its metadata);
    ``resolve_key(request)`` returns the Gemini key (sync or async);
    ``generate`` is the model call, replaceable in tests."""
    router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

    def need_campaign(cid):
        c = store.get_campaign(cid)
        if not c:
            raise HTTPException(status_code=404, detail="Campaign not found")
        return c

    def video_fields(clip):
        return dict(
            title=str(clip.get("video_title_for_youtube_short") or clip.get("title") or "")[:300],
            hook=str(clip.get("hook_text") or clip.get("hook") or "")[:300],
            score=clip.get("virality_score") if isinstance(clip.get("virality_score"), (int, float)) else None,
            video_url=str(clip.get("video_url") or ""),
            meta={k: clip.get(k) for k in ("start", "end", "video_description_for_tiktok",
                                          "video_description_for_instagram", "virality_score")
                  if clip.get(k) is not None})

    @router.get("")
    def list_campaigns():
        return {"campaigns": store.list_campaigns()}

    @router.post("")
    def create_campaign(body: CampaignIn):
        if not body.name.strip():
            raise HTTPException(status_code=400, detail="Give the campaign a name.")
        return store.create_campaign(body.name, body.rules)

    @router.get("/{cid}")
    def get_campaign(cid: str):
        c = need_campaign(cid)
        return {**c, "videos": store.list_videos(cid)}

    @router.patch("/{cid}")
    def patch_campaign(cid: str, body: CampaignPatch):
        need_campaign(cid)
        if body.name is not None and not body.name.strip():
            raise HTTPException(status_code=400, detail="The name cannot be empty.")
        return store.update_campaign(cid, body.name, body.rules)

    @router.delete("/{cid}")
    def delete_campaign(cid: str):
        need_campaign(cid)
        store.delete_campaign(cid)
        return {"ok": True}

    # ---- videos ----
    @router.post("/{cid}/videos")
    def add_video(cid: str, body: VideoIn):
        need_campaign(cid)
        fields = {}
        if body.job_id is not None and body.clip_index is not None:
            clips = clip_loader(body.job_id)
            if not clips or not (0 <= body.clip_index < len(clips)):
                raise HTTPException(status_code=404, detail="Clip not found in that job")
            fields = video_fields(clips[body.clip_index])
        if body.title.strip():
            fields["title"] = body.title.strip()
        vid, _ = store.add_video(cid, posted_url=body.posted_url, notes=body.notes,
                                 job_id=body.job_id, clip_index=body.clip_index, **fields)
        return store.get_video(cid, vid)

    @router.post("/{cid}/import-job")
    def import_job(cid: str, body: ImportJob):
        """Link every clip of a finished job to the campaign (already linked
        clips are skipped, so it is safe to call twice)."""
        need_campaign(cid)
        clips = clip_loader(body.job_id)
        if not clips:
            raise HTTPException(status_code=404, detail="That job has no clips")
        added = 0
        for i, clip in enumerate(clips):
            _, created = store.add_video(cid, job_id=body.job_id, clip_index=i, **video_fields(clip))
            added += int(created)
        return {"added": added, "total": len(clips)}

    @router.patch("/{cid}/videos/{vid}")
    def patch_video(cid: str, vid: str, body: VideoPatch):
        need_campaign(cid)
        if not store.get_video(cid, vid):
            raise HTTPException(status_code=404, detail="Video not found")
        store.update_video(cid, vid, **body.model_dump())
        return next(v for v in store.list_videos(cid) if v["id"] == vid)

    @router.delete("/{cid}/videos/{vid}")
    def delete_video(cid: str, vid: str):
        need_campaign(cid)
        store.delete_video(cid, vid)
        return {"ok": True}

    # ---- screenshots ----
    @router.post("/{cid}/videos/{vid}/shots")
    async def add_shot(cid: str, vid: str, file: UploadFile = File(...), label: str = Form("")):
        need_campaign(cid)
        if not store.get_video(cid, vid):
            raise HTTPException(status_code=404, detail="Video not found")
        raw = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(raw) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Image is too large (15 MB max).")
        sid = store.add_shot(vid, normalize_image(raw), label.strip())
        return {"id": sid, "label": label.strip()}

    @router.get("/shots/{sid}/image")
    def shot_image(sid: str):
        shot = store.get_shot(sid)
        path = store.shot_path(shot) if shot else None
        if not path or not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Screenshot not found")
        return FileResponse(path, media_type="image/jpeg")

    @router.delete("/shots/{sid}")
    def delete_shot(sid: str):
        store.delete_shot(sid)
        return {"ok": True}

    # ---- chat ----
    @router.get("/{cid}/chat")
    def get_chat(cid: str):
        need_campaign(cid)
        return {"messages": store.messages(cid)}

    @router.delete("/{cid}/chat")
    def clear_chat(cid: str):
        need_campaign(cid)
        store.clear_messages(cid)
        return {"ok": True}

    @router.post("/{cid}/chat")
    async def chat(cid: str, body: ChatIn, request: Request):
        campaign = need_campaign(cid)
        question = body.message.strip()
        if not question:
            raise HTTPException(status_code=400, detail="Write a message first.")
        key = resolve_key(request)
        if asyncio.iscoroutine(key):
            key = await key
        if not key:
            raise HTTPException(status_code=400, detail="Missing X-Gemini-Key header")

        videos = store.list_videos(cid)
        images = []
        for shot in store.newest_shots(cid, MAX_SHOTS_IN_PROMPT):
            path = store.shot_path(shot)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    images.append((f"{shot['video_title'] or 'video'}"
                                   + (f" — {shot['label']}" if shot["label"] else ""), f.read()))
        history = store.messages(cid)[-MAX_HISTORY:]
        try:
            answer = await asyncio.to_thread(
                generate, key, SYSTEM_PROMPT, history, build_context(campaign, videos),
                images, question)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"The AI request failed: {e}")
        store.add_message(cid, "user", question)
        store.add_message(cid, "assistant", answer)
        return {"reply": answer, "images_used": len(images)}

    return router
