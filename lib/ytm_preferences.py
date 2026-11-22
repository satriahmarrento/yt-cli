#!/usr/bin/env python3
"""Local taste engine for the YouTube Music radio.

Tracks what you like, dislike, ban and play, then ranks YouTube Music search
results so `ytra` drifts towards artists you respond well to and away from the
ones you skip. All state lives in ~/.config/ytfzf/preferences.json.
"""

import json
import os
import random
import re
import sys
import time
from urllib.request import Request, urlopen

CONFIG_DIR = os.path.expanduser("~/.config/ytfzf")
PREF_PATH = os.path.join(CONFIG_DIR, "preferences.json")
CURRENT_PATH = os.path.join(CONFIG_DIR, "current.json")
CLIENT_VERSION = "1.20261117.06.00"
USER_AGENT = ("Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")

EMPTY = {"artists": {}, "tracks": {}, "banned": [], "seed_uses": {}}

# How strongly each action moves an artist's score.
WEIGHTS = {"like": 2.0, "dislike": -1.2, "skip": -0.6, "ban": -3.0, "play": 0.15}

# Compilations and clip-farms dominate YouTube search; they are bad seeds.
JUNK_RE = re.compile(
    r"\b(live|cover|karaoke|tutorial|remix|unofficial|mix|playlist|compilation|loop|reaction)\b"
    r"|\|\||\b1 hour\b|\bfull album\b",
    re.IGNORECASE,
)


def is_junk(title, artist):
    return bool(JUNK_RE.search(f"{title} {artist}"))


KIND_WORDS = {"song", "video", "album", "single", "ep", "playlist"}


def parse_artist(text):
    """YTM rows read 'Song • Coldplay | 2.4B plays', so the artist is not [0]."""
    parts = [part.strip() for part in (text or "").split(" • ")]
    if not parts:
        return ""
    if parts[0].lower() in KIND_WORDS:
        parts = parts[1:]
    return parts[0].split(" | ")[0].strip() if parts else ""


def load():
    try:
        with open(PREF_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception:
        return {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in EMPTY.items()}
    for key, default in EMPTY.items():
        data.setdefault(key, default.copy() if isinstance(default, (dict, list)) else default)
    return data


def save(data):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = PREF_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, PREF_PATH)


# ---------------------------------------------------------------- YTM search

