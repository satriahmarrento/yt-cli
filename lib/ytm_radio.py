#!/usr/bin/env python3
"""Sequential YouTube Music radio with URL prefetch.

Why this exists
---------------
mpv's ytdl hook runs `yt-dlp` for every track. On Termux that costs ~4.8s per
track, paid *before* audio starts, which is the "always buffering" symptom.
Resolving the media URL ahead of time drops the per-track startup to ~1.4s.

Design
------
* One mpv process for the whole session (keyboard shortcuts keep working).
* mpv is driven over its IPC socket; upcoming tracks are appended with
  `loadfile <url> append` while the current track plays.
* A single-instance lock kills a stale radio so two songs never overlap.
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time

CONFIG_DIR = os.path.expanduser("~/.config/ytfzf")
HISTORY = os.path.join(CONFIG_DIR, "history.jsonl")
LOCK_PATH = os.path.join(CONFIG_DIR, "radio.lock")
IPC_PATH = os.path.join(CONFIG_DIR, "radio.sock")
CACHE_PATH = os.path.join(CONFIG_DIR, "url_cache.json")
CACHE_TTL = 900  # seconds; googlevideo URLs live for hours but 403s creep in

CLIENT_VERSION = "1.20261117.06.00"
USER_AGENT = ("Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36")

# HLS first (reliable on mobile networks), DASH as fallback.
FORMATS = ["234", "233", "251", "250", "249", "140"]
PREFETCH_AHEAD = 3


# ---------------------------------------------------------------- YTM queue

def fetch_queue(seed_id, limit=20):
    """Ask YouTube Music for the radio queue that belongs to this seed."""
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
        req = Request(
            "https://music.youtube.com/youtubei/v1/next",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        with urlopen(req, timeout=20) as resp:
            data = json.load(resp)
    except Exception:
        return []

    found = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            panel = node.get("playlistPanelVideoRenderer")
            if panel:
                vid = panel.get("videoId")
                runs = panel.get("title", {}).get("runs", []) or []
                title = "".join(r.get("text", "") for r in runs)
                if vid:
                    found.append((vid, title))
            for value in node.values():
                walk(value)

    walk(data)
    seen = {seed_id}
    queue = []
    for vid, title in found:
        if vid in seen:
            continue
        seen.add(vid)
        queue.append((vid, title))
        if len(queue) >= limit:
            break
    return queue


# ------------------------------------------------------------- media lookup

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
    """Return a playable direct URL, or None. HLS first, then DASH.

    Direct URLs stay valid for hours, so a short-lived cache removes both the
    ~5s extraction cost and the repeated YouTube calls that trigger 403s.
    """
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


# ------------------------------------------------------------------- mpv IPC

class Mpv:
    def __init__(self, first_url):
        env_ao = os.environ.get("YTR_AO") or ""
        self.proc = None
        self.sock = None
        cmd = [
            shutil.which("mpv") or "mpv",
            "--no-video",
            "--no-resume-playback",
            "--volume=50",
            "--cache=yes",
            "--cache-secs=5",
            "--demuxer-readahead-secs=10",
            "--network-timeout=20",
            "--input-ipc-server=" + IPC_PATH,
            "--input-terminal=yes",
            "--term-status-msg=",
            first_url,
        ]
        if env_ao:
            cmd.insert(1, "--ao=" + env_ao)
        if os.path.exists(IPC_PATH):
            try:
                os.unlink(IPC_PATH)
            except OSError:
                pass
        self.proc = subprocess.Popen(cmd)
        _write_lock(os.getpid(), self.proc.pid)

        for _ in range(50):  # wait up to ~5s for the socket
            if os.path.exists(IPC_PATH):
                break
            time.sleep(0.1)
        try:
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(IPC_PATH)
        except OSError:
            self.sock = None

    def command(self, *args):
        if not self.sock:
            return False
        try:
            self.sock.sendall((json.dumps({"command": list(args)}) + "\n").encode())
            return True
        except OSError:
            return False

    def append(self, url):
        return self.command("loadfile", url, "append")

    def wait(self):
        return self.proc.wait()

    def terminate(self):
        """Kill mpv so it never outlives the wrapper (the double-audio bug)."""
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


# -------------------------------------------------------------- bookkeeping

def log_event(kind, video_id, title=""):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(HISTORY, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": int(time.time()), "kind": kind,
                                     "id": video_id, "title": title},
                                    ensure_ascii=False) + "\n")
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
    """Kill any mpv still attached to this radio's IPC socket.

    Lock data can go stale (wrapper SIGKILLed, killed mid-start), and an
    orphaned mpv is exactly what makes two songs play at once.
    """
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
    """Stop a radio left running by an earlier command (the double-audio bug).

    The previous run may have died without cleaning up mpv, so both pids are
    tracked and terminated before the new session starts.
    """
    old = {}
    try:
        with open(LOCK_PATH, "r", encoding="utf-8") as handle:
            raw = (handle.read() or "").strip()
        if raw:
            parsed = json.loads(raw)
            # Older lock files stored a bare pid.
            old = parsed if isinstance(parsed, dict) else {"wrapper": parsed}
    except Exception:
        old = {}
    for key in ("mpv", "wrapper"):
        pid = old.get(key)
        if pid and pid != os.getpid():
            _kill_pid(pid)
    _kill_stale_mpv()
    _write_lock(os.getpid(), None)


def _write_lock(wrapper_pid, mpv_pid):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LOCK_PATH, "w", encoding="utf-8") as handle:
            json.dump({"wrapper": wrapper_pid, "mpv": mpv_pid}, handle)
    except Exception:
        pass


def release_single_instance():
    try:
        os.unlink(LOCK_PATH)
    except OSError:
        pass


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
        first_url = resolve_url(seed_id)
        if not first_url:
            print("Gagal resolve stream.", file=sys.stderr)
            return 1

        player = Mpv(first_url)
        log_event("played", seed_id)

        queue = fetch_queue(seed_id, limit)
        if not queue and os.environ.get("YTR_DEBUG"):
            print("queue kosong, main satu lagu saja", file=sys.stderr)

        # Resolve ahead in a worker so playback never waits on yt-dlp.
        def prefetch():
            pending = list(queue)
            while pending and player.proc.poll() is None:
                while len(_ready) >= PREFETCH_AHEAD and player.proc.poll() is None:
                    time.sleep(0.2)
                vid, title = pending.pop(0)
                url = resolve_url(vid)
                if url:
                    _ready.append((vid, title, url))

        _ready = []
        worker = threading.Thread(target=prefetch, daemon=True)

        def feeder():
            worker.start()
            appended = 0
            while player.proc.poll() is None:
                if _ready:
                    vid, title, url = _ready.pop(0)
                    if player.append(url):
                        appended += 1
                        log_event("played", vid, title)
                else:
                    time.sleep(0.3)
                if not worker.is_alive() and not _ready and appended >= len(queue):
                    break

        threading.Thread(target=feeder, daemon=True).start()
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
