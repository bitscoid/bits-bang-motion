# Voiceover — script, TTS, word timing

Everything a narrated build needs, in this skill. No other skill has to be
installed to follow it.

- how a word timestamp becomes a GSAP tween (`saySync`)
- how `DUR` stops being a constant
- how the audio reaches `index.html` without a server
- how the MP4 gets its audio track

Read this when the user supplies a voiceover, or asks for one to be generated.

## 1. The order never changes

```
script → TTS (or user recording) → audio/voiceover.wav → word timing
      → audio/cues.js → index.html timeline → frames
      ↓
music bed (optional, most videos) → ducked mix → MP4 (mux audio)
```

Voice and music are two decisions, not one. A narrated video almost always
wants a bed underneath it — that is what makes it read as finished rather than
as a screen recording with a voice. Ask for both in the brief
(`references/explainer.md`, "Langkah nol"); the default when there is a voice is
music **on**.

| Voice | Music | What it is for |
|---|---|---|
| generated / recorded | yes | the common case: narration over a ducked bed |
| generated / recorded | no | interview or demo; dry but valid |
| none | yes | bumper, opener, mood piece — text carries the story |
| none | no | silent slideshow, or audio to be added later |

**This file applies whenever either audio track exists.** A silent build never
opens it. And do not quietly turn "generate" into "no voice" when a key or
quota is missing: say what happened and offer the recording route instead.

**Write the script first and get it approved.** Never generate audio for a
script the user has not read. Audio is the clock for everything after it; a
rewritten script means every tween moves.

Save it as `vo-script.md` **and** `script.txt`:

- `vo-script.md` — what the user reads, with `## Adegan 1` headings so each
  paragraph maps to one scene.
- `script.txt` — the same prose with headings and labels stripped, verbatim
  only. This is what the TTS receives and what ASR is aligned back against.

Labels such as `[Hook]` or `## Adegan 2` must never reach `script.txt`: the
TTS model reads text verbatim and will speak them aloud.

## 2. Generating the voice

Run the script. It builds the payload, handles the model fallback, parses the
response and checks the result against the script:

```bash
# Tidak perlu export: kunci dibaca dari /root/.hermes/keys/*.key dan dirotasi
python3 scripts/tts-gemini.py        # script.txt -> audio/voiceover.wav
python3 scripts/tts-gemini.py --voice Puck --style "bright, playful"
python3 /root/.hermes/keys/gemini_key.py   # cek berapa kunci siap
```

Kalau kuota satu kunci habis, skrip pindah sendiri ke kunci berikutnya dan
mencetak `(key#N)` — jangan hentikan run hanya karena satu kunci kena 429.

Defaults: `gemini-3.8-flash-tts`, voice `Kore`, style
`warm, clear, slightly upbeat`. Working voices — `Kore` (firm), `Puck`
(bright), `Charon` (informative), `Zephyr` (clear), `Leda` (young/female).
Names are case-sensitive. Say which one you used in the delivery.

What the script gets right that a hand-rolled call does not:

| Trap | What it does |
|---|---|
| Script inlined into `curl -d` | builds the payload with `json.dumps`, so quotes and newlines stay valid |
| Instructions written inside `text` | sends verbatim prose only; delivery lives in `annotations[].style` |
| `[Hook]`, `## Adegan` spoken aloud | those never reach `script.txt` — the model reads text verbatim |
| Daily quota hit | falls back to `gemini-3.8-flash-lite-tts`, a separate quota |
| Length nothing like the script | warns when the duration misses the word-count estimate by more than 35% |
| Raw PCM from an older model | decodes 24 kHz s16le, then writes 48 kHz mono |

On failure the full API response is left in `work/tts-response.json`:

- `No matching speaker voice found for name: X` → wrong voice name
- `Invalid JSON payload received` → the script prevents this; if it appears,
  something edited the request file
- `RESOURCE_EXHAUSTED` on both models → the daily quota is gone; ask the user
  to record the script and say so plainly

**Check the result before moving on:**

```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 "audio/voiceover.wav"
```

Compare with `words ÷ 2.5` (roughly Indonesian narration speed). A large gap
means non-script text was spoken, or the script was cut short. Regenerate
once; if it still makes no sense, tell the user instead of continuing.

**Duration cap.** This skill has no cap of its own; take the one the user
approved in the brief. Portrait (9:16) and landscape (16:9) are different
products, not a preference — a 5-minute portrait clip is unwatchable in a
feed, and a 60-second landscape explainer under-delivers its format. If the
audio overruns the agreed length, cut the script and regenerate. Never speed
up the audio to fit.

**No API key, or the user wants their own voice:** ask them to record
`script.txt` and send the file. Normalise it the same way and continue from
§3 — nothing downstream cares where the audio came from.

```bash
ffmpeg -v error -y -i <their-file> -ar 48000 -ac 1 "audio/voiceover.wav"
```

