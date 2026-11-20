#!/usr/bin/env python3
"""Transcribe audio/voiceover.wav into audio/words.json with per-word timings.

This is the bits-motion/references/RENDER.md §3 recipe as a script. It exists
so the browser skill does not depend on prose being re-read correctly, and so
the decode step (which trips people up) is already right.

Two things this does that a naive call does not:

  * decodes the WAV itself with the wave module and passes a float32 numpy
    array at 16 kHz — passing a path makes some environments fail with
    "open() got an unexpected keyword argument 'metadata_errors'"
  * aligns the ASR sentence back to the spelling in script.txt, so the
    subtitle and the on-screen text carry the script's words, not the ASR's

Usage:
    python3 scripts/asr-words.py
    python3 scripts/asr-words.py --script script.txt --audio audio/voiceover.wav \
        --out audio/words.json --lang id --vo-delay 1.0

Needs faster-whisper and ffmpeg.
"""

import argparse
import json
import os
import subprocess
import sys
import wave

import numpy as np

ASR_16K = "work/voiceover-16k.wav"


def to_16k(src):
    os.makedirs("work", exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", "16000", "-ac", "1", ASR_16K],
        check=True,
    )
    return ASR_16K


def load_mono16k(path):
    with wave.open(path) as w:
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def tokens(text):
    return [t for t in text.lower().split() if t]


def align_display(asr_text, script_sentences):
    """Pick the script sentence that best matches an ASR segment.

    Token index is enough most of the time; a small overlap score handles the
    cases where ASR splits one written sentence into two segments.
    """
    a = set(tokens(asr_text))
    if not a:
        return asr_text
    best, best_score = asr_text, -1
    for s in script_sentences:
        b = set(tokens(s))
        if not b:
            continue
        score = len(a & b) / len(a | b)
        if score > best_score:
            best, best_score = s, score
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="script.txt")
    ap.add_argument("--audio", default="audio/voiceover.wav")
    ap.add_argument("--out", default="audio/words.json")
    ap.add_argument("--model", default="small")
    ap.add_argument(
        "--lang", default=None, help="pin e.g. 'id'; leave unset to auto-detect"
    )
    ap.add_argument(
        "--vo-delay",
        type=float,
        default=1.0,
        help="seconds of lead-in before the first word on the video timeline",
    )
    args = ap.parse_args()

    if not os.path.exists(args.audio):
        sys.exit(f"{args.audio} not found. Generate or supply the voiceover first.")

    try:
        script = open(args.script, encoding="utf-8").read().strip()
    except FileNotFoundError:
        sys.exit(f"{args.script} not found. It is needed to align the display text.")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit(
            "faster-whisper is not installed. pip install faster-whisper\n"
            "Without it, split time by silencedetect and label the result "
            "as approximate — never present an estimate as measured."
        )

    pcm = load_mono16k(to_16k(args.audio))
    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    segments, info = model.transcribe(
        pcm,
        language=args.lang,  # None auto-detects; a wrong pin corrupts boundaries
        word_timestamps=True,
        vad_filter=False,
    )

    sentences = [
        s.strip() for s in script.replace("\n\n", "\n").split("\n") if s.strip()
    ]

    out = {"vo_delay": args.vo_delay, "language": info.language, "segments": []}
    for seg in segments:
        out["segments"].append(
            {
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text.strip(),  # ASR spelling: kept as-is
                "text_display": align_display(seg.text, sentences),  # script spelling
                "words": [
                    {
                        "word": w.word.strip(),
                        "start": round(w.start, 3),
                        "end": round(w.end, 3),
                    }
                    for w in (seg.words or [])
                ],
            }
        )

    if not out["segments"]:
        sys.exit("ASR returned no segments. Check the audio is not silent.")

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    total = out["segments"][-1]["end"]
    nwords = sum(len(s["words"]) for s in out["segments"])
    print(f"wrote {args.out}")
    print(
        f"  {len(out['segments'])} segments · {nwords} words · {total:.2f}s · lang {info.language}"
    )
    print("  ASR spelling stays in `text` on purpose; only its boundaries matter.")
    print("  Next: node scripts/make-cues.mjs")


if __name__ == "__main__":
    main()
