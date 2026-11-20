# Publish copy — `output/publish.txt`

You write the upload package. There is no generator and no validator: the copy
is prose, and prose is what produces good captions when the writer actually
reads the video.

**Write this file in every delivery.** It is the last thing the user touches
before posting; without it they have to write their own caption after watching,
which is work that should already be done.

## Read the finished video, then write

Before a line is written, watch what should be delivered: the exported MP4, not
the plan. Every claim in the copy must already be said or shown in the video.
The hook is not a promise you hope the video keeps.

## What you must measure, not guess

Do not invent these numbers — read them from the file:

```bash
ffprobe -v error -show_entries \
  stream=codec_name,width,height,r_frame_rate,channels:format=duration,size \
  -of default=nw=1 output/<slug>.mp4

ffmpeg -hide_banner -i output/<slug>.mp4 \
  -af loudnorm=print_format=summary -f null - 2>&1 | \
  grep -E "Input Integrated|Input True Peak"
```

The header of `publish.txt` carries those real values:

```
ANAK DAN GADGET — PAKET UNGGAH
Video: output/anak-dan-gadget.mp4
Spesifikasi: 1080x1920, 30 fps, 39.0 s (1170 frame), H264 + AAC stereo,
I = -17.2 LUFS, true peak -1.8 dBTP. Berkas 4.8 MB
```

A header with no measured spec is a skeleton, not a delivery.

## Shape

```
=== TikTok
<caption> <hashtags, same block>

=== Instagram Reels
<caption> <hashtags>

=== YouTube Shorts
Judul: <title, <=100 chars>
<caption> <2-5 hashtags>

CATATAN
- <voice, music, duration, source notes>
```

No markdown headings inside the copies, no quotes around them, no placeholder
left in. The `===` lines are for the human reading the file; the text between
them is what gets pasted.

A landscape build adds a `=== YouTube` block with `Judul` and `Deskripsi`
(2–3 short lines, plus a disclaimer when the topic is financial, medical or
legal). A portrait build never gets that block — say why it was skipped in
`CATATAN` instead of writing a block for a format the video is not.

## Rules of thumb, not gates

These are what the good files do. They are not a checklist to satisfy; a caption
that breaks one deliberately is fine and should not be bent to fit.

| Hint | Reasoning |
|---|---|
| caption 120–600 characters | shorter than that is usually a title, not a caption |
| first sentence ≤ ~110 characters | Reels and TikTok truncate around 90; the hook has to survive |
| 5–15 hashtags on TikTok/Reels, 3–5 on Shorts | Shorts ignores most tags; past 15 reads as a tag wall |
| title ≤ 100 characters | YouTube's hard cap — the only real limit in this table |
| mix the tags: one broad, several topical, at most one niche | name the subject, not the emotion |
| per-platform difference is real | TikTok carries the long caption, Reels reads better short with a save prompt, Shorts leans on the title because the caption is collapsed |

## Failure that is not a style question

One thing here is genuinely wrong rather than different: **a number in the copy
that the video never says.** A caption claiming "87 persen anak kecanduan layar"
for a video that never mentions it is not a style choice — it is a false claim
attached to the user's face.

Check every figure, percentage, year and count in the copy against `script.txt`
before writing the file. If it is not there, remove it or put it in the video
first.

Two more that are not style:

- **Never overwrite an existing `publish.txt` without reading it.** It is the one
  file the user may have edited by hand.
- **Never write the file before the video exists.** Without a finished file there
  is nothing to measure, so the header would be invented.

## Writing captions that are worth posting

- **Derived from the finished script.** Every claim is something the video says
  or shows.
- **The first line is the hook** and it must survive truncation. Ask a question,
  or state the surprising fact — do not open with "Video ini tentang".
- **Language follows the narration.** Indonesian voice → Indonesian caption and
  Indonesian hashtags (`#parentingindonesia`, not `#parentingtips`).
- **Never include**: emoji walls, "link in bio" when there is no link, declared
  statistics, or the word "viral".
- **Do not ship a skeleton.** If the copy is not ready, say so and deliver
  without the claim that `publish.txt` is done — a file reading "lengkapi
  caption sebelum unggah" is a broken promise, not a draft.

## Why there is no script for this

It was tried. A generator that measured the file and validated the captions was
written and removed: it rejected a caption carrying 7 tags that was, by the
user's own judgement, the best copy in the project. Compliance is not quality,
and a script cannot tell a good hook from a compliant one.

The one part that a writer cannot check about their own work is the invented
number, and that is caught by re-reading `script.txt` — which is a step in the
rules above, not a program.