## 3. Word timing

```bash
python3 scripts/asr-words.py                 # audio/voiceover.wav -> audio/words.json
python3 scripts/asr-words.py --lang id       # pin it; unset = auto-detect
```

What it produces, and why each field exists:

```json
{ "vo_delay": 1.0, "language": "id",
  "segments": [
    { "start": 0.2, "end": 4.6,
      "text": "anak bukan kertas kosong",
      "text_display": "Anak bukan kertas kosong.",
      "words": [{ "word": "anak", "start": 0.2, "end": 0.65 }] }
  ] }
```

- `text` stays exactly as recognised. Only its **boundaries** matter, and
  correcting the spelling there would hide a bad transcription instead of
  surfacing it.
- `text_display` is aligned back to `script.txt`, so subtitles and on-screen
  text carry the words you approved, not the ones Whisper heard.
- `vo_delay` is the lead-in before the first word on the video timeline. Keep
  it as one constant and derive every time from it — never add it per scene.
- `audio/`, not `work/`. Re-running ASR after a cleanup returns timestamps
  that differ by ~±0.1 s, which silently desyncs a re-render. Sitting beside
  `voiceover.wav` makes it a durable project input.

If ASR cannot be installed: split time by `silencedetect` pauses, distribute
words per phrase by syllable count, and **tell the user the sync is
approximate**. Never present an estimate as measured.

Then convert it into something a `<script src>` tag can load:

```bash
node scripts/make-cues.mjs          # audio/words.json -> audio/cues.js
```

Why a JS file instead of `fetch('words.json')`: this skill promises a
double-clickable `index.html`. `fetch()` is blocked by CORS on `file://`, but
a classic `<script src="audio/cues.js">` is not. The page must work with no
server, so the timing ships as script.

`audio/cues.js` is generated — never hand-edit it. It looks like:

```js
// generated by scripts/make-cues.mjs — do not edit
window.CUES = {
  voDelay: 1.0,
  dur: 47.2,
  segments: [
    {start: 1.0, end: 5.3, text: "Kalimat pertama.",
     words: [{w: "Kalimat", t: 1.0, e: 1.28}, {w: "pertama", t: 1.32, e: 1.86}]}
  ]
};
```

`t` and `e` are absolute video seconds, already shifted by `voDelay`. Do not
add the delay again anywhere else.

**`audio/` is durable, `work/` is not.** Re-running ASR after a cleanup
returns timestamps that differ by ~±0.1 s, which silently desyncs a re-render.
`audio/words.json` and `audio/cues.js` sit beside `voiceover.wav` so
`rm -rf work` loses nothing that matters.

Never sweep the project with a broad `rm -rf`, and never delete a source a
revision would need (`voiceover.wav`, `words.json`, `cues.js`, `script.txt`,
`index.html`, the final MP4). Full rule: SKILL.md workflow #8.

## 4. Putting the audio in the page

The starters already ship the hook — `<audio id="vo" src="">` and a ticker
that nudges `vo.currentTime` back onto `tl.time()` when they drift. Two edits:

```html
<audio id="vo" src="audio/voiceover.wav" preload="auto"></audio>
```

```html
<script src="audio/cues.js"></script>   <!-- before the timeline script -->
```

Then `DUR` comes from the cue file instead of a constant:

```js
const W = /* from ?ratio=, see §6 */ 1920;
const H = /* ... */ 1080;
const DUR = (window.CUES?.dur ?? 18) + (window.CUES ? 0.6 : 0);  // tail after the last word
```

The 0.6 s tail is deliberate: a video that stops on the final syllable feels
cut off. Without `cues.js` the constant still applies, so a silent build keeps
working.

**A longer `DUR` does not build scenes for you.** The starters end with
`tl.to({}, {duration: .01}, DUR)` — a spacer that stretches the timeline to
`DUR`, not a scene. If the audio runs 47 s and your last scene ends at 18 s,
seconds 18–47 are a static frame. That is the one failure this mechanism can
cause: the render succeeds, the duration is right, and the back half is dead.

So when the voice is longer than the example choreography, **add scenes until
the last one ends near `DUR`** — check with a snapshot at `DUR - 3`. A spacer at
the end is the safety net, not the plan.

## 5. Making text land on its word

The starters' `say(sel, at)` staggers a whole line decoratively. That is
correct for a line with no voiceover, and wrong for a line that has one.

Use `saySync` for any line whose sentence is in `cues.js`:

