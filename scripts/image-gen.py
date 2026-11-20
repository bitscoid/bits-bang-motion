#!/usr/bin/env python3
"""Generate an image with a fallback chain, and say which model produced it.

Chain, best first (order set by measurement, see references/imagegen.md):

  1. cf/@cf/leonardo/phoenix-1.0               fastest, only one that honours
                                               the requested pixel size
  2. cf/@cf/black-forest-labs/flux-2-dev        highest detail, slow, 1024 fixed
  3. cf/@cf/leonardo/lucid-origin               fast, variable quality
  4. cf/@cf/black-forest-labs/flux-1-schnell    fast, flattest output
  5. Pollinations (public, no key)              last resort, ignores the size

Every attempt is recorded, so the delivery can name the model instead of
guessing. Needs requests and Pillow; ffmpeg not required.

Usage:
    python3 scripts/image-gen.py --prompt "flat vector child, warm palette" --out assets/cutA.png
    python3 scripts/image-gen.py --prompt "..." --out out.png --size 1080x1920
    python3 scripts/image-gen.py --prompt "..." --out out.png --model phoenix
    python3 scripts/image-gen.py --prompt "..." --out out.png --json

Endpoint defaults to the local relay; override with IMG_BASE_URL.
"""

import argparse
import base64
import io
import json
import os
import sys
import time

import requests
from PIL import Image

BASE = os.environ.get("IMG_BASE_URL", "http://192.168.50.202:20128/v1")
KEY = os.environ.get("IMG_API_KEY") or os.environ.get("NINEROUTER_API_KEY", "")
ENDPOINT = f"{BASE}/images/generations"

# alias -> model id. Order in CHAIN is the fallback order.
ALIASES = {
    "phoenix": "cf/@cf/leonardo/phoenix-1.0",
    "flux2dev": "cf/@cf/black-forest-labs/flux-2-dev",
    "lucid": "cf/@cf/leonardo/lucid-origin",
    "schnell": "cf/@cf/black-forest-labs/flux-1-schnell",
    "pollinations": "pollinations",
}
CHAIN = ["phoenix", "flux2dev", "lucid", "schnell"]

MODELS_THAT_HONOUR_SIZE = {"phoenix", "lucid"}


def log(msg):
    print(msg, file=sys.stderr)


def request_model(alias, prompt, size, timeout):
    """Return raw image bytes, or raise with a readable reason."""
    model = ALIASES[alias]
    payload = {"model": model, "prompt": prompt, "n": 1}
    if size and alias in MODELS_THAT_HONOUR_SIZE:
        payload["size"] = size

    r = requests.post(
        ENDPOINT,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")

    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"not JSON: {r.text[:120]}")

    if "error" in data:
        # the relay wraps provider errors in one string; the useful part is first
        raise RuntimeError(str(data["error"])[:200])

    for item in data.get("data", []):
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img = requests.get(url, timeout=timeout)
            img.raise_for_status()
            return img.content
    raise RuntimeError("response had no image data")


def request_pollinations(prompt, size, timeout):
    """Public fallback. Ignores the requested size — the caller resizes."""
    w, h = size.split("x") if size else ("1024", "1024")
    url = (
        "https://image.pollinations.ai/prompt/"
        + requests.utils.quote(prompt, safe="")
        + f"?width={w}&height={h}&nologo=true"
    )
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def to_png(raw, out, size):
    """Normalise whatever came back — every relay model returns JPEG."""
    im = Image.open(io.BytesIO(raw))
    original = im.size
    im = im.convert("RGB")
    if size:
        w, h = (int(v) for v in size.lower().split("x"))
        if im.size != (w, h):
            im = im.resize((w, h), Image.LANCZOS)
    out = os.path.splitext(out)[0] + ".png"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    im.save(out, "PNG")
    return out, original, im.size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True, help="path; .png is forced")
    ap.add_argument("--size", default=None, help="WxH, e.g. 1080x1920")
    ap.add_argument(
        "--model",
        default=None,
        help=f"force one model: {', '.join(ALIASES)}; no fallback",
    )
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--json", action="store_true", help="print a result object")
    args = ap.parse_args()

    if not KEY:
        log(
            "IMG_API_KEY is not set. The relay needs a bearer token; refusing "
            "rather than silently falling through to a public service."
        )
        sys.exit(1)

    order = [args.model] if args.model else list(CHAIN)
    if args.model and args.model not in ALIASES:
        sys.exit(f"unknown model {args.model}; choose from {', '.join(ALIASES)}")

    attempts = []
    raw, used = None, None

    def try_one(alias):
        t0 = time.time()
        try:
            got = (
                request_pollinations(args.prompt, args.size, args.timeout)
                if alias == "pollinations"
                else request_model(alias, args.prompt, args.size, args.timeout)
            )
        except Exception as e:
            attempts.append(
                {"model": ALIASES[alias], "ms": int((time.time() - t0) * 1000),
                 "error": str(e)[:200]}
            )
            log(f"  {alias}: {str(e)[:110]}")
            return None
        attempts.append(
            {"model": ALIASES[alias], "ms": int((time.time() - t0) * 1000), "error": None}
        )
        return got

    for alias in order:
        raw = try_one(alias)
        if raw:
            used = alias
            break

    # Public fallback only when no model was pinned: pinning means "this exact
    # model or fail", not "or something from the internet".
    if raw is None and args.model is None:
        raw = try_one("pollinations")
        if raw:
            used = "pollinations"

    if raw is None:
        log("every model failed. Nothing was written.")
        for a in attempts:
            if a["error"]:
                log(f"  {a['model']}: {a['error']}")
        sys.exit(1)

    path, original, final = to_png(raw, args.out, args.size)
    meta = {
        "prompt": args.prompt,
        "requested_size": args.size,
        "model": ALIASES.get(used, used),
        "alias": used,
        "source_size": list(original),
        "output_size": list(final),
        "output": path,
        "attempts": attempts,
    }
    with open("work/image-meta.json", "a", encoding="utf-8") as f:
        os.makedirs("work", exist_ok=True)
        f.write(json.dumps(meta, ensure_ascii=False) + "\n")

    if args.json:
        print(json.dumps(meta, ensure_ascii=False))
    else:
        extra = ""
        if original != final:
            extra = f" (from {original[0]}x{original[1]}, resized)"
        print(f"{path} — {final[0]}x{final[1]}{extra} · {ALIASES.get(used, used)}")


if __name__ == "__main__":
    main()
