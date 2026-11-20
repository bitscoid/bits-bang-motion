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

## Two severities, and why

The validator has two levels because mixing them was a mistake: an earlier
version refused to write the file when a caption carried 7 tags, which would
have blocked a perfectly good caption on a real project.

**Hard — nothing is written, exit 1:**

| Rule | Why it cannot be a warning |
|---|---|
| the video file does not exist | there is nothing to measure, so the header would be invented |
| every number in the copy must appear in `script.txt` | an invented statistic is attached to the user's face; it is not a style choice |
| `publish.txt` exists and `--force` was not passed | it may hold hand-written copy, and that loss cannot be undone |

**Advisory — the file is written, the notes are printed:**

| Hint | Why only a hint |
|---|---|
| caption text 120–600 characters | a short caption can be the right caption |
| first sentence ≤ ~110 characters | the writer judges what the hook is |
| 5–15 hashtags on TikTok/Reels, 3–5 on Shorts | a 7-tag Reels caption was the best file in the folder this was tested against |
| title ≤ 100 characters | YouTube truncates; it does not reject |
| duration within the orientation cap | the user may have approved a longer one |
| a platform block is missing | better three good blocks than a fourth written to satisfy a checker |

Read the advisory list, fix what is worth fixing, then ship. Do not treat it as
a gate — that is what made the first version wrong.

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

`--allow-skeleton` writes the file even when a hard check fails. Use it to show
the user a shape early. **Never ship a draft**: the delivery message names
`publish.txt` as a deliverable, so a skeleton there is a broken promise.

Observed on real files from another skill that used prose rules alone: 17 of 34
`publish.txt` files were still skeletons — "Skeleton otomatis, lengkapi caption
sebelum unggah" — with placeholder tags like `#bad #mood`. The same rules in
prose produced both excellent and unusable output, because nothing forced the
question at the end. That is the reason this script measures the file and asks
for the captions, not the reason to gate style.

## What this script does not do

It does not write the captions. The copy comes from the agent, from the finished
script, and that is where the quality lives — a validator cannot tell a good hook
from a compliant one. It only stops the two failures that a writer cannot catch
about their own work: numbers that were never in the video, and a file quietly
replaced.