```js
/* Per-word entry, driven by real timings instead of a decorative stagger.
   ws must be the same per-word spans the starter already builds (.w). */
const saySync = (sel, seg, {dur = .42} = {}) => {
  const el = $(sel), ws = words(el);
  tl.set(el, {opacity: 1}, seg.start - .05);
  seg.words.forEach((cue, i) => {
    const span = ws[i];
    if (!span) return;                        // ASR and markup disagree: skip, do not guess
    tl.fromTo(span,
      {opacity: 0, yPercent: 60, scaleY: 1.25},
      {opacity: 1, yPercent: 0, scaleY: 1, duration: dur, ease: 'power4.out',
       immediateRender: false},               // REQUIRED: otherwise a seek shows the end state
      cue.t);
  });
  blurTween(tl, el, seg.start - .05, 22, 0, dur + .3, VERT);
  $$('.hl i', el).forEach((h, i) =>
    tl.fromTo(h, {scaleX: 0}, {scaleX: 1, duration: .4, ease: 'power3.out',
      immediateRender: false}, (seg.words[seg.words.length - 1]?.e ?? seg.end) + .2 + i * .2));
};
```

Rules that make or break this:

- **`immediateRender: false` on every `fromTo` that a seek will touch.** The
  starters already depend on this; omit it once and a snapshot capture shows
  the finished state instead of the entry.
- **Span count must match word count.** If ASR splits one written word into
  two, the extra cue has no span — skip it and tell the user. Do not
  redistribute cues across spans by guesswork.
- **One line per sentence.** A sentence broken across two `.line` elements
  cannot be synced word-by-word; merge it or split the cue.
- **`unsay` still clears the line.** Call it at `seg.end + .1`, not at a
  guessed time.

For silent lines keep `say()` — it is not replaced, only supplemented.

## 6. Ratio: `?ratio=9x16`

Adding a fifth portrait starter would mean maintaining six near-identical
files. One query parameter is enough.

In every starter, replace the hardcoded stage metrics with a read of the
parameter:

```js
const q = new URLSearchParams(location.search);
const PORTRAIT = q.get('ratio') === '9x16';
const W = PORTRAIT ? 1080 : 1920;
const H = PORTRAIT ? 1920 : 1080;
$('#stage').style.width  = W + 'px';
$('#stage').style.height = H + 'px';
```

The camera rig centres on `W/2, H/2`. In the starters that is written as
`960, 540`; replace those literals with `W/2, H/2` in `applyCam`, `C`, and
`home()`. Anything else hardcoded to 960/540 — scene offsets, the `look()`
targets — must move too, or the composition hangs off-frame.

Text size does **not** scale down with the stage. Follow
`references/explainer.md` §"Keterbacaan di ponsel": body 44 px, label 34 px,
headline ≥100 px on the 1080-wide side. A 9:16 build keeps the landscape
sizes; they are measured against the short side, not the long one.

## 7. Exporting the MP4 — with sound

`scripts/export-frames.mjs` writes PNGs only. Read `WIDTH` and `HEIGHT` so it
captures the portrait stage, then build the audio track and mux it.

**Build the mix first, export second.** Doing it in one ffmpeg call means you
cannot hear the balance before the expensive frame render.

**Step 1 — the audio mix.** A video with voice and music wants both, with the
music ducked:

```bash
# music bed, length from CUES.dur (or DUR0 for a silent build)
python3 scripts/make_music.py --duration 47 --out audio/music.wav

# voice + ducked bed -> one track
ffmpeg -v error -y -i audio/voiceover.wav -i audio/music.wav \
  -filter_complex "\
[1:a]volume=0.30[m];\
[m][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[duck];\
[0:a][duck]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[out]" \
  -map "[out]" -ar 48000 -ac 2 audio/mix.wav
```

`normalize=0` is not optional: without it `amix` divides by the input count and
the whole mix drops ~10 dB. Measured on a 20 s test, the bed sat 6.5 dB lower
under speech and returned between sentences.

**A filter label may be consumed once.** Using `[vo]` as both the
`sidechaincompress` key and an `amix` input yields a mix with the voice
silently gone — ffmpeg does not error, and the result is a bed with holes where
the narration was. Split it: `[1:a]…,asplit=2[vo][key];` then
`[bed][key]sidechaincompress…[duck]; [vo][duck]amix…[out]`.

Symptom to watch for: ASR of the finished MP4 returns one unrelated sentence
(often a stock sign-off in another language) instead of the script. That means
the voice is missing, not that Whisper failed — check the mix before
regenerating anything. Confirm sync by normalised cross-correlation of the MP4
waveform against `voiceover.wav` (8 kHz mono, expect the peak at `voDelay`,
corr > 0.99); `silencedetect` cannot answer this once a bed is under the voice.

No music, voice only → skip the filter and use `audio/voiceover.wav` directly.
Music only → skip this step and use `audio/music.wav`.

**Step 1b — measure the mix and bring it into band.** The summed mix never
lands on target by itself; measured on a 20 s test it came out −21.2 LUFS,
below the band in §8. Normalise the mix, not the pieces:

