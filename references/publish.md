# Publish copy — `output/publish.txt`

`scripts/publish.py` writes the upload package. It is the last thing the user
touches before posting, so **every delivery writes it** and every block in it is
copy-paste ready.

```bash
python3 scripts/publish.py \
  --video output/anak-dan-gadget.mp4 \
  --slug "Anak dan Gadget" \
  --captions work/captions.json \
  --script script.txt \
  --voice "Gemini TTS (Kore)" \
  --music "pad sintetis, audio/music.wav"
```

Refuses to run when:
- the video file is missing — render first, write copy second
- `publish.txt` already exists and `--force` was not passed (it may hold
  hand-written copy; losing that is worse than failing)

## What it measures, versus what you write

The script reads the finished file and fills the header itself. Do not type any
of this:

```
ANAK DAN GADGET — PAKET UNGGAH
Video: output/anak-dan-gadget.mp4
Spesifikasi: 1080x1920, 30 fps, 39.0 s (1170 frame), H264 + AAC, I = -17.2 LUFS,
true peak -1.8 dBTP. Berkas 4.8 MB
```

Duration, frame count, codec, resolution and loudness come from `ffprobe` and
`loudnorm`. If the number in the file disagrees with what the agent believes, the
file is right.

You write only the captions, in `work/captions.json`:

```json
{
  "title": "Anak Diam Bukan Berarti Aman",
  "tiktok": "...",
  "reels": "...",
  "shorts": "...",
  "youtube": {"title": "...", "description": "..."},
  "notes": ["Narasi: Gemini TTS (Kore)"]
}
```

## The rules the validator enforces

The script exits non-zero rather than writing a half-finished file. These are
hard checks, not suggestions:

| Rule | Why |
|---|---|
| caption text 150–600 characters | under 150 is a skeleton, not a caption |
| first sentence ≤ ~110 characters | Reels and TikTok truncate around 90 |
| TikTok/Reels 8–15 hashtags, Shorts 3–5 | Shots ignores most tags; a tag wall reads as spam |
| no `link in bio` without a link, no `viral` | both read as bait |
| no emoji wall (3+ in one caption) | |
| **every number must appear in `script.txt`** | copy that invents a statistic is the worst failure here |
| title ≤ 100 characters | YouTube's hard cap |
| duration within the cap for the orientation | 60 s portrait, 300 s landscape |

The number check is the important one. A caption claiming "87 persen anak
kecanduan layar" for a video that never says it is not a style problem — it is a
false claim attached to the user's face.

## Shape

```
=== TikTok
<caption> <hashtags, same block>

=== Instagram Reels
<caption> <hashtags>

=== YouTube Shorts
Judul: <title, <=100 chars>
<caption> <3-5 hashtags>

CATATAN
- <voice, music, duration note>
```

No markdown headings inside the copies, no quotes around them, no placeholder
left in. The `===` lines are for the human reading the file; the text between
them is what gets pasted.

A landscape build adds a `=== YouTube` block with `Judul` and `Deskripsi`
(2–3 short lines, plus a disclaimer when the topic is financial, medical or
legal). A portrait build never gets that block — the script writes a note saying
why it skipped it.

## Writing captions that are worth posting

- **Derived from the finished script.** Every claim is something the video says
  or shows. The validator catches invented numbers; it cannot catch a claim that
  is merely unsupported, so hold yourself to the same rule.
- **The first line is the hook**, and it has to survive truncation. Ask a
  question, or state the surprising fact — do not open with "Video ini tentang".
- **Language follows the narration.** Indonesian voice → Indonesian caption and
  Indonesian hashtags (`#parentingindonesia`, not `#parentingtips`).
- **Tags: one broad, several topical, at most one niche.** Name the subject in
  the tag, not the emotion.
- **Per-platform difference is real.** TikTok can carry the long caption with 10
  tags; Reels reads better short with a save prompt; Shorts wants the title to do
  the work because the caption is collapsed.

## Draft mode

`--allow-skeleton` writes the file anyway, with warnings printed. Use it to show
the user a shape early. **Never ship a draft**: the delivery message names
`publish.txt` as a deliverable, so a skeleton there is a broken promise.