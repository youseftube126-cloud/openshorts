import io
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

import campaigns

CLIPS = [
    {"video_title_for_youtube_short": "Clip A", "hook_text": "Wait for it", "virality_score": 88,
     "video_url": "/videos/j1/a.mp4", "start": 10, "end": 50},
    {"video_title_for_youtube_short": "Clip B", "video_url": "/videos/j1/b.mp4", "start": 60, "end": 90},
]


def png_bytes(size=(40, 30), color="red"):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def env(tmp_path):
    calls = []

    def fake_generate(key, system, history, context, images, question):
        calls.append(dict(key=key, system=system, history=history, context=context,
                          images=images, question=question))
        return "answer: " + question

    store = campaigns.Store(str(tmp_path))
    app = FastAPI()
    app.include_router(campaigns.create_router(
        store, lambda job: CLIPS if job == "j1" else [],
        lambda req: req.headers.get("X-Gemini-Key"), fake_generate))
    return TestClient(app), store, calls, tmp_path


def make(client, name="Camp", rules="No profanity"):
    return client.post("/api/campaigns", json={"name": name, "rules": rules}).json()


def test_create_list_update_delete(env):
    c, *_ = env
    camp = make(c)
    assert c.post("/api/campaigns", json={"name": "  "}).status_code == 400
    assert [x["name"] for x in c.get("/api/campaigns").json()["campaigns"]] == ["Camp"]
    assert c.patch(f"/api/campaigns/{camp['id']}", json={"rules": "New"}).json()["rules"] == "New"
    assert c.delete(f"/api/campaigns/{camp['id']}").json() == {"ok": True}
    assert c.get(f"/api/campaigns/{camp['id']}").status_code == 404


def test_import_job_links_every_clip_once(env):
    c, *_ = env
    camp = make(c)
    assert c.post(f"/api/campaigns/{camp['id']}/import-job", json={"job_id": "j1"}).json() == {"added": 2, "total": 2}
    assert c.post(f"/api/campaigns/{camp['id']}/import-job", json={"job_id": "j1"}).json() == {"added": 0, "total": 2}
    assert c.post(f"/api/campaigns/{camp['id']}/import-job", json={"job_id": "nope"}).status_code == 404
    vids = c.get(f"/api/campaigns/{camp['id']}").json()["videos"]
    assert [v["title"] for v in vids] == ["Clip A", "Clip B"]
    assert vids[0]["hook"] == "Wait for it" and vids[0]["score"] == 88
    assert vids[0]["video_url"] == "/videos/j1/a.mp4"


def test_same_clip_can_belong_to_two_campaigns(env):
    c, *_ = env
    a, b = make(c, "A"), make(c, "B")
    for camp in (a, b):
        assert c.post(f"/api/campaigns/{camp['id']}/import-job", json={"job_id": "j1"}).json()["added"] == 2


def test_manual_video_and_patch(env):
    c, *_ = env
    camp = make(c)
    v = c.post(f"/api/campaigns/{camp['id']}/videos", json={"title": "Mine", "posted_url": "https://y/1"}).json()
    assert v["title"] == "Mine" and v["job_id"] is None
    out = c.patch(f"/api/campaigns/{camp['id']}/videos/{v['id']}", json={"notes": "good", "posted_url": "https://y/2"}).json()
    assert out["notes"] == "good" and out["posted_url"] == "https://y/2" and out["title"] == "Mine"
    assert c.post(f"/api/campaigns/{camp['id']}/videos", json={"job_id": "j1", "clip_index": 9}).status_code == 404


def test_screenshot_upload_serve_delete(env):
    c, store, _, tmp = env
    camp = make(c)
    v = c.post(f"/api/campaigns/{camp['id']}/videos", json={"title": "V"}).json()
    r = c.post(f"/api/campaigns/{camp['id']}/videos/{v['id']}/shots",
               files={"file": ("s.png", png_bytes((3000, 1500)), "image/png")}, data={"label": "day 1"})
    sid = r.json()["id"]
    img = c.get(f"/api/campaigns/shots/{sid}/image")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert max(Image.open(io.BytesIO(img.content)).size) <= 1600           # downscaled
    assert c.get(f"/api/campaigns/{camp['id']}").json()["videos"][0]["shots"][0]["label"] == "day 1"
    bad = c.post(f"/api/campaigns/{camp['id']}/videos/{v['id']}/shots", files={"file": ("x.txt", b"not an image", "text/plain")})
    assert bad.status_code == 400
    c.delete(f"/api/campaigns/shots/{sid}")
    assert c.get(f"/api/campaigns/shots/{sid}/image").status_code == 404
    assert os.listdir(store.shots_dir) == []


