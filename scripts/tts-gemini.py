#!/usr/bin/env python3
"""Generate audio/voiceover.wav from script.txt with Gemini TTS.

Calls the Interactions endpoint: the script goes in verbatim, delivery goes in
annotations[].style (instructions written inside text get read aloud), and the
audio comes back base64 in steps[].content[].data.

Builds the payload with json.dumps — inlining a script into curl -d corrupts
quotes and newlines and comes back as 400 INVALID_ARGUMENT. Verifies the
resulting duration against a word-count estimate, because a large gap usually
means non-script text was spoken.

Usage:
    python3 scripts/tts-gemini.py                       # script.txt -> audio/voiceover.wav
    python3 scripts/tts-gemini.py --voice Puck --style "bright, playful"
    python3 scripts/tts-gemini.py --script vo/script.txt --out audio/vo.wav

Needs GEMINI_API_KEY in the environment.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"]  # separate quotas
WORDS_PER_SECOND = 2.5  # Indonesian; only used to sanity-check, never to place text


def build_payload(script, model, voice, style):
    return {
        "model": model,
        "input": [
            {
                "type": "user_input",
                "content": [
                    {
                        "type": "text",
                        "text": script,
                        # Delivery goes here. Instructions placed inside `text` get read aloud.
                        "annotations": [{"type": "speech_metadata", "style": style}],
                    }
                ],
            }
        ],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }


def post(payload, key):
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        return {"error": {"code": e.code, "body": body[:800]}}


def extract_audio(resp):
    """Interactions keeps audio in steps[].content[].data; last block wins."""
    for step in resp.get("steps", []):
        if step.get("type") != "model_output":
            continue
        blocks = [
            c
            for c in step.get("content", [])
            if c.get("type") == "audio" and c.get("data")
        ]
        if blocks:
            return base64.b64decode(blocks[-1]["data"]), "wav"

    # legacy generateContent fallback: no speech_metadata, use only if needed
    try:
        part = resp["candidates"][0]["content"]["parts"][0]
        mime = part["inlineData"].get("mimeType", "")
        data = base64.b64decode(part["inlineData"]["data"])
        return data, "wav" if "wav" in mime else "pcm"
    except (KeyError, IndexError, TypeError):
        return None, None


def probe_duration(path):
    out = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="script.txt")
    ap.add_argument("--out", default="audio/voiceover.wav")
    ap.add_argument("--voice", default="Kore")
    ap.add_argument("--style", default="warm, clear, slightly upbeat")
    ap.add_argument("--model", default=None, help="default: first available")
    args = ap.parse_args()

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        sys.exit(
            "GEMINI_API_KEY is not set. Do not fabricate a voice — ask the "
            "user to record the script instead."
        )

    try:
        script = open(args.script, encoding="utf-8").read().strip()
    except FileNotFoundError:
        sys.exit(f"{args.script} not found. Write the approved script first.")
    if not script:
        sys.exit(f"{args.script} is empty.")

    os.makedirs("audio", exist_ok=True)
    os.makedirs("work", exist_ok=True)

    resp, used_model = None, None
    for model in [args.model] if args.model else MODELS:
        payload = build_payload(script, model, args.voice, args.style)
        with open("work/tts-request.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=1)
        print(f"model {model} -> voice {args.voice}")
        resp = post(payload, key)
        if "error" not in resp:
            used_model = model
            break
        err = json.dumps(resp["error"])[:400]
        print(f"  failed: {err}")
        if "RESOURCE_EXHAUSTED" not in err and "429" not in err:
            break  # a real error: switching models will not help

    with open("work/tts-response.json", "w", encoding="utf-8") as f:
        json.dump(resp, f, ensure_ascii=False)

    if used_model is None:
        sys.exit(
            "TTS failed. Read work/tts-response.json. On a bad voice name "
            "the message says so; on a daily quota the switch above has "
            "already been tried."
        )

    data, kind = extract_audio(resp)
    if data is None:
        sys.exit("No audio in the response. Inspect work/tts-response.json.")

    raw = "work/tts.pcm" if kind == "pcm" else "work/tts.wav"
    with open(raw, "wb") as f:
        f.write(data)

    cmd = (
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "s16le",
            "-ar",
            "24000",
            "-ac",
            "1",
            "-i",
            raw,
            "-ar",
            "48000",
            args.out,
        ]
        if kind == "pcm"
        else [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            raw,
            "-ar",
            "48000",
            "-ac",
            "1",
            args.out,
        ]
    )
    subprocess.run(cmd, check=True)

    dur = probe_duration(args.out)
    words = len(script.split())
    est = words / WORDS_PER_SECOND
    print(f"\nwrote {args.out} · {dur:.1f}s · {words} words")
    if dur:
        # A large gap usually means non-script text was spoken (labels,
        # instructions, placeholders) or the script was truncated.
        if est and abs(dur - est) / est > 0.35:
            print(
                f"  WARNING: expected ~{est:.1f}s from word count. Check that "
                f"{args.script} holds verbatim prose only, then regenerate."
            )
        elif dur > 0 and est:
            print(f"  duration matches the script estimate (~{est:.1f}s)")
    print(f"  model: {used_model} · voice: {args.voice}")


if __name__ == "__main__":
    main()
