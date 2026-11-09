"""Download only the parts of a YouTube video that will become clips.

The normal job downloads the whole video (1.6 GB for a 1h40 talk at 1080p)
before it cuts a few one-minute clips out of it. For someone on a metered
connection that is almost all waste. This module does it in the other order:

  1. fetch the audio track alone (about 100 MB for the same talk),
  2. the caller transcribes it and lets the model pick the clips,
  3. fetch only the picked stretches of video (plus a margin so the clip editor
     can still extend a clip a little),
  4. glue those stretches into ONE compact file and remap the transcript and the
     clip times onto it.

From there the rest of the pipeline sees an ordinary, shorter source video with
a matching transcript, exactly as if the user had uploaded an edited file.
Nothing downstream needs to know that the original was longer.

Everything here is independent of main.py (so it can be unit-tested without
Whisper, Gemini or YouTube). The pieces that touch the network or ffmpeg take
their options as arguments.
"""

import copy
import json
import os
import subprocess

DEFAULT_PAD = 30.0        # seconds of video kept on each side of a clip
DEFAULT_MERGE_GAP = 30.0  # stretches closer than this become one download
# Past this share of the source there is nothing to save: the caller should
# fall back to the ordinary full download.
MAX_USEFUL_SHARE = 0.6


# --------------------------------------------------------------------------
# Pure functions: planning and remapping
# --------------------------------------------------------------------------

def plan_ranges(shorts, duration, pad=DEFAULT_PAD, merge_gap=DEFAULT_MERGE_GAP):
    """Merged ``(start, end)`` stretches (seconds) that cover every clip.

    Each clip grows by ``pad`` on both sides (clamped to the video); stretches
    that overlap or sit within ``merge_gap`` of each other become one, so ten
    nearby clips are one download instead of ten.
    """
    spans = []
    for s in shorts or []:
        start, end = float(s["start"]), float(s["end"])
        if end <= start:
            continue
        spans.append((max(0.0, start - pad), min(float(duration), end + pad)))
    spans.sort()
    merged = []
    for start, end in spans:
        if merged and start - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return [(round(a, 3), round(b, 3)) for a, b in merged]


def total_seconds(ranges):
    return sum(e - s for s, e in ranges)


def is_worth_it(ranges, duration):
    """False when the stretches cover so much of the video that a partial
    download would save little (the caller then downloads everything)."""
    return bool(ranges) and duration > 0 and total_seconds(ranges) <= MAX_USEFUL_SHARE * duration


def place(ranges, actual_durations):
    """Where each downloaded stretch sits in the compact file.

    ``actual_durations`` are the real lengths of the downloaded files (they can
    differ from ``end - start`` by a frame or two). The compact timeline is
    those files back to back, so stretch ``i`` starts at the sum of the
    durations before it.
    """
    placements, offset = [], 0.0
    for (src_start, src_end), dur in zip(ranges, actual_durations):
        placements.append({"src_start": src_start,
                           "src_end": min(src_end, src_start + dur),
                           "offset": offset})
        offset += dur
    return placements


def _locate(t, placements):
    """The placement containing time ``t`` (source seconds), or None."""
    for p in placements:
        if p["src_start"] - 1e-6 <= t <= p["src_end"] + 1e-6:
            return p
    return None


def to_compact(t, placement):
    return round(t - placement["src_start"] + placement["offset"], 3)


def remap_clips(clips_data, placements):
    """Clip dicts with their times moved onto the compact timeline.

    A clip that does not fit inside one stretch is dropped (planning pads every
    clip, so this only happens if a download came back short).
    """
    out = copy.deepcopy(clips_data)
    kept = []
    for clip in out.get("shorts", []):
        p = _locate(float(clip["start"]), placements)
        if p is None or float(clip["end"]) > p["src_end"] + 1e-6:
            continue
        for key in ("start", "end"):
            clip[key] = to_compact(float(clip[key]), p)
        if isinstance(clip.get("proposed"), (list, tuple)) and len(clip["proposed"]) == 2:
            clip["proposed"] = [to_compact(min(max(float(v), p["src_start"]), p["src_end"]), p)
                                for v in clip["proposed"]]
        for seg in clip.get("segments") or []:
            if isinstance(seg, dict) and "start" in seg and "end" in seg:
                seg["start"] = to_compact(float(seg["start"]), p)
                seg["end"] = to_compact(float(seg["end"]), p)
        kept.append(clip)
    out["shorts"] = kept
    return out