def test_deleting_video_or_campaign_removes_files(env):
    c, store, *_ = env
    camp = make(c)
    v = c.post(f"/api/campaigns/{camp['id']}/videos", json={"title": "V"}).json()
    c.post(f"/api/campaigns/{camp['id']}/videos/{v['id']}/shots", files={"file": ("s.png", png_bytes(), "image/png")})
    assert len(os.listdir(store.shots_dir)) == 1
    c.delete(f"/api/campaigns/{camp['id']}/videos/{v['id']}")
    assert os.listdir(store.shots_dir) == []
    v2 = c.post(f"/api/campaigns/{camp['id']}/videos", json={"title": "V2"}).json()
    c.post(f"/api/campaigns/{camp['id']}/videos/{v2['id']}/shots", files={"file": ("s.png", png_bytes(), "image/png")})
    c.delete(f"/api/campaigns/{camp['id']}")
    assert os.listdir(store.shots_dir) == []
    assert store.list_campaigns() == []


def test_chat_sends_rules_videos_images_and_keeps_history(env):
    c, _, calls, _ = env
    camp = make(c, rules="Max 60 seconds. No music.")
    c.post(f"/api/campaigns/{camp['id']}/import-job", json={"job_id": "j1"})
    vid = c.get(f"/api/campaigns/{camp['id']}").json()["videos"][0]["id"]
    c.patch(f"/api/campaigns/{camp['id']}/videos/{vid}", json={"posted_url": "https://y/1"})
    c.post(f"/api/campaigns/{camp['id']}/videos/{vid}/shots", files={"file": ("s.png", png_bytes(), "image/png")}, data={"label": "retention"})

    assert c.post(f"/api/campaigns/{camp['id']}/chat", json={"message": "hi"}).status_code == 400   # no key
    r = c.post(f"/api/campaigns/{camp['id']}/chat", json={"message": "what went wrong?"}, headers={"X-Gemini-Key": "k"})
    assert r.json() == {"reply": "answer: what went wrong?", "images_used": 1}
    call = calls[-1]
    assert call["key"] == "k" and "Max 60 seconds. No music." in call["context"]
    assert "Clip A" in call["context"] and "https://y/1" in call["context"] and "not posted yet" in call["context"]
    assert call["images"][0][0] == "Clip A — retention" and call["images"][0][1][:2] == b"\xff\xd8"  # JPEG

    c.post(f"/api/campaigns/{camp['id']}/chat", json={"message": "and now?"}, headers={"X-Gemini-Key": "k"})
    assert [m["role"] for m in calls[-1]["history"]] == ["user", "assistant"]
    msgs = c.get(f"/api/campaigns/{camp['id']}/chat").json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]
    c.delete(f"/api/campaigns/{camp['id']}/chat")
    assert c.get(f"/api/campaigns/{camp['id']}/chat").json()["messages"] == []


def test_chat_failure_is_502_and_not_saved(env):
    c, store, *_ = env
    camp = make(c)
    def boom(*a, **k): raise RuntimeError("quota")
    app = FastAPI()
    app.include_router(campaigns.create_router(store, lambda j: [], lambda r: "k", boom))
    r = TestClient(app).post(f"/api/campaigns/{camp['id']}/chat", json={"message": "x"})
    assert r.status_code == 502 and "quota" in r.json()["detail"]
    assert store.messages(camp["id"]) == []


def test_newest_screenshots_are_capped(env):
    c, store, calls, _ = env
    camp = make(c)
    v = c.post(f"/api/campaigns/{camp['id']}/videos", json={"title": "V"}).json()
    for i in range(campaigns.MAX_SHOTS_IN_PROMPT + 3):
        c.post(f"/api/campaigns/{camp['id']}/videos/{v['id']}/shots", files={"file": ("s.png", png_bytes(), "image/png")}, data={"label": str(i)})
    c.post(f"/api/campaigns/{camp['id']}/chat", json={"message": "q"}, headers={"X-Gemini-Key": "k"})
    labels = [l for l, _ in calls[-1]["images"]]
    assert len(labels) == campaigns.MAX_SHOTS_IN_PROMPT and labels[-1].endswith("— 14")
