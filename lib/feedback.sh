#!/bin/sh
# Called by mpv key bindings (L/D/B) to record feedback for the current track.
exec python3 "$HOME/.config/ytfzf/lib/ytm_preferences.py" log "$1" --current
