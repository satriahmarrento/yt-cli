#!/usr/bin/env bash
set -e

echo "🎵 Installing YT CLI & Radio Mode..."

# 1. Detect Termux vs Standard Linux/macOS
if [ -n "$PREFIX" ] && [ -d "$PREFIX" ]; then
    echo "🤖 Termux environment detected."
    pkg update -y
    pkg install -y fzf jq curl yt-dlp mpv
    BIN_DIR="$PREFIX/bin"
    CONFIG_BASE="$HOME/.config"
else
    BIN_DIR="$HOME/.local/bin"
    CONFIG_BASE="$HOME/.config"
    mkdir -p "$BIN_DIR"
fi

# 2. Copy binaries
cp bin/yt "$BIN_DIR/yt"
cp bin/ytr "$BIN_DIR/ytr"
cp bin/ytra "$BIN_DIR/ytra"
chmod +x "$BIN_DIR/yt" "$BIN_DIR/ytr" "$BIN_DIR/ytra"

# 3. Setup ytfzf configurations
mkdir -p "$CONFIG_BASE/ytfzf/url-handlers"
cp config/ytfzf/conf.sh "$CONFIG_BASE/ytfzf/conf.sh"
cp config/ytfzf/url-handlers/radio "$CONFIG_BASE/ytfzf/url-handlers/radio"
chmod +x "$CONFIG_BASE/ytfzf/url-handlers/radio"

# 4. Setup mpv configurations
mkdir -p "$CONFIG_BASE/mpv"
[ ! -f "$CONFIG_BASE/mpv/input.conf" ] && cp config/mpv/input.conf "$CONFIG_BASE/mpv/input.conf" || cp config/mpv/input.conf "$CONFIG_BASE/mpv/input.conf"
[ ! -f "$CONFIG_BASE/mpv/mpv.conf" ] && cp config/mpv/mpv.conf "$CONFIG_BASE/mpv/mpv.conf" || cp config/mpv/mpv.conf "$CONFIG_BASE/mpv/mpv.conf"

echo ""
echo "✅ YT CLI installed successfully!"
echo "🚀 Standard Search: yt -m \"nama lagu\""
echo "📻 Radio Autoplay:  ytr \"nama lagu\""
echo "⚡ Instant Autoplay: ytra \"nama lagu\""
