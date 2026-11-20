# Images — one script, a fallback chain, and an honest record

There is no built-in image model and no image MCP in this skill. Everything
goes through `scripts/image-gen.py`, which talks to the relay at
`IMG_BASE_URL` (default `http://192.168.50.202:20128/v1`) and falls back down a
measured chain.

Read this before choosing images for a style. Three of the six explainer styles
cannot be built without it.

```bash
export IMG_API_KEY=...                       # required; the relay rejects anonymous calls

python3 scripts/image-gen.py --prompt "flat vector child, thick brown outline, warm palette" \
  --out assets/cutA.png --size 1080x1920
```

## The chain, best first

Order is set by measurement, not by reputation. Numbers below come from a
1024² editorial prompt on the local relay.

| Order | Model (`--model`) | Why here | Wall | Detail | Honours `--size` |
|---|---|---|---|---|---|
| 1 | `phoenix` — `cf/@cf/leonardo/phoenix-1.0` | fastest by a wide margin and the most detailed output measured | ~3 s | highest edge density (12%) | **yes, any size** |
| 2 | `flux2dev` — `cf/@cf/black-forest-labs/flux-2-dev` | highest colour variety, slowest | ~13 s | good | no, 1024 only |
| 3 | `lucid` — `cf/@cf/leonardo/lucid-origin` | fast, but output quality swings run to run | ~5 s | variable | yes |
| 4 | `schnell` — `cf/@cf/black-forest-labs/flux-1-schnell` | reliable but the flattest | ~4–7 s | lowest | no |
| 5 | `pollinations` | public, no key, last resort | ~5 s | — | **no — returns ~768 px and ignores the request** |

`--model <alias>` pins one and **disables the chain**: pinning means "this exact
model or fail", so a failure is reported instead of silently downgraded. The
public fallback only runs when no model was pinned.

## What the relay actually does

Four things learned by testing rather than reading:

- **Every model returns JPEG**, even when the request says
  `"output_format": "png"`. The script re-encodes to real PNG and the output
  path always ends `.png`.
- **`/v1/models` does not list image models.** All 136 entries report
  `imageOutput: false`, yet the endpoint works. Do not try to discover image
  models from that list; use the aliases here.
- **Only `phoenix` and `lucid` honour `size`.** The others answer at 1024²
  whatever you ask for, so the script resizes — that is a real loss of detail on
  a 9:16 build, and the reason `phoenix` is first.
- **Deprecated Cloudflare models fail with HTTP 410**, naming the date they
  died (SDXL base, SDXL Lightning, DreamShaper 8 LCM were all gone on
  2026-11-20). If a model 410s, drop it from the chain rather than retrying.

## Recording where an image came from

Every run appends one JSON line to `work/image-meta.json`:

```json
{"prompt": "...", "requested_size": "1080x1920",
 "model": "cf/@cf/leonardo/phoenix-1.0", "alias": "phoenix",
 "source_size": [1080,1920], "output_size": [1080,1920],
 "output": "assets/scene1.png",
 "attempts": [{"model": "...", "ms": 5136, "error": null}]}
```

**Report the model in the delivery.** "Generated with Phoenix, resized from
1024" is information the user needs; "an illustration" is not. When the public
fallback produced the file, say so — its size is not what was asked for and the
licence terms are not the relay's.

## What needs an image at all

| Style | Assets | Script needed |
|---|---|---|
| 1 Kartun kolase | generated flat illustration → background removed | yes |
| 2 Jurnalisme visual | real photos from Commons/NASA/DVIDS | no — see below |
| 3 Katalog putih | product/person photos, cut backgrounds | yes, or user photos |
| 4 Sketsa vintage | generated engraving-style illustration | yes |
| 5 Aksi kontinu | 100% SVG drawn in code | **no** |
| 6 Kartun panggung | vector body + generated head | yes, head only |

If the relay and the public fallback both fail, **style 5 still works**. Say
that instead of shipping a video with placeholder boxes.

## Prompt discipline

The style brief decides the look; the prompt only executes it. Keep one block
of style words for every asset in a video, or the cutouts will not match:

```
flat vector cartoon, thick warm brown outline, muted teal and mustard
palette, plain cream background, editorial children's-book style
```

Then vary only the subject. Generate the batch, look at the results, and only
then animate.

Never generate a real person's face, a celebrity, or a brand logo. Logos go in
as vector paths; text in generated images is unreliable and should be drawn in
code.

## Background removal

The script does not remove backgrounds. For cutouts on a plain background the
generated image is already close: ask for `plain white background` or
`plain cream background` and cut it out with a threshold, or supply a
transparent PNG from elsewhere.

When a subject sits on a busy background, regeneration is cheaper than
matting — change the prompt before reaching for a remover.

## Failure the script prevents

Both of these were real before the script existed:

- **Writing a 0-byte file.** A 200 response with an empty `b64_json` was
  accepted; the script now treats "no image data" as a failure and moves on.
- **Silent fallback to a public service.** Without a key the script refuses
  instead of quietly sending the prompt somewhere unexpected.