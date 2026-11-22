#!/usr/bin/env python3
"""YouTube Music radio: prefetched streams, titles on screen, like/dislike keys.

Why the prefetch: mpv's ytdl hook runs yt-dlp per track (~5s on Termux) before
audio starts, which is the "always buffering" symptom. URLs are resolved ahead
of time and appended to a single mpv over IPC instead.

Keys (active while playing):
    L  like        D  dislike        B  ban
"""

import json
import os
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

CONFIG_DIR = os.path.expanduser("~/.config/ytfzf")
LIB_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_PATH = os.path.join(CONFIG_DIR, "radio.lock")
IPC_PATH = os.path.join(CONFIG_DIR, "radio.sock")
CACHE_PATH = os.path.join(CONFIG_DIR, "url_cache.json")
CURRENT_PATH = os.path.join(CONFIG_DIR, "current.json")
KEYS_PATH = os.path.join(CONFIG_DIR, "radio-keys.conf")
FEEDBACK = os.path.join(LIB_DIR, "feedback.sh")

CACHE_TTL = 900
CLIENT_VERSION = "1.20261117.06.00"
USER_AGENT = ("Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")
FORMATS = ["234", "233", "251", "250", "249", "140"]
PREFETCH_AHEAD = 3


# ------------------------------------------------------------------ YTM data

def fetch_queue(seed_id, limit=20):
    """Return [{id,title,artist,duration}] starting with the seed."""
    try:
        from urllib.request import Request, urlopen
    except Exception:
        return []

    try:
        payload = {
            "context": {"client": {"clientName": "WEB_REMIX",
                                   "clientVersion": CLIENT_VERSION,
                                   "hl": "en", "gl": "US"}},
            "videoId": seed_id,
            "playlistId": "RDAMVM" + seed_id,
        }
        req = Request("https://music.youtube.com/youtubei/v1/next",
                      data=json.dumps(payload).encode(),
                      headers={"Content-Type": "application/json",
                               "User-Agent": USER_AGENT})
        with urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception:
        return []

    rows = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return
        panel = node.get("playlistPanelVideoRenderer")
        if panel:
            vid = panel.get("videoId")
            title = "".join(r.get("text", "") for r in (panel.get("title", {}).get("runs") or []))
            artist = "".join(r.get("text", "") for r in
                             (panel.get("shortBylineText", {}).get("runs") or []))
            length = "".join(r.get("text", "") for r in
                             (panel.get("lengthText", {}).get("runs") or []))
            if vid:
                rows.append({"id": vid, "title": title, "artist": artist,
                             "duration": length})
        for value in node.values():
            walk(value)

    walk(data)
    seen, queue = set(), []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        queue.append(row)
        if len(queue) >= limit:
            break
    return queue


# -------------------------------------------------------------- media lookup

def _cache_load():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _cache_store(video_id, url):
    try:
        now = time.time()
        data = {k: v for k, v in _cache_load().items()
                if isinstance(v, dict) and now - v.get("ts", 0) < CACHE_TTL}
        data[video_id] = {"url": url, "ts": now}
        tmp = CACHE_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(tmp, CACHE_PATH)
    except Exception:
        pass


def resolve_url(video_id):
    """Direct media URL. HLS first (reliable on mobile), DASH as fallback."""
    cached = _cache_load().get(video_id)
    if cached and time.time() - cached.get("ts", 0) < CACHE_TTL:
        return cached.get("url")

    for fmt in FORMATS:
        args = [shutil.which("yt-dlp") or "yt-dlp", "-f", fmt, "-g",
                "--no-warnings", "--no-playlist",
                "https://www.youtube.com/watch?v=" + video_id]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=45)
        except Exception:
            continue
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("http"):
                _cache_store(video_id, line)
                return line
    return None


# --------------------------------------------------------------------- mpv

