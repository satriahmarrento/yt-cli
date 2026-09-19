# 🎵 YT CLI (Terminal YouTube & Radio Player)

Pemutar YouTube Audio/Video di terminal dengan fitur **YouTube Radio / Mix Autoplay** dan optimasi *low-latency streaming*.

## ✨ Fitur
- **Audio Only Mode (`-m`)**: Streaming musik hemat kuota & tanpa jendela video.
- **Spotify-Style Autoplay (`ytr`)**: Pilih 1 lagu, otomatis putar 20 lagu rekomendasi (*related tracks*) tanpa henti.
- **Instant Autoplay (`ytra`)**: Putar langsung hasil pertama tanpa fzf picker.
- **Low-Latency Mix**: Dibatasi 20 playlist-end & no-sub untuk start instan (< 2 detik).
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
# 1. Mode Radio Autoplay (Pilih lagu via menu):
ytr "coldplay yellow"

# 2. Mode Radio Instan (Auto-select lagu pertama, tanpa menu):
ytra "coldplay yellow"

# 3. Mode Pencarian Standar (Audio Only):
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
