# Publish copy — `output/publish.txt`

Kamu yang menulis paket unggah. Tidak ada generator dan tidak ada validator:
copy ini prosa, dan prosa bagus lahir saat penulisnya benar-benar menonton
videonya.

**Tulis file ini di SETIAP delivery.** Ini hal terakhir yang disentuh user
sebelum posting; tanpa file ini dia harus menulis caption sendiri setelah
menonton, padahal itu kerja yang seharusnya sudah selesai.

## Baca video jadi dulu, baru menulis

Sebelum satu baris ditulis, tonton yang akan dikirim: MP4 hasil ekspor, bukan
rencananya. Setiap klaim di copy harus sudah diucapkan atau diperlihatkan di
video. Hook bukan janji yang kamu harap ditepati video.

## Yang harus diukur, bukan ditebak

Jangan mengarang angka — baca dari file:

```bash
ffprobe -v error -show_entries \
  stream=codec_name,width,height,r_frame_rate,channels:format=duration,size \
  -of default=nw=1 output/<slug>.mp4

ffmpeg -hide_banner -i output/<slug>.mp4 \
  -af loudnorm=print_format=summary -f null - 2>&1 | \
  grep -E "Input Integrated|Input True Peak"
```

Header `publish.txt` memakai enam baris ini (kunci Inggris, nilai Indonesia)
supaya file bisa diurutkan dan diparse:

```
# PROYEK : <slug>
# VIDEO  : <slug>/output/<slug>.mp4
# CHANNEL: BITS Style | BITS Tech | BITS Living
# DURASI : <detik, satu desimal>
# STATUS : SIAP | PERLU-REVIEW
# UPDATE : <YYYY-MM-DD> (<satu kalimat apa yang berubah>)
```

Angka spesifikasi terukur (fps, jumlah frame, LUFS, true peak, ukuran MB) masuk
blok `CATATAN`, bukan header. Header dengan durasi karangan adalah skeleton,
bukan delivery.

## Bentuk lengkap publish.txt (BITS, 2026-11-21)

Ini satu-satunya bentuk yang berlaku. Tidak ada aturan caption lain.

```
# PROYEK : <slug>
# VIDEO  : <slug>/output/<slug>.mp4
# CHANNEL: BITS Style | BITS Tech | BITS Living
# DURASI : <detik, satu desimal>
# STATUS : SIAP | PERLU-REVIEW
# UPDATE : <YYYY-MM-DD> (<apa yang berubah>)

=== TikTok
<description 30–45 kata, satu paragraf>

<5–8 hashtag>

=== Instagram Reels
<description>

<5–8 hashtag>

=== YouTube Shorts
Judul: <judul maks 100 karakter>
<description>

<5–8 hashtag termasuk #Shorts>

CATATAN
- <VO, musik, LUFS, sumber — blok internal, tidak pernah dibaca Buffer>
```

Di dalam blok platform hanya ada dua hal: satu paragraf description, dan satu
baris hashtag. Tidak ada baris lain.

### Description bukan script

Script sampai ke penonton lewat jalur suara. Caption dibaca orang yang sedang
memutuskan mau menonton atau tidak, dan dibaca mesin pencari. Menyalin baris VO
ke caption membuang dua fungsi itu sekaligus.

Tiap description punya tiga gerak:

1. **Hook** — masalah atau kejadian yang relatable, bukan kalimat pembuka VO.
   Harus selamat dari pemotongan ~90 karakter pertama.
2. **Nilai** — apa yang penonton dapat setelah menonton, ditulis dengan kata
   yang orang benar-benar cari ("cara menyimpan beras", "takaran deterjen").
3. **Jangkar** — sebut apa yang ada di video ("ini urutan pemeriksaannya").

30–45 kata, satu paragraf, tanpa emoji, tanpa em dash.

### Hashtag

Satu baris, 5–8 tag: 2–3 topik besar, 2–3 spesifik, 1 tag channel
(`#bitsstyle` / `#bitscoid` / `#bitsliving`), tambah `#Shorts` khusus blok
YouTube. Sebut subjeknya, bukan emosinya.

### Dilarang di blok platform

- CTA apa pun: "Hubungi kami", "link di bio", "follow untuk part 2".
- Baris `Video dibuat dengan bantuan AI.` — disclosure sudah tidak dipakai di
  caption maupun di frame.
- Baris `Musik: ...` atau atribusi musik apa pun.
- Angka, persentase, tahun, atau hitungan yang tidak ada di `script.txt`.
- Dinding emoji, kata "viral", statistik karangan.

### Aturan berkas

- Tidak ada heading markdown di dalam blok, tidak ada tanda kutip pembungkus,
  tidak ada placeholder tersisa.
- Baris `===` hanya penanda bagi manusia; teks di antaranya yang ditempel.
- Build landscape menambah blok `=== YouTube` dengan `Judul` dan `Deskripsi`
  (2–3 baris pendek, plus disclaimer bila topiknya finansial, medis, atau
  hukum). Build portrait tidak pernah dapat blok itu — jelaskan alasannya di
  `CATATAN`, jangan tulis blok untuk format yang bukan videonya.
- **Jangan menimpa `publish.txt` yang sudah ada tanpa membacanya.** Itu
  satu-satunya file yang mungkin sudah diedit tangan.
- **Jangan menulis file sebelum video jadi.** Tanpa file jadi tidak ada yang
  bisa diukur, jadi header akan berisi angka karangan.
- **Jangan kirim skeleton.** Kalau copy belum siap, bilang terus terang dan
  kirim tanpa klaim `publish.txt` selesai — file berisi "lengkapi caption
  sebelum unggah" itu janji rusak, bukan draf.

## Angka yang tidak ada di video = cacat, bukan selera

Satu hal di sini benar-benar salah, bukan sekadar berbeda: **angka di copy yang
tidak pernah diucapkan video.** Caption yang mengklaim "87 persen anak kecanduan
layar" untuk video yang tidak menyebutnya bukan pilihan gaya — itu klaim palsu
yang ditempel ke wajah user.

Periksa setiap angka, persentase, tahun, dan hitungan di copy terhadap
`script.txt` sebelum menulis file. Kalau tidak ada di situ, hapus atau masukkan
dulu ke videonya.

## Menyebar ke post Buffer yang sudah terjadwal

Caption post yang sudah ada di Buffer tidak ikut berubah saat file diperbaiki.
Jalankan:

```bash
python3 /root/BITS/scripts/buffer-caption-bersih.py          # dry-run, tampilkan diff
python3 /root/BITS/scripts/buffer-caption-bersih.py --apply  # editPost id + text
```

Aset dan `dueAt` tidak tersentuh; hanya `text`.

## Kenapa tidak ada skrip penulis caption

Sudah dicoba. Generator yang mengukur file dan memvalidasi caption pernah
ditulis lalu dihapus: ia menolak caption dengan 7 tag yang justru, menurut
penilaian user sendiri, copy terbaik di proyek itu. Kepatuhan bukan kualitas,
dan skrip tidak bisa membedakan hook bagus dari hook yang patuh aturan.

Satu-satunya bagian yang penulis tidak bisa periksa pada karyanya sendiri adalah
angka karangan, dan itu tertangkap dengan membaca ulang `script.txt` — langkah
di aturan atas, bukan program.