```bash
ffmpeg -i audio/mix.wav -af loudnorm=print_format=summary -f null -   # read the number

ffmpeg -v error -y -i audio/mix.wav -af loudnorm=I=-16:TP=-1.5:LRA=11 \
  -ar 48000 -ac 2 audio/mix-norm.wav                                  # only if out of band
```

Same test after the second command: −15.9 LUFS. Export with `mix-norm.wav`
when you normalised; use `mix.wav` when it was already in band. Report the
number either way.

**Step 2 — the delay.** The cue timings are already shifted onto the video
timeline, so the audio must be shifted by the same amount or every word lands
early and `-shortest` cuts the last line off:

```bash
DELAY_MS=$(node -e "console.log(Math.round((window.CUES?.voDelay ?? 1)*1000))" 2>/dev/null || echo 1000)
```

Use the `voDelay` in `audio/cues.js`, not the literal 1000. With no voiceover
there is no delay to compensate for: set `DELAY_MS=0` (and pass `--no-delay`
to `make-cues.mjs` so the timings themselves start at zero).

**Step 3 — render and mux.**

```bash
npm i puppeteer
python -m http.server 5178 &

WIDTH=1080 HEIGHT=1920 FPS=30 node scripts/export-frames.mjs

# MIX=audio/mix-norm.wav when step 1b normalised, otherwise audio/mix.wav
MIX=audio/mix-norm.wav

ffmpeg -framerate 30 -i frames/f%05d.png -i "$MIX" \
  -af "adelay=${DELAY_MS}:all=1,apad" \
  -c:v libx264 -pix_fmt yuv420p -crf 16 \
  -c:a aac -b:a 192k -shortest output/<slug>.mp4
```

`adelay` shifts the audio later; `apad` then pads silence so `-shortest` ends
on the last **video** frame instead of the last **audio** sample.

Measured on a 20.6 s portrait build with `voDelay: 1.0`: without the delay the
file came out 19.6 s and the final sentence was clipped; with it, 20.6 s and
every word present. Always `ffprobe` the result and compare against
`CUES.dur`.

If the page is served over `file://` there is no server to poll, but the audio
still needs muxing — the commands above do not change.

## 8. Loudness — not optional

A platform targets **I ∈ [−17, −14] LUFS, true peak ≤ −1 dBTP**. A quiet mix
passes every visual check and still plays badly everywhere.

**Measure the finished mix, not the voice track.** The summing in §7 always
changes the level — a 20 s test came out −21.2 LUFS from a voice that was
already in band on its own. The measure-and-normalise step is §7 step 1b;
there is no separate voice-only correction to apply.

Report the measured value in the delivery message. A build without a number is
a build nobody verified.

## 9. Music bed — what make_music.py actually gives you

The command and the ducking recipe are in §7. This section is only what you
need in order to choose and to describe it honestly.

```bash
python3 scripts/make_music.py --duration 47 --out audio/music.wav \
    --brief "grup chat kacau, tegang, ritmis, urban, digital"
```

`--brief` **wajib** dan ditulis dari topik video — bukan disalin dari film
sebelumnya. Brief menentukan skala (minor/dorian/major/lydian/phrygian/
mixolydian), progresi akor fungsional, keluarga timbre (kapur/kayu/kaca/logam),
gerak bass (root/oktaf/walking), kerapatan arp, tekstur, dan tempo — lalu
menjadi benih acak, jadi brief sama menghasilkan audio identik (re-render tidak
menggeser musik dari gambar yang sudah disinkronkan).

`--duration` harus menutup video jadi — ambil dari `CUES.dur`, bukan dari
panjang naskah. Opsional: `--tempo` untuk memaksa BPM, `--seed` untuk mengambil
varian lain dari brief yang sama. Kalau topiknya butuh musik yang tidak bisa
disintesis di sini (instrumen daerah tertentu, lagu jadi), kirim
`audio/music.wav` sendiri — berkas user selalu dipakai lebih dulu.

The output is a pad, a bass, an arpeggio and a breath at each chord change — a
progression with a pulse, not a composition. **Say it is synthesised** in the
delivery; do not present it as licensed music.

It is a bed, not a score: no intro sting, no outro, no hit on a specific beat.
If a video needs an accent on one moment, place a short sound there rather
than regenerating the track.

If the user sends their own music, it goes through the same `volume` +
`sidechaincompress` treatment in §7 — the ducking is what makes any bed sit
under a voice, not something specific to the generated one. Ask them to
confirm the licence; this skill ships no music library and can make no claim
about theirs.

## 10. When any of this is skipped

Say so plainly in the delivery, in the user's language:

- no audio → "video bisu, siap diberi VO kapan saja"
- timings estimated from word count rather than ASR → "sinkron kata
  perkiraan, bisa meleset ±0.5 dtk"
- no loudness measurement → do not claim the mix is correct

Never describe an estimated sync as measured.