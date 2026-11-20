#!/usr/bin/env python3
"""Write output/publish.txt — one copy-paste-ready caption block per platform.

The file is the last thing the user touches before uploading, so it has to be
finished, not a skeleton. Everything in it is derived from what the video
actually says and what the file actually is: duration, codec, dimensions and
loudness are measured with ffprobe/ffmpeg, never typed in by hand.

Usage:
    python3 scripts/publish.py --video output/foo.mp4 --slug "Anak dan Gadget" \
        --script script.txt --orientation portrait

    # captions written by the agent, passed as a JSON file
    python3 scripts/publish.py --video output/foo.mp4 --slug "..." \
        --captions work/captions.json

    # with a subtitle file and the model/voice record from image-meta/tts
    python3 scripts/publish.py ... --srt output/foo.srt --voice "Gemini TTS (Kore)"

Needs ffmpeg/ffprobe. Exits non-zero rather than writing a half-filled file.

Captions JSON shape (all keys optional except tiktok/reels/shorts):

{
  "title": "Judul video",                 // also used for the Shorts title field
  "tiktok":  "caption\n\n#tag1 #tag2",    // 150-300 chars, 8-15 tags
  "reels":   "caption\n\n#tag1 #tag2",
  "shorts":  "caption\n\n#tag1 #tag2",    // 3-5 tags
  "youtube": {"title": "...", "description": "..."},   // landscape only
  "notes":   ["Suara: ...", "Musik: ..."]
}
"""

import argparse
import json
import os
import re
import subprocess
import sys

# Advisory, not a gate. A good caption can carry 7 tags; the file this
# was written against used exactly that. Range is a hint for the writer.
MIN_TIKTOK_TAGS, MAX_TIKTOK_TAGS = 5, 15
MIN_SHORTS_TAGS, MAX_SHORTS_TAGS = 3, 5
CAPTION_MIN, CAPTION_MAX = 120, 300
LANDSCAPE_MAX = 600
HOOK_SAFE = 90  # characters that survive truncation on Reels/TikTok


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def probe(video):
    """Real numbers from the file, not from whatever the agent remembers."""
    raw = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,channels:format=duration,size",
            "-of",
            "json",
            video,
        ]
    )
    if not raw:
        sys.exit(f"ffprobe could not read {video}. Is the file finished?")
    d = json.loads(raw)
    streams = d.get("streams", [])
    v = next((s for s in streams if s.get("codec_name") not in ("aac", "mp3")), {})
    a = next((s for s in streams if s.get("codec_name") in ("aac", "mp3")), {})
    fps = v.get("r_frame_rate", "0/1")
    try:
        num, den = (int(x) for x in fps.split("/"))
        fps_val = round(num / den) if den else 0
    except ValueError:
        fps_val = 0
    dur = float(d.get("format", {}).get("duration") or 0)
    return {
        "duration": dur,
        "frames": int(round(dur * fps_val)) if fps_val else 0,
        "fps": fps_val,
        "width": v.get("width"),
        "height": v.get("height"),
        "vcodec": v.get("codec_name"),
        "acodec": a.get("codec_name"),
        "channels": a.get("channels"),
        "size_mb": round(int(d.get("format", {}).get("size") or 0) / 1048576, 1),
    }


def loudness(video):
    """Integrated LUFS and true peak of the finished file."""
    out = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            video,
            "-af",
            "loudnorm=print_format=summary",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stderr
    i = re.search(r"Input Integrated:\s*(-?[\d.]+) LUFS", out)
    tp = re.search(r"Input True Peak:\s*(-?[\d.]+) dBTP", out)
    return (i.group(1) if i else None, tp.group(1) if tp else None)


def count_tags(text):
    return len(re.findall(r"#\w+", text))


def body_without_tags(text):
    return re.sub(r"#\w+", "", text).strip()


