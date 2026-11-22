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

# 2. Copy binaries + preference engine
mkdir -p "$CONFIG_BASE/ytfzf/lib"
cp lib/ytm_preferences.py lib/ytm_radio.py lib/feedback.sh "$CONFIG_BASE/ytfzf/lib/"
chmod +x "$CONFIG_BASE/ytfzf/lib/ytm_preferences.py" "$CONFIG_BASE/ytfzf/lib/ytm_radio.py" "$CONFIG_BASE/ytfzf/lib/feedback.sh"
cp bin/yt "$BIN_DIR/yt"
cp bin/ytr "$BIN_DIR/ytr"
cp bin/ytra "$BIN_DIR/ytra"
cp bin/yty "$BIN_DIR/yty"
cp bin/ytyr "$BIN_DIR/ytyr"
cp bin/ytya "$BIN_DIR/ytya"
cp bin/ytra-smart "$BIN_DIR/ytra-smart"
cp bin/ytm-like bin/ytm-dislike bin/ytm-skip bin/ytm-ban bin/ytm-reset bin/ytm-show "$BIN_DIR/"
chmod +x "$BIN_DIR/yt" "$BIN_DIR/ytr" "$BIN_DIR/ytra" \
  "$BIN_DIR/yty" "$BIN_DIR/ytyr" "$BIN_DIR/ytya" \
  "$BIN_DIR/ytra-smart" "$BIN_DIR/ytm-like" "$BIN_DIR/ytm-dislike" "$BIN_DIR/ytm-skip" "$BIN_DIR/ytm-ban" "$BIN_DIR/ytm-reset" "$BIN_DIR/ytm-show"

# 3. Setup ytfzf configurations
mkdir -p "$CONFIG_BASE/ytfzf/url-handlers" "$CONFIG_BASE/ytfzf/scrapers"
cp config/ytfzf/conf.sh "$CONFIG_BASE/ytfzf/conf.sh"
cp config/ytfzf/url-handlers/radio "$CONFIG_BASE/ytfzf/url-handlers/radio"
cp config/ytfzf/scrapers/ytmusic "$CONFIG_BASE/ytfzf/scrapers/ytmusic"
chmod +x "$CONFIG_BASE/ytfzf/url-handlers/radio" "$CONFIG_BASE/ytfzf/scrapers/ytmusic"

# 4. Setup mpv configurations
mkdir -p "$CONFIG_BASE/mpv"
[ ! -f "$CONFIG_BASE/mpv/input.conf" ] && cp config/mpv/input.conf "$CONFIG_BASE/mpv/input.conf" || cp config/mpv/input.conf "$CONFIG_BASE/mpv/input.conf"
[ ! -f "$CONFIG_BASE/mpv/mpv.conf" ] && cp config/mpv/mpv.conf "$CONFIG_BASE/mpv/mpv.conf" || cp config/mpv/mpv.conf "$CONFIG_BASE/mpv/mpv.conf"

echo ""
echo "✅ YT CLI installed successfully!"
echo "🚀 Standard Search: yt -m \"nama lagu\""
echo "📻 Radio Autoplay:  ytr \"nama lagu\""
echo "⚡ Instant Autoplay: ytra \"nama lagu\""
