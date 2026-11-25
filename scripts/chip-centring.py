#!/usr/bin/env python3
"""Centring check for text inside a chip / badge / tag / card, measured from pixels.

Why: text nudged with a fixed offset (``y + size * 0.34``) or centred only
horizontally reads as misplaced. Judge from the rendered frame, never from the
code that drew it and never by eye.

Usage
  python chip-centring.py shot.png x0 y0 x1 y1            # auto base colour
  python chip-centring.py shot.png x0 y0 x1 y1 --fg 14,20,28
  python chip-centring.py shot.png x0 y0 x1 y1 --json     # machine output

Exit 0 = centred, 1 = off-centre (gaps differ by more than the tolerance).

Library use, when drawing with PIL:
    from chip_centring import ink_box
    ix0, iy0, ix1, iy1 = ink_box(font, "SANDI KUAT", tracking=2)
    w, h = (ix1 - ix0) + 2 * pad_x, (iy1 - iy0) + 2 * pad_y
    d.text((cx - (ix0 + ix1) / 2, cy - (iy0 + iy1) / 2), "SANDI KUAT", font=font, anchor="lm")
"""

import argparse
import json
import sys

import numpy as np
from PIL import Image, ImageFont


def ink_box(font: ImageFont.FreeTypeFont, s: str, tracking: float = 0.0):
    """Real ink box of ``s`` relative to text drawn at anchor 'lm' (no hinting slack)."""
    x, xs, ys = 0.0, [], []
    for ch in s:
        b = font.getbbox(ch, anchor="lm")
        xs += [x + b[0], x + b[2]]
        ys += [b[1], b[3]]
        x += font.getlength(ch) + tracking
    return min(xs), min(ys), max(xs), max(ys)


def measure(path, box, fg=None, tol=4, border=4, radius=14):
    arr = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 + border, y0 + border, x1 - border, y1 - border

    yy, xx = np.mgrid[y0:y1 + 1, x0:x1 + 1]
    hx = np.maximum(np.maximum(0, (x0 + radius) - xx), xx - (x1 - radius))
    hy = np.maximum(np.maximum(0, (y0 + radius) - yy), yy - (y1 - radius))
    mask = (hx ** 2 + hy ** 2) <= radius ** 2  # drop rounded corners + border ring

    area = arr[y0:y1 + 1, x0:x1 + 1]
    if fg is None:  # base = most common colour inside the arc, ink = pixels far from it
        # Without --fg a stroke or border inside the box counts as ink and the
        # result reads as off-centre when it is not (seen: 25/1 reported, 4/4 real).
        # Pass --fg with the text colour whenever the frame has an outline.
        flat = area[mask].reshape(-1, 3)
        warna, hitung = np.unique(flat, axis=0, return_counts=True)
        base = warna[hitung.argmax()]
        d = np.abs(area - base).sum(axis=2)
        ambang = 80
    else:
        d = np.abs(area - np.array(fg, dtype=np.int16)).sum(axis=2)
        ambang = 90

    ys, xs = np.where((d > ambang) & mask)
    if xs.size == 0:
        return None
    tx0, tx1, ty0, ty1 = x0 + xs.min(), x0 + xs.max(), y0 + ys.min(), y0 + ys.max()
    kiri, kanan = tx0 - x0, x1 - tx1
    atas, bawah = ty0 - y0, y1 - ty1
    return {
        "tinta": [int(tx0), int(ty0), int(tx1), int(ty1)],
        "kotak": [x0, y0, x1, y1],
        "kiri": int(kiri), "kanan": int(kanan), "atas": int(atas), "bawah": int(bawah),
        "selisih_mendatar": int(abs(kiri - kanan)),
        "selisih_tegak": int(abs(atas - bawah)),
        "tengah": abs(kiri - kanan) <= tol and abs(atas - bawah) <= tol,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("box", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"))
    ap.add_argument("--fg", help="R,G,B of the text when the background is textured")
    ap.add_argument("--tol", type=int, default=4)
    ap.add_argument("--border", type=int, default=4)
    ap.add_argument("--radius", type=int, default=14)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    fg = tuple(int(v) for v in a.fg.split(",")) if a.fg else None
    r = measure(a.image, tuple(a.box), fg=fg, tol=a.tol, border=a.border, radius=a.radius)
    if r is None:
        print("tidak ada tinta terdeteksi — perluas kotak atau beri --fg"); return 1
    if a.json:
        print(json.dumps(r))
    else:
        print(f"tinta {r['tinta']} · kotak {r['kotak']}")
        print(f"sisa kiri/kanan {r['kiri']}/{r['kanan']} · atas/bawah {r['atas']}/{r['bawah']}")
        print("tengah" if r["tengah"] else
              f"MELESET {r['selisih_mendatar']} px mendatar, {r['selisih_tegak']} px tegak")
    return 0 if r["tengah"] else 1


if __name__ == "__main__":
    sys.exit(main())