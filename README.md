# 🎵 YT CLI (Terminal YouTube Music & Radio Player)

Pemutar YouTube Music / YouTube Audio/Video di terminal dengan fitur **Radio / Mix Autoplay** dan optimasi *low-latency streaming*. Sumber pencarian default adalah **YouTube Music**, dengan fallback ke YouTube biasa lewat perintah `yty*`.

## ✨ Fitur
- **YouTube Music Default**: Hasil pencarian lagu/resmi lebih relevan (bukan video random).
- **Audio Only Mode (`-m`)**: Streaming musik hemat kuota & tanpa jendela video.
- **Spotify-Style Autoplay (`ytr`)**: Pilih 1 lagu, otomatis putar 20 lagu rekomendasi (*related tracks*) tanpa henti.
- **Smart Instant Autoplay (`ytra`)**: Pilih seed secara weighted random dari hasil YTM, hindari lagu/artist yang sering diulang, dan belajar dari like/dislike/ban.
- **Like / Dislike Saat Memutar**: Tekan `y` untuk like, `x` untuk dislike, `b` untuk ban — algoritma langsung menyesuaikan artist yang kamu suka.
- **Judul Lagu**: Setiap lagu menampilkan `▶ Judul — Artist` di terminal.
- **Data Lokal**: Preferensi disimpan di `~/.config/ytfzf/preferences.json`; riwayat lengkap disimpan di `history.jsonl`.
- **Low-Latency Mix**: URL stream di-resolve di depan (prefetch) dan di-cache, jadi jeda antar-lagu ~1.4 detik, bukan ~6 detik.
- **Single Player**: Satu proses mpv per sesi; menjalankan `ytra` lagi otomatis mematikan sesi lama, jadi tidak ada dua lagu berbunyi bersamaan.
- **Kontrol Penuh Keyboard**: Navigasi lagu berikutnya/sebelumnya, volume, dan pause langsung di terminal.
- **Kompatibel Termux (Android)**: 100% jalan di HP Android melalui Termux.

## 🚀 Instalasi Cepat (Linux / macOS / Termux)
```bash
git clone https://github.com/satriahmarrento/yt-cli.git
cd yt-cli
bash install.sh
```

## 🎮 Penggunaan
```bash
# Sumber default = YouTube Music

# 1. Mode Radio Autoplay (Pilih lagu via menu):
ytr "coldplay yellow"

# 2. Mode Radio Instan Cerdas (weighted seed, belajar dari history):
ytra "coldplay yellow"

# Feedback setelah mendengar lagu (id = video ID dari URL YouTube)
ytm-like   9qnqYL0eNNI "Yellow" "Coldplay"
ytm-dislike gm-Y9idMMQ4 "The Scientist" "Coldplay"
ytm-skip   VIDEO_ID "Judul" "Artist"
ytm-ban    VIDEO_ID "Judul" "Artist"
ytm-show    # lihat preferensi
ytm-reset   # hapus preferensi

# 3. Mode Pencarian Standar (Audio Only):
yt -m "lofi hip hop"

# 4. Pilih Banyak Lagu Sekaligus (Queue):
yt -m "queen"  # Gunakan tombol TAB untuk centang beberapa lagu, lalu ENTER

# 5. Pakai YouTube biasa (bukan YouTube Music):
yty "coldplay yellow"
ytyr "coldplay yellow"
ytya "coldplay yellow"
```

> **Ganti sumber default:** edit `~/.config/ytfzf/conf.sh` lalu ubah
> `scrape="ytmusic"` menjadi `scrape="yt"` untuk kembali sepenuhnya ke YouTube.

## ⌨️ Kontrol Tombol (Keyboard)
| Tombol | Fungsi |
| :--- | :--- |
| **`>`** / **`.`** / **`n`** / **`Enter`** | Lagu Berikutnya (*Next Track*) |
| **`<`** / **`,`** / **`p`** | Lagu Sebelumnya (*Previous Track*) |
| **`Space`** / **`k`** | Pause / Play |
| **`0`** / **`9`** atau **`+`** / **`-`** | Besarkan / Kecilkan Volume |
| **`m`** | Mute / Unmute |
| **`q`** | Keluar |
| **`y`** | Like lagu ini (artist-nya naik) |
| **`x`** | Dislike lagu ini (artist-nya turun) |
| **`b`** | Ban lagu ini (tidak akan diputar lagi) |