def check_caption(body):
    """Return a list of problems; an empty list means it is shippable."""
    problems = []
    plain = " ".join(body_without_tags(body).split())
    if not plain:
        problems.append("caption text is empty")
        return problems
    if len(plain) < CAPTION_MIN:
        problems.append(f"caption is {len(plain)} chars, below {CAPTION_MIN}")
    if len(plain) > LANDSCAPE_MAX:
        problems.append(f"caption is {len(plain)} chars, above {LANDSCAPE_MAX}")
    first = plain.split(".")[0].split("?")[0]
    if len(first) > HOOK_SAFE + 20:
        problems.append(
            f"first sentence is {len(first)} chars; the hook is cut "
            f"around {HOOK_SAFE} on Reels/TikTok"
        )
    for bad in ("link in bio", "viral", "jangan sampai kelewatan!!!"):
        if bad in plain.lower():
            problems.append(f"banned phrase: {bad!r}")
    if plain.count("🔥") + plain.count("😱") >= 3:
        problems.append("emoji wall")
    return problems


def check_tags(text, lo, hi, platform):
    n = count_tags(text)
    if n == 0:
        return [f"{platform}: no hashtags"]
    if not (lo <= n <= hi):
        return [f"{platform}: {n} hashtags, expected {lo}-{hi}"]
    return []


