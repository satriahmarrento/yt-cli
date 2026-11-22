# ytfzf configuration

# Search YouTube Music by default (custom scraper: config/ytfzf/scrapers/ytmusic).
# Use the yty / ytyr / ytya commands for regular YouTube search.
scrape="ytmusic"

# Always use standard YouTube URLs for video playback
yt_video_link_domain="https://www.youtube.com"

# Prefer direct fast audio streams (Opus 251 / AAC 140 / bestaudio)
# Prefer YouTube's HLS audio formats. Direct DASH URLs can intermittently
# return 403 on Android/Termux; HLS lets ffmpeg reconnect and avoids that path.
# 234/233 are HLS (m3u8) streams: signed differently and reconnect-safe.
# DASH direct URLs (250/251/140) intermittently return 403 on mobile networks.
audio_pref="234/233/250/251/249/140/bestaudio/best"
ytdl_pref="234/233/250/251/249/140/bestaudio/best"
