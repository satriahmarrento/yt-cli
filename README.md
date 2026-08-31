# 🎵 YT CLI (Terminal YouTube & Radio Player)

Pemutar YouTube Audio/Video di terminal dengan fitur **YouTube Radio / Mix Autoplay** dan optimasi *low-latency streaming*.

## ✨ Fitur
- **Audio Only Mode (`-m`)**: Streaming musik hemat kuota & tanpa jendela video.
- **Spotify-Style Autoplay (`ytr`)**: Pilih 1 lagu, otomatis putar 25–50+ lagu rekomendasi (*related tracks*) tanpa henti.
- **Kontrol Penuh Keyboard**: Navigasi lagu berikutnya/sebelumnya, volume, dan pause langsung di terminal.
- **Kompatibel Termux (Android)**: 100% jalan di HP Android melalui Termux.

## 🚀 Instalasi Cepat (Linux / macOS / Termux)
```bash
git clone <repo-url> yt-cli
cd yt-cli
bash install.sh
```

## 🎮 Penggunaan
```bash
# 1. Mode Radio Autoplay (Mirip Spotify Radio):
ytr "coldplay yellow"

# 2. Mode Pencarian Standar (Audio Only):
yt -m "lofi hip hop"

# 3. Pilih Banyak Lagu Sekaligus (Queue):
yt -m "queen"  # Gunakan tombol TAB untuk centang beberapa lagu, lalu ENTER
```

## ⌨️ Kontrol Tombol (Keyboard)
| Tombol | Fungsi |
| :--- | :--- |
| **`>`** / **`.`** / **`n`** / **`Enter`** | Lagu Berikutnya (*Next Track*) |
| **`<`** / **`,`** / **`p`** | Lagu Sebelumnya (*Previous Track*) |
| **`Space`** / **`k`** | Pause / Play |
| **`0`** / **`9`** atau **`+`** / **`-`** | Besarkan / Kecilkan Volume |
| **`m`** | Mute / Unmute |
| **`q`** | Keluar |
