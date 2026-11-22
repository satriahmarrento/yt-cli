# ytfzf configuration

# Search YouTube Music by default (custom scraper: config/ytfzf/scrapers/ytmusic).
# Use the yty / ytyr / ytya commands for regular YouTube search.
scrape="ytmusic"

# Always use standard YouTube URLs for video playback
yt_video_link_domain="https://www.youtube.com"

# Prefer direct fast audio streams (Opus 251 / AAC 140 / bestaudio)
audio_pref="251/140/bestaudio/best"
ytdl_pref="251/140/bestaudio/best"