def remap_transcript(transcript, placements):
    """The transcript restricted to the downloaded stretches, on the compact
    timeline. Words outside every stretch are dropped; a segment keeps only the
    words that fall inside the stretch it overlaps."""
    out = {k: v for k, v in transcript.items() if k != "segments"}
    segments = []
    for p in placements:
        for seg in transcript.get("segments", []):
            if seg["end"] <= p["src_start"] or seg["start"] >= p["src_end"]:
                continue
            words = [w for w in (seg.get("words") or [])
                     if w["start"] >= p["src_start"] - 1e-6 and w["end"] <= p["src_end"] + 1e-6]
            if seg.get("words") and not words:
                continue
            new = copy.deepcopy(seg)
            new["start"] = to_compact(max(seg["start"], p["src_start"]), p)
            new["end"] = to_compact(min(seg["end"], p["src_end"]), p)
            if seg.get("words"):
                new["words"] = [dict(w, start=to_compact(w["start"], p), end=to_compact(w["end"], p))
                                for w in words]
                new["text"] = " ".join(w["word"].strip() for w in words if w["word"].strip()) \
                    or seg.get("text", "")
            segments.append(new)
    out["segments"] = segments
    return out


# --------------------------------------------------------------------------
# Network + ffmpeg
# --------------------------------------------------------------------------

def _opts(extractor_args, **extra):
    opts = {
        "quiet": True, "no_warnings": True,
        "socket_timeout": 30, "retries": 10, "fragment_retries": 10,
        "nocheckcertificate": True, "cachedir": False, "noplaylist": True,
        "extractor_args": extractor_args,
        "overwrites": True,
        "http_headers": {"User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")},
    }
    opts.update(extra)
    return opts


def fetch_audio(url, out_dir, extractor_args, fmt="bestaudio[ext=m4a]/bestaudio"):
    """Download just the audio track. Returns ``(path, duration, title)``."""
    import yt_dlp
    opts = _opts(extractor_args, format=fmt,
                 outtmpl=os.path.join(out_dir, ".smart_audio.%(ext)s"))
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ((info.get("requested_downloads") or [{}])[0].get("filepath")
                or ydl.prepare_filename(info))
    if not path or not os.path.exists(path):
        raise RuntimeError("audio download produced no file")
    return path, info.get("duration"), info.get("title") or "youtube_video"


def fetch_sections(url, ranges, out_dir, extractor_args, fmt, log=print,
                   workers=2, guard=None):
    """Download each stretch of video into its own file; returns the paths.

    ``force_keyframes_at_cuts`` makes yt-dlp re-encode the cut so a stretch
    starts exactly where it was asked to. Without it the cut snaps to the
    previous keyframe, up to several seconds early, and every caption in the
    stretch would drift against the picture. It is slower (roughly real time),
    which is the price of the bandwidth saved, so a couple of stretches are
    fetched at once. ``guard`` is a context-manager factory entered in every
    worker thread (main.py passes the SSRF guard, which is per thread).
    """
    import contextlib
    from concurrent.futures import ThreadPoolExecutor
    import yt_dlp
    from yt_dlp.utils import download_range_func
    guard = guard or contextlib.nullcontext

    def one(i):
        start, end = ranges[i]
        log(f"   section {i + 1}/{len(ranges)}: {start:.0f}s-{end:.0f}s ({end - start:.0f}s)")
        path = os.path.join(out_dir, f".smart_section_{i}.mp4")
        opts = _opts(extractor_args, format=fmt,
                     outtmpl=os.path.join(out_dir, f".smart_section_{i}.%(ext)s"),
                     merge_output_format="mp4",
                     download_ranges=download_range_func(None, [(start, end)]),
                     force_keyframes_at_cuts=True)
        with guard(), yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            raise RuntimeError(f"section {i + 1} was not downloaded")
        return path

    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as pool:
        return list(pool.map(one, range(len(ranges))))


def probe_duration(path, ffprobe="ffprobe"):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True, timeout=60)
    return float(out.stdout.strip())


def concat_sections(paths, out_path, ffmpeg="ffmpeg", ffprobe="ffprobe"):
    """Join the stretch files into ``out_path``; returns their durations.

    Stream copy first (instant, lossless). If the pieces cannot be joined that
    way, they are re-encoded once.
    """
    durations = [probe_duration(p, ffprobe) for p in paths]
    if len(paths) == 1:
        os.replace(paths[0], out_path)
        return durations
    list_file = out_path + ".concat.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for p in paths:
            f.write("file '" + os.path.abspath(p).replace("\\", "/").replace("'", "'\\''") + "'\n")
    try:
        copy_cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", "-movflags", "+faststart", out_path]
        res = subprocess.run(copy_cmd, capture_output=True, text=True)
        ok = res.returncode == 0 and os.path.exists(out_path)
        if ok:
            # A copy-join can silently drift: trust it only if the length adds up.
            ok = abs(probe_duration(out_path, ffprobe) - sum(durations)) < 0.5
        if not ok:
            enc_cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                       "-i", list_file, "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out_path]
            res = subprocess.run(enc_cmd, capture_output=True, text=True)
            if res.returncode != 0:
                raise RuntimeError("could not join the downloaded sections: " + res.stderr[-300:])
            durations = [probe_duration(p, ffprobe) for p in paths]
    finally:
        try:
            os.remove(list_file)
        except OSError:
            pass
    return durations


def write_map(path, ranges, placements, source_duration):
    """Record how the compact file maps back to the original video."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"source_duration": source_duration, "sections": placements,
                   "requested": [list(r) for r in ranges]}, f, indent=2)
