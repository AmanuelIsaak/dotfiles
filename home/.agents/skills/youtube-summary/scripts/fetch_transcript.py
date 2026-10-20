#!/usr/bin/env python3
"""Fetch a YouTube video's metadata and transcript with yt-dlp.

Usage: fetch_transcript.py <url> <out_dir> [--lang en] [--chunk 30]

Writes to <out_dir>:
  meta.json       title, channel, duration, upload date, chapters, description
  transcript.txt  "[mm:ss] text" lines, deduplicated, grouped every --chunk seconds
Prints a short summary (title, duration, transcript source, word count) to stdout.
Exit code 2 = no transcript available.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def ts(seconds):
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def parse_vtt_time(t):
    parts = t.replace(",", ".").split(":")
    parts = [float(p) for p in parts]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def vtt_to_cues(path):
    """Return [(start_seconds, text)] with YouTube's rolling-caption duplication removed."""
    cues, start, buf = [], None, []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            m = re.match(r"^(\d[\d:.,]+)\s+-->\s+(\d[\d:.,]+)", line)
            if m:
                start, buf = parse_vtt_time(m.group(1)), []
                continue
            if not line.strip():
                if start is not None and buf:
                    cues.append((start, buf))
                start, buf = None, []
                continue
            if start is not None:
                text = re.sub(r"<[^>]+>", "", line)  # strip inline word timings
                text = re.sub(r"&nbsp;", " ", text).strip()
                if text:
                    buf.append(text)
    if start is not None and buf:
        cues.append((start, buf))

    # Auto-captions repeat the previous line at the top of each cue; keep only new lines.
    out, seen_last = [], None
    for start, lines in cues:
        for text in lines:
            if text == seen_last:
                continue
            out.append((start, text))
            seen_last = text
    return out


def group(cues, chunk):
    groups, cur_start, cur = [], None, []
    for start, text in cues:
        if cur_start is None:
            cur_start = start
        if start - cur_start >= chunk and cur:
            groups.append((cur_start, " ".join(cur)))
            cur_start, cur = start, []
        cur.append(text)
    if cur:
        groups.append((cur_start, " ".join(cur)))
    return groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("out_dir")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--chunk", type=int, default=30)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    r = run(["yt-dlp", "--skip-download", "--dump-single-json", "--no-playlist", a.url])
    if r.returncode != 0:
        sys.exit(f"yt-dlp metadata failed:\n{r.stderr.strip()[-1500:]}")
    info = json.loads(r.stdout)
    meta = {
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "url": info.get("webpage_url") or a.url,
        "duration": ts(info.get("duration") or 0),
        "upload_date": info.get("upload_date"),
        "chapters": [
            {"start": ts(c["start_time"]), "title": c["title"]}
            for c in (info.get("chapters") or [])
        ],
        "description": (info.get("description") or "")[:3000],
        "language": info.get("language"),
    }

    # Prefer human subtitles; fall back to auto-generated. Try requested lang, then any English variant.
    langs = f"{a.lang},{a.lang}.*,{a.lang}-orig" if a.lang else "en,en.*"
    source = None
    for flag, label in (("--write-subs", "manual"), ("--write-auto-subs", "auto-generated")):
        for f in glob.glob(os.path.join(a.out_dir, "sub*.vtt")):
            os.remove(f)
        run(["yt-dlp", "--skip-download", "--no-playlist", flag, "--sub-langs", langs,
             "--sub-format", "vtt", "-o", os.path.join(a.out_dir, "sub"), a.url])
        files = sorted(glob.glob(os.path.join(a.out_dir, "sub*.vtt")))
        if files:
            source = (label, files[0])
            break

    if not source:
        # Last resort: any auto caption language (e.g. non-English video); Claude can translate.
        orig = info.get("language") or ""
        if orig and orig != a.lang:
            run(["yt-dlp", "--skip-download", "--no-playlist", "--write-auto-subs",
                 "--sub-langs", f"{orig},{orig}-orig", "--sub-format", "vtt",
                 "-o", os.path.join(a.out_dir, "sub"), a.url])
            files = sorted(glob.glob(os.path.join(a.out_dir, "sub*.vtt")))
            if files:
                source = (f"auto-generated ({orig})", files[0])

    meta["transcript_source"] = source[0] if source else None
    with open(os.path.join(a.out_dir, "meta.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"Title:    {meta['title']}")
    print(f"Channel:  {meta['channel']}")
    print(f"Duration: {meta['duration']}  Chapters: {len(meta['chapters'])}")
    if not source:
        print("Transcript: NONE available")
        sys.exit(2)

    groups = group(vtt_to_cues(source[1]), a.chunk)
    with open(os.path.join(a.out_dir, "transcript.txt"), "w") as f:
        for start, text in groups:
            f.write(f"[{ts(start)}] {text}\n")
    words = sum(len(t.split()) for _, t in groups)
    print(f"Transcript: {source[0]}, {words} words -> {os.path.join(a.out_dir, 'transcript.txt')}")


if __name__ == "__main__":
    main()