def search(query, timeout=20):
    payload = {
        "context": {"client": {"clientName": "WEB_REMIX",
                               "clientVersion": CLIENT_VERSION,
                               "hl": "en", "gl": "US"}},
        "query": query,
    }
    req = Request("https://music.youtube.com/youtubei/v1/search",
                  data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json",
                           "User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)

    rows = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        item = node.get("musicResponsiveListItemRenderer")
        if item:
            vid = (item.get("playlistItemData") or {}).get("videoId")
            cols = []
            for col in item.get("flexColumns", []) or []:
                runs = (col.get("musicResponsiveListItemFlexColumnRenderer", {})
                        .get("text", {}).get("runs", []) or [])
                cols.append("".join(run.get("text", "") for run in runs))
            if vid:
                title = cols[0] if cols else "Unknown"
                artist = parse_artist(cols[1]) if len(cols) > 1 else ""
                if not is_junk(title, artist):
                    rows.append({"id": vid, "title": title, "artist": artist})
        card = node.get("musicCardShelfRenderer")
        if card:
            vid = ((card.get("onTap") or {}).get("watchEndpoint") or {}).get("videoId")
            if not vid:
                for button in card.get("buttons", []) or []:
                    vid = (button.get("buttonRenderer", {})
                           .get("navigationEndpoint", {})
                           .get("watchEndpoint", {}).get("videoId"))
                    if vid:
                        break
            if vid:
                title = "".join(r.get("text", "") for r in (card.get("title", {}).get("runs") or []))
                artist = parse_artist("".join(r.get("text", "") for r in
                                     (card.get("subtitle", {}).get("runs") or [])))
                if not is_junk(title, artist):
                    rows.insert(0, {"id": vid, "title": title, "artist": artist})
        for value in node.values():
            walk(value)

    walk(data)
    seen, unique = set(), []
    for row in rows:
        if row["id"] not in seen:
            seen.add(row["id"])
            unique.append(row)
    return unique[:20]


# ------------------------------------------------------------------ scoring

def score_track(row, data, now):
    track = data["tracks"].get(row["id"], {})
    artist_key = (row.get("artist") or "").strip().lower()
    affinity = float(data["artists"].get(artist_key, 0))

    value = 100.0
    value += affinity * 12.0
    value += float(track.get("likes", 0)) * 25.0
    value -= float(track.get("dislikes", 0)) * 22.0
    value -= float(track.get("skips", 0)) * 10.0
    value -= float(data["seed_uses"].get(row["id"], 0)) * 6.0

    last = track.get("last_play")
    if last:
        hours = (now - last) / 3600.0
        if hours < 1:
            value -= 60.0      # just heard it
        elif hours < 6:
            value -= 25.0 * (6 - hours) / 5.0

    if row["id"] in data["banned"]:
        value -= 1000.0

    # Exploration keeps the radio from collapsing into one artist.
    value += random.random() * 30.0
    return value


def liked_artists(data, limit=6):
    ranked = sorted(data["artists"].items(), key=lambda kv: kv[1], reverse=True)
    return [name for name, value in ranked if value > 0.5][:limit]


def pick_seed(query):
    data = load()
    now = time.time()

    candidates = []
    try:
        candidates.extend(search(query))
    except Exception:
        return None

    # Occasionally widen the pool with artists you already respond well to.
    # This is what makes the radio drift towards "more like what I like".
    liked = liked_artists(data)
    if liked and random.random() < 0.4:
        for artist in random.sample(liked, k=min(2, len(liked))):
            try:
                candidates.extend(search(artist)[:8])
            except Exception:
                continue

    if not candidates:
        return None

    seen, pool = set(), []
    for row in candidates:
        if row["id"] not in seen:
            seen.add(row["id"])
            pool.append(row)

    pool.sort(key=lambda row: score_track(row, data, now), reverse=True)
    shortlist = pool[:max(3, min(8, len(pool)))]
    weights = [max(1, len(shortlist) - index) for index in range(len(shortlist))]
    chosen = random.choices(shortlist, weights=weights, k=1)[0]

    data["seed_uses"][chosen["id"]] = data["seed_uses"].get(chosen["id"], 0) + 1
    track = data["tracks"].setdefault(chosen["id"], {})
    track.update({"title": chosen["title"], "artist": chosen["artist"]})
    save(data)
    return chosen["id"]


# ----------------------------------------------------------------- feedback

def _current_meta():
    try:
        with open(CURRENT_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def log_event(kind, video_id, title="", artist=""):
    kind = kind.lower()
    data = load()
    now = time.time()

    track = data["tracks"].setdefault(video_id, {})
    if title:
        track["title"] = title
    if artist:
        track["artist"] = artist

    if kind == "play":
        track["plays"] = track.get("plays", 0) + 1
        track["last_play"] = now
    elif kind == "like":
        track["likes"] = track.get("likes", 0) + 1
    elif kind in ("dislike", "skip"):
        track["dislikes" if kind == "dislike" else "skips"] = \
            track.get("dislikes" if kind == "dislike" else "skips", 0) + 1
    elif kind == "ban":
        if video_id not in data["banned"]:
            data["banned"].append(video_id)

    artist_key = (artist or track.get("artist") or "").strip().lower()
    if artist_key:
        delta = WEIGHTS.get(kind, 0)
        data["artists"][artist_key] = round(data["artists"].get(artist_key, 0) + delta, 3)

    save(data)

    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(os.path.join(CONFIG_DIR, "history.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": int(now), "kind": kind, "id": video_id,
                                     "title": track.get("title", ""),
                                     "artist": track.get("artist", "")},
                                    ensure_ascii=False) + "\n")
    except Exception:
        pass

    label = {"like": "❤ LIKE", "dislike": "👎 DISLIKE", "skip": "⏭ SKIP",
             "ban": "🚫 BAN", "play": "▶ PLAY"}.get(kind, kind.upper())
    name = track.get("title") or video_id
    who = track.get("artist") or ""
    print(f"{label}: {name}{(' — ' + who) if who else ''}", flush=True)


def main(argv):
    if len(argv) < 2:
        print("usage: ytm_preferences.py <seed|log|show|reset> ...", file=sys.stderr)
        return 2

    command = argv[1]

    if command == "seed":
        seed = pick_seed(argv[2] if len(argv) > 2 else "")
        if not seed:
            return 1
        print(seed)
        return 0

    if command == "log":
        if len(argv) < 3:
            return 2
        kind = argv[2]
        if "--current" in argv or len(argv) < 4:
            meta = _current_meta()
            log_event(kind, meta.get("id", ""), meta.get("title", ""), meta.get("artist", ""))
        else:
            log_event(kind, argv[3], argv[4] if len(argv) > 4 else "",
                      argv[5] if len(argv) > 5 else "")
        return 0

    if command == "show":
        data = load()
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    if command == "reset":
        save({k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in EMPTY.items()})
        return 0

    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