def build_keys_conf():
    """Merge the user's key bindings with our feedback keys."""
    lines = []
    user_conf = os.path.expanduser("~/.config/mpv/input.conf")
    if os.path.exists(user_conf):
        try:
            with open(user_conf, "r", encoding="utf-8") as handle:
                lines.append(handle.read())
        except Exception:
            pass
    if os.path.exists(FEEDBACK):
        quoted = shlex.quote(FEEDBACK)
        lines.append("\n# ytm radio feedback (y=like x=dislike b=ban)\n")
        lines.append(f"y run {quoted} like\n")
        lines.append(f"x run {quoted} dislike\n")
        lines.append(f"b run {quoted} ban\n")
    try:
        with open(KEYS_PATH, "w", encoding="utf-8") as handle:
            handle.write("".join(lines))
    except Exception:
        return None
    return KEYS_PATH


class Mpv:
    def __init__(self, keys_conf):
        env_ao = os.environ.get("YTR_AO") or ""
        if os.path.exists(IPC_PATH):
            try:
                os.unlink(IPC_PATH)
            except OSError:
                pass

        cmd = [shutil.which("mpv") or "mpv",
               "--no-video", "--idle=yes", "--no-resume-playback",
               "--volume=50", "--cache=yes", "--cache-secs=5",
               "--demuxer-readahead-secs=10", "--network-timeout=20",
               "--input-ipc-server=" + IPC_PATH, "--input-terminal=yes",
               "--term-playing-msg=▶ ${media-title}"]
        if keys_conf:
            cmd.append("--input-conf=" + keys_conf)
        if env_ao:
            cmd.insert(1, "--ao=" + env_ao)

        self.proc = subprocess.Popen(cmd)
        self.lock = threading.Lock()
        _write_lock(os.getpid(), self.proc.pid)

        for _ in range(50):
            if os.path.exists(IPC_PATH):
                break
            time.sleep(0.1)
        self.sock = self._connect()

    @staticmethod
    def _connect(timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect(IPC_PATH)
                return sock
            except OSError:
                time.sleep(0.2)
        return None

    def command(self, *args):
        return self._send(self.sock, *args)

    def _send(self, sock, *args):
        if sock is None:
            return False
        try:
            with self.lock:
                sock.sendall((json.dumps({"command": list(args)}) + "\n").encode())
            return True
        except OSError:
            return False

    def query(self, sock, prop):
        if sock is None:
            return None
        try:
            with self.lock:
                sock.sendall((json.dumps({"command": ["get_property", prop],
                                          "request_id": 1}) + "\n").encode())
                deadline = time.time() + 5
                buf = b""
                while time.time() < deadline:
                    chunk = sock.recv(65536)
                    if not chunk:
                        return None
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            msg = json.loads(line.decode())
                        except Exception:
                            continue
                        if msg.get("request_id") == 1:
                            return msg.get("data")
        except Exception:
            return None
        return None

    def play(self, url, label):
        return self.command("loadfile", url, "replace", -1,
                            {"force-media-title": label})

    def append(self, url, label):
        return self.command("loadfile", url, "append", -1,
                            {"force-media-title": label})

    def wait(self):
        return self.proc.wait()

    def terminate(self):
        if self.proc.poll() is not None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=3)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


# ------------------------------------------------------------- bookkeeping

def _write_lock(wrapper_pid, mpv_pid):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOCK_PATH, "w", encoding="utf-8") as handle:
            json.dump({"wrapper": wrapper_pid, "mpv": mpv_pid}, handle)
    except Exception:
        pass


def _kill_pid(pid):
    if not pid:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _kill_stale_mpv():
    marker = IPC_PATH.encode()
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == os.getpid():
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as handle:
                cmdline = handle.read()
        except Exception:
            continue
        if marker in cmdline and b"mpv" in cmdline:
            _kill_pid(pid)