def fmt_time(sec):
    m, s = divmod(int(round(sec)), 60)
    return f"{m} menit {s} detik" if m else f"{s} detik"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--slug", required=True, help="human title, used as the heading")
    ap.add_argument("--out", default=None, help="default: <video dir>/publish.txt")
    ap.add_argument("--captions", default=None, help="JSON file with the copy")
    ap.add_argument("--script", default=None, help="script.txt, used to warn on drift")
    ap.add_argument("--srt", default=None)
    ap.add_argument(
        "--orientation", choices=("portrait", "landscape", "square"), default=None
    )
    ap.add_argument("--voice", default=None)
    ap.add_argument("--music", default=None)
    ap.add_argument(
        "--allow-skeleton",
        action="store_true",
        help="write the file even with warnings (not for delivery)",
    )
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing publish.txt")
    args = ap.parse_args()

    if not os.path.exists(args.video):
        sys.exit(f"{args.video} not found. Render the video before writing copy.")

    info = probe(args.video)
    lufs, tp = loudness(args.video)

    w, h = info["width"] or 0, info["height"] or 0
    orientation = args.orientation or (
        "portrait" if h > w else "landscape" if w > h else "square"
    )
    orientation_id = {
        "portrait": "tegak",
        "landscape": "mendatar",
        "square": "persegi",
    }[orientation]
    cap = {"portrait": 60, "landscape": 300, "square": 60}[orientation]

    caps = {}
    if args.captions:
        try:
            caps = json.load(open(args.captions, encoding="utf-8"))
        except Exception as e:
            sys.exit(f"cannot read {args.captions}: {e}")

    hard = []      # a real failure: invented fact, nothing to measure, bad file
    soft = []      # style and length: report, do not block
    missing = [k for k in ("tiktok", "reels", "shorts") if not caps.get(k)]
    if missing:
        hard.append(f"captions missing for: {', '.join(missing)}")

    if caps.get("tiktok"):
        soft += check_caption(caps["tiktok"]) + check_tags(
            caps["tiktok"], MIN_TIKTOK_TAGS, MAX_TIKTOK_TAGS, "TikTok"
        )
    if caps.get("reels"):
        soft += check_caption(caps["reels"]) + check_tags(
            caps["reels"], MIN_TIKTOK_TAGS, MAX_TIKTOK_TAGS, "Reels"
        )
    if caps.get("shorts"):
        soft += check_caption(caps["shorts"]) + check_tags(
            caps["shorts"], MIN_SHORTS_TAGS, MAX_SHORTS_TAGS, "Shorts"
        )

    title = caps.get("title") or args.slug
    if len(title) > 100:
        soft.append(f"title is {len(title)} chars, YouTube caps at 100")

    if info["duration"] > cap:
        soft.append(
            f"duration {info['duration']:.1f}s exceeds the {cap}s cap for {orientation}"
        )

    # a claim in the copy that the video never makes is the worst failure here
    if args.script and caps:
        spoken = " ".join(open(args.script, encoding="utf-8").read().lower().split())
        for platform in ("tiktok", "reels", "shorts"):
            body = body_without_tags(caps.get(platform, "")).lower()
            numbers = [
                n
                for n in re.findall(r"\b\d[\d.,]*\b", body)
                if n not in ("1", "2", "3", "4", "5")
            ]
            for n in numbers:
                if n not in spoken:
                    hard.append(
                        f"{platform}: number {n} does not appear in script.txt "
                        f"— copy must not invent facts"
                    )

    if hard:
        print("Not writing publish.txt. These are failures, not style:", file=sys.stderr)
        for h in hard:
            print(f"  - {h}", file=sys.stderr)
        print(
            "\nFix them and re-run. --allow-skeleton exists for a draft, "
            "never for delivery.",
            file=sys.stderr,
        )
        sys.exit(1)

    if soft:
        print("Writing publish.txt. Read these before you deliver:", file=sys.stderr)
        for s_ in soft:
            print(f"  - {s_}", file=sys.stderr)

    out = args.out or os.path.join(os.path.dirname(args.video) or ".", "publish.txt")

    # Never silently replace a publish.txt that is already there. It is the one
    # file the user may have edited by hand, and losing that edit is worse than
    # failing loudly.
    if os.path.exists(out) and not args.force:
        sys.exit(
            f"{out} already exists. Pass --force to replace it, or --out to write "
            "somewhere else. This file may hold hand-written copy."
        )
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    spec = (
        f"Spesifikasi: {w}x{h}, {info['fps']} fps, {info['duration']:.1f} s "
        f"({info['frames']} frame), {info['vcodec'].upper()} + "
        f"{info['acodec'].upper()}"
        f"{' stereo' if info.get('channels') == 2 else ''}"
    )
    if lufs:
        spec += f", I = {lufs} LUFS, true peak {tp} dBTP"
    spec += f". Berkas {info['size_mb']} MB"
    if args.srt:
        spec += f". Subtitle: {args.srt}"

    lines = [f"{args.slug.upper()} — PAKET UNGGAH", f"Video: {args.video}", spec, ""]

    def block(name, text):
        lines.append(f"=== {name}")
        lines.append(text.strip())
        lines.append("")

    if caps.get("tiktok"):
        block("TikTok", caps["tiktok"])
    if caps.get("reels"):
        block("Instagram Reels", caps["reels"])
    if caps.get("shorts"):
        block("YouTube Shorts", f"Judul: {title}\n{caps['shorts']}")

    yt = caps.get("youtube")
    if yt and orientation == "landscape":
        block(
            "YouTube",
            f"Judul: {yt.get('title', title)}\n{yt.get('description', '').strip()}",
        )
    elif yt and orientation != "landscape":
        lines.append("CATATAN")
        lines.append(
            f"- Blok YouTube dilewati: video ini {orientation_id}, bukan mendatar."
        )
        lines.append("")

    notes = list(caps.get("notes") or [])
    if args.voice:
        notes.append(f"Suara: {args.voice}")
    if args.music:
        notes.append(f"Musik: {args.music}")
    notes.append(
        f"Durasi {fmt_time(info['duration'])}, batas {cap} detik untuk format "
        f"{orientation_id}."
    )
    lines.append("CATATAN")
    for n in notes:
        lines.append(f"- {n}")

    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    print(
        f"{out} — {len([k for k in ('tiktok', 'reels', 'shorts') if caps.get(k)])} "
        f"platform, {info['duration']:.1f}s, {w}x{h}"
    )
    if soft:
        print(f"\n{len(soft)} advisory note(s) — the file is written and shippable.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
