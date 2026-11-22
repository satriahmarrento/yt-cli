# ytfzf configuration

# Search YouTube Music by default (custom scraper: config/ytfzf/scrapers/ytmusic).
# Use the yty / ytyr / ytya commands for regular YouTube search.
scrape="ytmusic"

# Always use standard YouTube URLs for video playback
yt_video_link_domain="https://www.youtube.com"

# Prefer direct fast audio streams (Opus 251 / AAC 140 / bestaudio)
# Prefer YouTube's HLS audio formats. Direct DASH URLs can intermittently
# return 403 on Android/Termux; HLS lets ffmpeg reconnect and avoids that path.
# 250 is a stable low-bitrate Opus fallback on direct DASH streams.
# 234 is the HLS AAC fallback with ffmpeg reconnect support.
audio_pref="250/234/233/251/249/140/bestaudio/best"
ytdl_pref="250/234/233/251/249/140/bestaudio/best"