def acquire_single_instance():
    old = {}
    try:
        with open(LOCK_PATH, "r", encoding="utf-8") as handle:
            raw = (handle.read() or "").strip()
        if raw:
            parsed = json.loads(raw)
            old = parsed if isinstance(parsed, dict) else {"wrapper": parsed}
    except Exception:
        old = {}
    for key in ("mpv", "wrapper"):
        pid = old.get(key)
        if pid and pid != os.getpid():
            _kill_pid(pid)
    _kill_stale_mpv()
    _write_lock(os.getpid(), None)


def release_single_instance():
    try:
        os.unlink(LOCK_PATH)
    except OSError:
        pass


def write_current(track):
    try:
        tmp = CURRENT_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(track, handle, ensure_ascii=False)
        os.replace(tmp, CURRENT_PATH)
    except Exception:
        pass


def log_play(track):
    try:
        subprocess.run([sys.executable, os.path.join(LIB_DIR, "ytm_preferences.py"),
                        "log", "play", track["id"], track.get("title", ""),
                        track.get("artist", "")],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10)
    except Exception:
        pass


def label_for(track):
    title = track.get("title") or track["id"]
    artist = track.get("artist") or ""
    return f"{title} — {artist}" if artist else title


# --------------------------------------------------------------------- main

def main():
    if len(sys.argv) < 2:
        print("usage: ytm_radio.py SEED_ID [LIMIT]", file=sys.stderr)
        return 2

    seed_id = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    player = None

    def _shutdown(signum, frame):
        raise SystemExit(0)

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            signal.signal(sig, _shutdown)
        except Exception:
            pass

    acquire_single_instance()
    try:
        queue = fetch_queue(seed_id, limit) or [{"id": seed_id, "title": "",
                                                 "artist": "", "duration": ""}]
        if queue[0]["id"] != seed_id:
            queue.insert(0, {"id": seed_id, "title": "", "artist": "", "duration": ""})

        first = queue[0]
        first_url = resolve_url(first["id"])
        if not first_url:
            print("Gagal resolve stream.", file=sys.stderr)
            return 1

        player = Mpv(build_keys_conf())
        if player.sock is None:
            print("Gagal terhubung ke mpv.", file=sys.stderr)
            return 1

        print("Tekan: y = like   x = dislike   b = ban   q = keluar", flush=True)
        player.play(first_url, label_for(first))
        entries = [first]

        # Prefetch ahead so a track never starts by waiting on yt-dlp.
        ready = []
        ready_lock = threading.Lock()

        def prefetch():
            for track in queue[1:]:
                if player.proc.poll() is not None:
                    break
                while True:
                    with ready_lock:
                        pending = len(ready)
                    if pending < PREFETCH_AHEAD or player.proc.poll() is not None:
                        break
                    time.sleep(0.2)
                url = resolve_url(track["id"])
                if url:
                    with ready_lock:
                        ready.append((track, url))

        def feeder():
            threading.Thread(target=prefetch, daemon=True).start()
            sent = 0
            while player.proc.poll() is None:
                item = None
                with ready_lock:
                    if ready:
                        item = ready.pop(0)
                if item is None:
                    time.sleep(0.2)
                    continue
                track, url = item
                if player.append(url, label_for(track)):
                    entries.append(track)
                    sent += 1
                if sent >= len(queue) - 1:
                    break
            # Everything queued: stay alive while mpv plays the rest.

        threading.Thread(target=feeder, daemon=True).start()

        def monitor():
            sock = Mpv._connect(timeout=20)
            last = None
            while player.proc.poll() is None:
                pos = player.query(sock, "playlist-pos")
                if isinstance(pos, int) and pos != last and 0 <= pos < len(entries):
                    last = pos
                    track = entries[pos]
                    write_current(track)
                    log_play(track)
                time.sleep(0.4)

        threading.Thread(target=monitor, daemon=True).start()

        code = player.wait()
        return code or 0
    except SystemExit:
        return 0
    finally:
        if player is not None:
            player.terminate()
        release_single_instance()


if __name__ == "__main__":
    sys.exit(main())
