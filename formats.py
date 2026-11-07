"""Format templates for the clip editor.

A *format* is a recipe for how a finished short looks and paces itself: where
the captions sit and how they animate, which hook style opens the clip, how
often the picture punches in, and which reframe layout is preferred. Applying
a format to a clip yields a plain ``project`` dict whose ``subtitles``,
``hook`` and ``effects`` keys match the Remotion ``ShortVideoProps`` in
``dashboard/src/remotion/lib/types.ts``, so the browser preview and the
render service can consume it as is, and the user can then edit any field.

Stdlib-only so it stays unit-testable without FFmpeg, Gemini or Remotion.
"""

from copy import deepcopy

# Fields a user override may touch, per section. Anything else is dropped so a
# bad client can never smuggle unknown keys into the render service.
_ALLOWED = {
    "subtitles": {"position", "maxChars", "maxDurationMs", "style"},
    "hook": {"text", "position", "size", "style", "font",
             "entranceAnimation", "displayDurationSec"},
    "effects": {"segments"},
}
_STYLE_KEYS = {
    "fontFamily", "fontSize", "fontColor", "highlightColor", "borderColor",
    "borderWidth", "bgColor", "bgOpacity", "animation", "baseOpacity",
    "uppercase", "reveal", "shadow", "highlightTextColor",
}

_BASE_STYLE = {
    "fontFamily": "Montserrat",
    "fontSize": 64,
    "fontColor": "#FFFFFF",
    "highlightColor": "#FFD60A",
    "borderColor": "#000000",
    "borderWidth": 4,
    "bgColor": "#000000",
    "bgOpacity": 0.0,
    "animation": "word-highlight",
}

FORMATS = {
    "talking_head": {
        "name": "Talking head",
        "description": "One speaker, big word-highlight captions, quick punch-ins on strong lines.",
        "layout": "track",
        "subtitles": {"position": "bottom", "maxChars": 22, "maxDurationMs": 2200,
                      "style": {"fontSize": 72, "animation": "word-highlight",
                                "uppercase": True}},
        "hook": {"position": "top", "size": "L", "style": "pill",
                 "entranceAnimation": "spring", "displayDurationSec": 3.0},
        "effects": {"punch_every": 4.0, "punch_len": 1.2, "zoom": 1.12},
    },
    "split_screen": {
        "name": "Split screen",
        "description": "Speaker on top, gameplay or B-roll below; captions in the middle seam.",
        "layout": "split",
        "subtitles": {"position": "middle", "maxChars": 18, "maxDurationMs": 1800,
                      "style": {"fontSize": 68, "animation": "pop", "uppercase": True}},
        "hook": {"position": "top", "size": "M", "style": "dark",
                 "entranceAnimation": "slide-up", "displayDurationSec": 2.5},
        "effects": {"punch_every": 0, "punch_len": 0, "zoom": 1.0},
    },
    "podcast": {
        "name": "Podcast",
        "description": "Two speakers, calmer pacing, karaoke captions, fewer zooms.",
        "layout": "split",
        "subtitles": {"position": "bottom", "maxChars": 28, "maxDurationMs": 3000,
                      "style": {"fontSize": 58, "animation": "karaoke",
                                "baseOpacity": 0.55}},
        "hook": {"position": "top", "size": "M", "style": "classic",
                 "entranceAnimation": "fade", "displayDurationSec": 3.5},
        "effects": {"punch_every": 8.0, "punch_len": 1.0, "zoom": 1.08},
    },
    "storytelling": {
        "name": "Storytelling",
        "description": "Fast pace, bold yellow captions, frequent punch-ins to keep retention up.",
        "layout": "general",
        "subtitles": {"position": "middle", "maxChars": 16, "maxDurationMs": 1500,
                      "style": {"fontSize": 80, "animation": "pop", "uppercase": True,
                                "fontColor": "#FFD60A", "highlightColor": "#FFFFFF"}},
        "hook": {"position": "center", "size": "L", "style": "yellow",
                 "font": "anton", "entranceAnimation": "spring",
                 "displayDurationSec": 2.5},
        "effects": {"punch_every": 2.5, "punch_len": 0.9, "zoom": 1.15},
    },
}

DEFAULT_FORMAT = "talking_head"


def list_formats():
    """Id, name, description and preferred layout for every format."""
    return [
        {"id": fid, "name": f["name"], "description": f["description"],
         "layout": f["layout"]}
        for fid, f in FORMATS.items()
    ]


def captions_from_words(words):
    """Transcript words ``{w, s, e}`` (seconds) to Remotion ``CaptionWord``s."""
    out = []
    for w in words or []:
        text = str(w.get("w", "")).strip()
        if not text:
            continue
        start, end = float(w.get("s", 0)), float(w.get("e", 0))
        if end <= start:
            end = start + 0.05
        out.append({"text": text, "startMs": int(round(start * 1000)),
                    "endMs": int(round(end * 1000))})
    return out


def punch_segments(duration, every, length, zoom):
    """Evenly spaced punch-in windows. No overlaps, none past the clip end,
    none in the first second (the hook owns it). Empty when ``every`` <= 0."""
    if every <= 0 or length <= 0 or zoom <= 1.0 or duration <= 0:
        return []
    segs, t = [], max(1.0, every)
    while t + length <= duration - 0.3:
        segs.append({"startSec": round(t, 3), "endSec": round(t + length, 3),
                     "zoom": zoom, "zoomCenterX": 0.5, "zoomCenterY": 0.45,
                     "brightness": 1.0, "contrast": 1.0, "saturate": 1.0})
        t += every
    return segs


def build_project(format_id, words, duration, hook_text=""):
    """Apply a format to a clip. Unknown ids fall back to the default."""
    fmt = deepcopy(FORMATS.get(format_id) or FORMATS[DEFAULT_FORMAT])
    fid = format_id if format_id in FORMATS else DEFAULT_FORMAT
    sub = fmt["subtitles"]
    style = dict(_BASE_STYLE)
    style.update(sub.get("style", {}))
    hook = dict(fmt["hook"])
    hook["text"] = (hook_text or "").strip()
    eff = fmt["effects"]
    return {
        "format": fid,
        "layout": fmt["layout"],
        "subtitles": {
            "captions": captions_from_words(words),
            "position": sub["position"],
            "maxChars": sub["maxChars"],
            "maxDurationMs": sub["maxDurationMs"],
            "style": style,
        },
        # No hook text, no hook layer: the preview would draw an empty pill.
        "hook": hook if hook["text"] else None,
        "effects": {"segments": punch_segments(
            duration, eff["punch_every"], eff["punch_len"], eff["zoom"])},
    }


def apply_overrides(project, overrides):
    """Merge a user's edits into a project, keeping only whitelisted keys."""
    out = deepcopy(project)
    for section, allowed in _ALLOWED.items():
        patch = (overrides or {}).get(section)
        if not isinstance(patch, dict):
            continue
        if out.get(section) is None:
            out[section] = {}
        for key, value in patch.items():
            if key not in allowed:
                continue
            if key == "style" and isinstance(value, dict):
                out[section].setdefault("style", {}).update(
                    {k: v for k, v in value.items() if k in _STYLE_KEYS})
            else:
                out[section][key] = value
    return out
