# ytfzf configuration

# Search YouTube Music by default (custom scraper: config/ytfzf/scrapers/ytmusic).
# Use the yty / ytyr / ytya commands for regular YouTube search.
scrape="ytmusic"

# Always use standard YouTube URLs for video playback
yt_video_link_domain="https://www.youtube.com"

# Prefer direct fast audio streams (Opus 251 / AAC 140 / bestaudio)
# Prefer YouTube's HLS audio formats. Direct DASH URLs can intermittently
# return 403 on Android/Termux; HLS lets ffmpeg reconnect and avoids that path.
audio_pref="234/233/140/249/250/251/bestaudio/best"
ytdl_pref="234/233/140/249/250/251/bestaudio/best"
