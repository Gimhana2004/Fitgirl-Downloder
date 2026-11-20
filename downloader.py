#!/usr/bin/env python3
"""
FitGirl Multi-Part Downloader v4.0 (FuckingFast & DataNodes Ultra)
Features:
- 1-by-1 Sequential Auto-Grab: Resolves links one at a time in the foreground so Cloudflare
  Turnstile never fails on background tabs! Auto-advances through the whole link list.
- Dual-Channel Bridge: Receives direct URLs via GM_xmlhttpRequest on localhost:18999
  AND auto-catches via GM_setClipboard.
- Smart URL Filter: Distinguishes filehoster webpages from real direct download links.
- Persistent Sessions: Auto-saves queue to downloads_state.json across PC restarts.
- Multi-Day Resume: Seamless HTTP Range resume from exact byte.
- "Refresh Expired Link": Update links for parts that expired after 24h without lost bytes.
- Right-click per-part controls: Start, Pause, Refresh Link, Restart, Delete.
"""

import os
import sys
import time
import math
import json
import queue
import re
import urllib.request
import urllib.error
import urllib.parse
import http.server
import ssl
import threading
import webbrowser
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

# Bypass SSL verify issues if any system certs are outdated
SSL_CTX = ssl._create_unverified_context()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads_state.json")


def format_size(bytes_val):
    if bytes_val <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(bytes_val, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_val / p, 2)
    return f"{s} {units[i]}"


def format_speed(bytes_per_sec):
    return f"{format_size(bytes_per_sec)}/s"


def format_time(seconds):
    if seconds <= 0 or math.isinf(seconds):
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def is_direct_download_url(url):
    """
    Returns True ONLY if URL is an actual downloadable file URL.
    Returns False if it's a filehoster webpage (like datanodes.to/... or fuckingfast.co/...).
    """
    u = url.strip().lower()
    if "datanodes.to/" in u:
        if "/d/" in u or "/download/" in u or "sig=" in u:
            return True
        return False
    if "fuckingfast.co/" in u:
        if "dl.fuckingfast.co" in u or "/download" in u or "/dl/" in u:
            return True
        return False
    return True


class DownloadItem:
    def __init__(self, item_id, url, destination_folder, filename=None, total_size=0, downloaded_size=0, status="Queued"):
        self.item_id = item_id
        self.url = url
        self.destination_folder = destination_folder
        self.filename = filename if filename else self._guess_filename(url)
        self.filepath = os.path.join(destination_folder, self.filename)
        self.status = status
        self.total_size = total_size
        self.downloaded_size = downloaded_size
        self.speed = 0
        self.eta = 0
        self.retries = 0
        self.max_retries = 5
        self.error_msg = ""
        self.stop_requested = False
        self.current_response = None

    def _guess_filename(self, url):
        parsed = urllib.parse.urlparse(url)
        if parsed.fragment:
            clean_frag = urllib.parse.unquote(parsed.fragment)
            if any(clean_frag.lower().endswith(ext) for ext in [".rar", ".zip", ".7z", ".bin", ".iso", ".exe", ".001", ".002", ".003", ".004", ".005", ".doi"]):
                return os.path.basename(clean_frag)
        clean_url = url.split("?")[0].split("#")[0]
        name = os.path.basename(clean_url)
        if not name or len(name) > 150 or "." not in name:
            name = f"part_{self.item_id}.rar"
        name = urllib.parse.unquote(name)
        return name

    def cancel(self):
        self.stop_requested = True
        self.speed = 0
        self.eta = 0
        if self.current_response:
            try:
                self.current_response.close()
            except Exception:
                pass

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "url": self.url,
            "destination_folder": self.destination_folder,
            "filename": self.filename,
            "filepath": self.filepath,
            "status": "Paused" if self.status in ("Downloading", "Queued", "Retrying") else self.status,
            "total_size": self.total_size,
            "downloaded_size": self.downloaded_size
        }


class DownloadManager:
    def __init__(self, max_concurrent=2):
        self.max_concurrent = max_concurrent
        self.items = []
        self.active_threads = {}
        self.lock = threading.Lock()
        self.is_running = True

    def add_url(self, url, dest_dir):
        with self.lock:
            for existing in self.items:
                if existing.url == url.strip():
                    return existing

            item_id = len(self.items) + 1
            item = DownloadItem(item_id, url.strip(), dest_dir)
            self.items.append(item)
            self.save_state()
            return item

    def get_item(self, item_id):
        with self.lock:
            for item in self.items:
                if item.item_id == item_id:
                    return item
        return None

    def start_single_item(self, item_id, on_update_callback):
        with self.lock:
            item = None
            for it in self.items:
                if it.item_id == item_id:
                    item = it
                    break
            if not item:
                return

            if item.item_id not in self.active_threads:
                item.stop_requested = False
                item.status = "Queued"
                t = threading.Thread(
                    target=self._download_worker,
                    args=(item, on_update_callback),
                    daemon=True
                )
                self.active_threads[item.item_id] = t
                t.start()
                if on_update_callback:
                    on_update_callback(item)

    def pause_single_item(self, item_id, on_update_callback):
        with self.lock:
            for it in self.items:
                if it.item_id == item_id:
                    it.status = "Paused"
                    it.cancel()
                    if on_update_callback:
                        on_update_callback(it)
                    break
        self.save_state()

    def update_item_url(self, item_id, new_url, on_update_callback):
        with self.lock:
            for it in self.items:
                if it.item_id == item_id:
                    it.url = new_url.strip()
                    it.status = "Queued"
                    it.retries = 0
                    it.error_msg = ""
                    it.stop_requested = False
                    if on_update_callback:
                        on_update_callback(it)
                    break
        self.save_state()
        self.start_single_item(item_id, on_update_callback)

    def remove_item(self, item_id, delete_disk_file=False):
        with self.lock:
            target_item = None
            for it in self.items:
                if it.item_id == item_id:
                    target_item = it
                    break

            if target_item:
                target_item.cancel()
                if target_item.item_id in self.active_threads:
                    del self.active_threads[target_item.item_id]

                if delete_disk_file and os.path.exists(target_item.filepath):
                    try:
                        os.remove(target_item.filepath)
                    except Exception:
                        pass

                self.items.remove(target_item)
                self.save_state()
                return True
        return False

    def restart_single_item(self, item_id, on_update_callback):
        with self.lock:
            target_item = None
            for it in self.items:
                if it.item_id == item_id:
                    target_item = it
                    break
            if target_item:
                target_item.cancel()
                if os.path.exists(target_item.filepath):
                    try:
                        os.remove(target_item.filepath)
                    except Exception:
                        pass
                target_item.downloaded_size = 0
                target_item.total_size = 0
                target_item.speed = 0
                target_item.eta = 0
                target_item.retries = 0
                target_item.stop_requested = False
                target_item.status = "Queued"
                if on_update_callback:
                    on_update_callback(target_item)

        self.save_state()
        self.start_single_item(item_id, on_update_callback)

    def resume_all(self, on_update_callback):
        self.is_running = True
        with self.lock:
            for item in self.items:
                if item.status == "Paused":
                    item.status = "Queued"
                    item.stop_requested = False
                    if on_update_callback:
                        on_update_callback(item)
        self.start_next_downloads(on_update_callback)

    def start_next_downloads(self, on_update_callback):
        if not self.is_running:
            return

        with self.lock:
            active_count = len(self.active_threads)
            if active_count >= self.max_concurrent:
                return

            for item in self.items:
                if item.status in ("Queued", "Retrying") and item.item_id not in self.active_threads:
                    item.stop_requested = False
                    t = threading.Thread(
                        target=self._download_worker,
                        args=(item, on_update_callback),
                        daemon=True
                    )
                    self.active_threads[item.item_id] = t
                    t.start()
                    active_count += 1
                    if active_count >= self.max_concurrent:
                        break

    def retry_failed(self, on_update_callback):
        self.is_running = True
        with self.lock:
            for item in self.items:
                if item.status.startswith("Failed") or "Not Found" in item.status or item.status == "Paused":
                    item.status = "Queued"
                    item.retries = 0
                    item.stop_requested = False
                    item.error_msg = ""
        self.start_next_downloads(on_update_callback)

    def pause_all(self, on_update_callback=None):
        self.is_running = False
        with self.lock:
            for item in self.items:
                if item.status not in ("Completed",):
                    item.status = "Paused"
                    item.cancel()
                    if on_update_callback:
                        on_update_callback(item)
        self.save_state()

    def clear_completed_or_invalid(self):
        with self.lock:
            kept = []
            for item in self.items:
                if item.status == "Completed":
                    continue
                if not is_direct_download_url(item.url):
                    item.cancel()
                    continue
                kept.append(item)
            self.items = kept
            self.save_state()

    def save_state(self):
        try:
            data = [item.to_dict() for item in self.items if is_direct_download_url(item.url)]
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print("Error saving state:", e)

    def load_state(self):
        if not os.path.exists(STATE_FILE):
            return

        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            for d in data:
                url = d.get("url", "")
                if not is_direct_download_url(url):
                    continue

                actual_bytes = 0
                fpath = d.get("filepath", "")
                if os.path.exists(fpath):
                    actual_bytes = os.path.getsize(fpath)

                total_sz = d.get("total_size", 0)
                status = d.get("status", "Paused")
                if total_sz > 0 and actual_bytes >= total_sz:
                    status = "Completed"
                elif status == "Downloading":
                    status = "Paused"

                item = DownloadItem(
                    item_id=d["item_id"],
                    url=url,
                    destination_folder=d.get("destination_folder", ""),
                    filename=d.get("filename"),
                    total_size=total_sz,
                    downloaded_size=actual_bytes,
                    status=status
                )
                self.items.append(item)
        except Exception as e:
            print("Error loading state:", e)

    def _download_worker(self, item, on_update):
        item.status = "Downloading"
        item.stop_requested = False
        chunk_size = 1024 * 64

        while item.retries <= item.max_retries and not item.stop_requested:
            try:
                existing_bytes = 0
                if os.path.exists(item.filepath):
                    existing_bytes = os.path.getsize(item.filepath)

                req = urllib.request.Request(item.url)
                req.add_header("User-Agent", DEFAULT_USER_AGENT)
                if "fuckingfast.co" in item.url:
                    req.add_header("Referer", "https://fuckingfast.co/")
                else:
                    req.add_header("Referer", item.url)

                if existing_bytes > 0:
                    req.add_header("Range", f"bytes={existing_bytes}-")

                with urllib.request.urlopen(req, context=SSL_CTX, timeout=25) as response:
                    item.current_response = response

                    content_type = response.headers.get("Content-Type", "").lower()
                    if "text/html" in content_type and not item.url.endswith(".html"):
                        first_chunk = response.read(2048).decode("utf-8", errors="ignore").lower()
                        if any(phrase in first_chunk for phrase in ["not found", "deleted", "removed", "does not exist", "404"]):
                            item.status = "❌ File Not Found (Deleted)"
                            item.error_msg = "Server reported: File Not Found or Deleted."
                        else:
                            item.status = "Failed (Webpage URL, not direct file)"
                            item.error_msg = "Received HTML page. This is a webpage link, not a direct file link."
                        item.speed = 0
                        item.eta = 0
                        if on_update:
                            on_update(item)
                        break

                    disp = response.headers.get("Content-Disposition")
                    if disp:
                        m = re.search(r'filename\*?=(?:UTF-8\'\')?\"?([^\";]+)\"?', disp)
                        if m:
                            real_fname = m.group(1).strip("\"' ")
                            if real_fname:
                                item.filename = real_fname
                                item.filepath = os.path.join(item.destination_folder, real_fname)

                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        if response.status == 206:
                            item.total_size = existing_bytes + int(content_length)
                        else:
                            item.total_size = int(content_length)
                            existing_bytes = 0
                    else:
                        item.total_size = existing_bytes

                    mode = "ab" if existing_bytes > 0 else "wb"
                    item.downloaded_size = existing_bytes

                    if item.total_size > 0 and item.downloaded_size >= item.total_size:
                        item.status = "Completed"
                        break

                    start_time = time.time()
                    bytes_since_check = 0
                    last_check_time = start_time
                    last_save_time = start_time

                    with open(item.filepath, mode) as f:
                        while not item.stop_requested:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break

                            f.write(chunk)
                            item.downloaded_size += len(chunk)
                            bytes_since_check += len(chunk)

                            now = time.time()
                            elapsed = now - last_check_time
                            if elapsed >= 0.5:
                                item.speed = bytes_since_check / elapsed
                                bytes_since_check = 0
                                last_check_time = now
                                if item.speed > 0 and item.total_size > item.downloaded_size:
                                    item.eta = (item.total_size - item.downloaded_size) / item.speed
                                else:
                                    item.eta = 0
                                if on_update:
                                    on_update(item)

                            if now - last_save_time >= 10:
                                last_save_time = now
                                self.save_state()

                if item.stop_requested:
                    item.status = "Paused"
                    item.speed = 0
                    item.eta = 0
                    break

                item.status = "Completed"
                item.speed = 0
                item.eta = 0
                break

            except urllib.error.HTTPError as e:
                item.current_response = None
                if e.code == 404:
                    item.status = "❌ File Not Found (Deleted)"
                    item.error_msg = f"HTTP 404: File not found or removed on server."
                    item.speed = 0
                    item.eta = 0
                    break
                elif e.code in (401, 403, 410):
                    item.status = "Failed (Link Expired - Right Click to Refresh)"
                    item.error_msg = f"HTTP {e.code}: Direct link expired. Right-click and choose 'Refresh / Update Link'."
                    item.speed = 0
                    item.eta = 0
                    break
                else:
                    item.retries += 1
                    item.error_msg = str(e)

            except Exception as e:
                item.current_response = None
                if item.stop_requested:
                    item.status = "Paused"
                    item.speed = 0
                    item.eta = 0
                    break

                item.retries += 1
                item.error_msg = str(e)
                if item.retries <= item.max_retries and not item.stop_requested:
                    item.status = f"Retrying ({item.retries}/{item.max_retries})"
                    if on_update:
                        on_update(item)
                    for _ in range(30):
                        if item.stop_requested:
                            item.status = "Paused"
                            item.speed = 0
                            item.eta = 0
                            break
                        time.sleep(0.1)
                else:
                    item.status = "Failed"
                    item.speed = 0
                    item.eta = 0
                    break

        item.current_response = None
        with self.lock:
            if item.item_id in self.active_threads:
                del self.active_threads[item.item_id]

        self.save_state()

        if on_update:
            on_update(item)

        if self.is_running and not item.stop_requested:
            self.start_next_downloads(on_update)


class LocalBridgeHandler(http.server.BaseHTTPRequestHandler):
    """Local HTTP bridge for Safari/Chrome userscripts to send direct links straight to this tool."""
    gui_instance = None

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            url = self.rfile.read(length).decode('utf-8').strip()
            if url and LocalBridgeHandler.gui_instance:
                LocalBridgeHandler.gui_instance.handle_bridge_url(url)

            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        except Exception:
            pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()

    def log_message(self, format, *args):
        pass


class FitGirlDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FitGirl Multi-Part Downloader v4.0 (FuckingFast & DataNodes Ultra) (1-by-1 Cloudflare Safe Auto-Grab)")
        self.root.geometry("940x670")
        self.root.minsize(860, 520)

        # Apply Modern Dark Theme colors
        self.bg_dark = "#1e1e2e"
        self.bg_card = "#252538"
        self.bg_entry = "#181825"
        self.fg_text = "#cdd6f4"
        self.fg_sub = "#a6adc8"
        self.accent_blue = "#89b4fa"
        self.accent_green = "#a6e3a1"
        self.accent_red = "#f38ba8"
        self.accent_yellow = "#f9e2af"
        self.accent_purple = "#cba6f7"

        self.root.configure(bg=self.bg_dark)

        # State
        default_dir = os.path.join(os.path.expanduser("~"), "Downloads", "FitGirl_Games")
        os.makedirs(default_dir, exist_ok=True)
        self.dest_dir_var = tk.StringVar(value=default_dir)
        self.concurrent_var = tk.IntVar(value=2)
        self.manager = DownloadManager(max_concurrent=self.concurrent_var.get())

        self.clipboard_watch_active = tk.BooleanVar(value=True)
        self.last_clipboard_val = ""
        self.selected_item_id = None
        self.auto_grab_active = False

        self._build_ui()
        self._build_context_menu()
        self._load_saved_session()
        self._start_clipboard_watcher()
        self._start_bridge_server()

        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _start_bridge_server(self):
        LocalBridgeHandler.gui_instance = self
        try:
            self.bridge_server = http.server.HTTPServer(('127.0.0.1', 18999), LocalBridgeHandler)
            t = threading.Thread(target=self.bridge_server.serve_forever, daemon=True)
            t.start()
        except Exception as e:
            print("Local bridge listener status:", e)

    def handle_bridge_url(self, payload):
        self.root.after(0, self._process_bridge_payload, payload)

    def _process_bridge_payload(self, payload):
        if payload.startswith("DEAD_LINK:"):
            data = payload[len("DEAD_LINK:"):].strip()
            parts = data.split(":::")
            dead_url = parts[0].strip()
            dead_filename = parts[1].strip() if len(parts) > 1 else os.path.basename(dead_url)

            dest_dir = self.dest_dir_var.get()
            item = self.manager.add_url(dead_url, dest_dir)
            if dead_filename and dead_filename != "unknown_part.rar":
                item.filename = dead_filename
                item.filepath = os.path.join(dest_dir, dead_filename)
            item.status = "❌ File Not Found (Deleted)"
            item.error_msg = "The file is missing or deleted on the file hoster."

            item_id_str = str(item.item_id)
            if not self.tree.exists(item_id_str):
                self.tree.insert(
                    "",
                    tk.END,
                    iid=item_id_str,
                    values=(
                        item.item_id,
                        item.filename,
                        "-",
                        "0%",
                        "-",
                        "--:--",
                        item.status
                    ),
                    tags=("file_not_found",)
                )
            else:
                self._sync_tree_item(item)

            self.status_bar.config(text=f"❌ Dead Link: {item.filename[:45]}")
            if getattr(self, "auto_grab_active", False):
                self.root.after(2500, self._open_next_auto_link)
            return

        self._add_single_url_from_bridge(payload)

    def _add_single_url_from_bridge(self, url):
        # ONLY accept real direct download URLs into the queue!
        if (url.startswith("http://") or url.startswith("https://")) and is_direct_download_url(url):
            dest_dir = self.dest_dir_var.get()
            item = self.manager.add_url(url, dest_dir)
            item_id_str = str(item.item_id)
            if not self.tree.exists(item_id_str):
                self.tree.insert(
                    "",
                    tk.END,
                    iid=item_id_str,
                    values=(
                        item.item_id,
                        item.filename,
                        "0 B",
                        "0%",
                        "-",
                        "--:--",
                        item.status
                    ),
                    tags=("queued",)
                )
                self.status_bar.config(
                    text=f"🚀 Direct file received: {item.filename[:45]}"
                )
                self.manager.start_next_downloads(self._on_item_update)

            # If 1-by-1 auto-grab is running, automatically trigger the next link after 3s
            if getattr(self, "auto_grab_active", False):
                self.root.after(3000, self._open_next_auto_link)

    def _load_saved_session(self):
        self.manager.load_state()
        for item in self.manager.items:
            item_id_str = str(item.item_id)
            prog_pct = 0
            if item.total_size > 0:
                prog_pct = int((item.downloaded_size / item.total_size) * 100)

            size_str = (
                f"{format_size(item.downloaded_size)} / {format_size(item.total_size)}"
                if item.total_size > 0
                else format_size(item.downloaded_size)
            )

            tag = "queued"
            if "File Not Found" in item.status or "404" in item.status:
                tag = "file_not_found"
            elif "Failed" in item.status:
                tag = "failed"
            elif item.status == "Completed":
                tag = "completed"
            elif item.status == "Paused":
                tag = "paused"

            self.tree.insert(
                "",
                tk.END,
                iid=item_id_str,
                values=(
                    item.item_id,
                    item.filename,
                    size_str,
                    f"{prog_pct}%",
                    "-",
                    "--:--",
                    item.status
                ),
                tags=(tag,)
            )

        if self.manager.items:
            self.status_bar.config(
                text=f"Restored {len(self.manager.items)} parts from previous session. Hit 'Start / Resume All' to continue!"
            )

    def _on_window_close(self):
        self.manager.pause_all()
        self.manager.save_state()
        self.root.destroy()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.bg_dark, pady=10, padx=15)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="⚡ FitGirl Multi-Part Downloader",
            font=("Helvetica", 16, "bold"),
            bg=self.bg_dark,
            fg=self.accent_blue
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            header,
            text="1-by-1 Cloudflare Safe Auto-Grab | Multi-Day Resume",
            font=("Helvetica", 9),
            bg=self.bg_dark,
            fg=self.accent_green
        )
        sub_lbl.pack(side=tk.LEFT, padx=12, pady=3)

        open_folder_btn = tk.Button(
            header,
            text="📂 Open Download Folder",
            font=("Helvetica", 9, "bold"),
            bg="#313244",
            fg=self.accent_blue,
            relief=tk.FLAT,
            command=self._open_dest_folder
        )
        open_folder_btn.pack(side=tk.RIGHT)

        folder_frame = tk.Frame(self.root, bg=self.bg_card, padx=12, pady=10)
        folder_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        tk.Label(
            folder_frame,
            text="Save Folder:",
            font=("Helvetica", 10, "bold"),
            bg=self.bg_card,
            fg=self.fg_text
        ).pack(side=tk.LEFT)

        folder_entry = tk.Entry(
            folder_frame,
            textvariable=self.dest_dir_var,
            font=("Helvetica", 10),
            bg=self.bg_entry,
            fg=self.fg_text,
            insertbackground=self.fg_text,
            relief=tk.FLAT
        )
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        browse_btn = tk.Button(
            folder_frame,
            text="📁 Browse",
            font=("Helvetica", 9, "bold"),
            bg=self.bg_entry,
            fg=self.accent_blue,
            relief=tk.FLAT,
            command=self._browse_folder
        )
        browse_btn.pack(side=tk.LEFT)

        input_frame = tk.Frame(self.root, bg=self.bg_card, padx=12, pady=10)
        input_frame.pack(fill=tk.X, padx=15, pady=(0, 10))

        lbl_input = tk.Label(
            input_frame,
            text="FitGirl Page Links (Paste FuckingFast or DataNodes links here -> click 'Start 1-by-1 Auto-Grab'):",
            font=("Helvetica", 10, "bold"),
            bg=self.bg_card,
            fg=self.fg_text
        )
        lbl_input.pack(anchor=tk.W)

        self.txt_links = tk.Text(
            input_frame,
            height=3,
            font=("Courier", 10),
            bg=self.bg_entry,
            fg=self.fg_text,
            insertbackground=self.fg_text,
            relief=tk.FLAT
        )
        self.txt_links.pack(fill=tk.X, pady=6)

        ctrl_frame = tk.Frame(input_frame, bg=self.bg_card)
        ctrl_frame.pack(fill=tk.X)

        self.auto_grab_btn = tk.Button(
            ctrl_frame,
            text="🌐 Start 1-by-1 Auto-Grab",
            font=("Helvetica", 10, "bold"),
            bg=self.accent_purple,
            fg="#11111b",
            padx=12,
            pady=5,
            relief=tk.FLAT,
            command=self._toggle_auto_grab
        )
        self.auto_grab_btn.pack(side=tk.LEFT)

        start_btn = tk.Button(
            ctrl_frame,
            text="▶ Start / Resume All",
            font=("Helvetica", 10, "bold"),
            bg="#89b4fa",
            fg="#11111b",
            padx=12,
            pady=5,
            relief=tk.FLAT,
            command=self._start_downloading
        )
        start_btn.pack(side=tk.LEFT, padx=8)

        pause_btn = tk.Button(
            ctrl_frame,
            text="⏸ Pause All",
            font=("Helvetica", 9, "bold"),
            bg="#f38ba8",
            fg="#11111b",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            command=self._pause_all
        )
        pause_btn.pack(side=tk.LEFT, padx=4)

        retry_btn = tk.Button(
            ctrl_frame,
            text="🔄 Retry Failed",
            font=("Helvetica", 9),
            bg="#313244",
            fg=self.accent_yellow,
            padx=8,
            pady=5,
            relief=tk.FLAT,
            command=self._retry_failed
        )
        retry_btn.pack(side=tk.LEFT, padx=4)

        clean_btn = tk.Button(
            ctrl_frame,
            text="🧹 Clear Finished / Invalid",
            font=("Helvetica", 9),
            bg="#313244",
            fg=self.fg_sub,
            padx=8,
            pady=5,
            relief=tk.FLAT,
            command=self._clean_queue
        )
        clean_btn.pack(side=tk.LEFT, padx=4)

        tk.Label(
            ctrl_frame,
            text="⚡ Simultaneous Downloads (Default 2):",
            font=("Helvetica", 9, "bold"),
            bg=self.bg_card,
            fg=self.accent_blue
        ).pack(side=tk.RIGHT, padx=(10, 4))

        spin_concurrent = tk.Spinbox(
            ctrl_frame,
            from_=1,
            to=5,
            width=3,
            textvariable=self.concurrent_var,
            bg=self.bg_entry,
            fg=self.fg_text,
            relief=tk.FLAT,
            command=self._update_concurrency
        )
        spin_concurrent.pack(side=tk.RIGHT)

        clip_check = tk.Checkbutton(
            ctrl_frame,
            text="📋 Auto-Catch Clipboard",
            variable=self.clipboard_watch_active,
            bg=self.bg_card,
            fg=self.fg_text,
            selectcolor=self.bg_entry,
            activebackground=self.bg_card,
            activeforeground=self.fg_text,
            font=("Helvetica", 9)
        )
        clip_check.pack(side=tk.RIGHT, padx=10)

        table_frame = tk.Frame(self.root, bg=self.bg_card, padx=12, pady=10)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        tk.Label(
            table_frame,
            text="Direct Downloads Queue (Only real downloadable parts appear here):",
            font=("Helvetica", 10, "bold"),
            bg=self.bg_card,
            fg=self.fg_text
        ).pack(anchor=tk.W, pady=(0, 5))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Custom.Treeview",
            background=self.bg_entry,
            foreground=self.fg_text,
            fieldbackground=self.bg_entry,
            rowheight=26,
            font=("Helvetica", 9)
        )
        style.configure(
            "Custom.Treeview.Heading",
            background="#313244",
            foreground=self.accent_blue,
            font=("Helvetica", 9, "bold")
        )
        style.map("Custom.Treeview", background=[("selected", "#45475a")])

        columns = ("id", "filename", "size", "progress", "speed", "eta", "status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Custom.Treeview"
        )

        self.tree.heading("id", text="#")
        self.tree.heading("filename", text="File Name")
        self.tree.heading("size", text="Size")
        self.tree.heading("progress", text="Progress")
        self.tree.heading("speed", text="Speed")
        self.tree.heading("eta", text="ETA")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=35, anchor=tk.CENTER)
        self.tree.column("filename", width=280, anchor=tk.W)
        self.tree.column("size", width=120, anchor=tk.CENTER)
        self.tree.column("progress", width=80, anchor=tk.CENTER)
        self.tree.column("speed", width=90, anchor=tk.CENTER)
        self.tree.column("eta", width=70, anchor=tk.CENTER)
        self.tree.column("status", width=160, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.tag_configure("file_not_found", foreground="#f38ba8")
        self.tree.tag_configure("failed", foreground="#f38ba8")
        self.tree.tag_configure("completed", foreground="#a6e3a1")
        self.tree.tag_configure("downloading", foreground="#89b4fa")
        self.tree.tag_configure("paused", foreground="#f9e2af")
        self.tree.tag_configure("queued", foreground="#cdd6f4")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Button-2>", self._show_context_menu)
        if sys.platform == "darwin":
            self.tree.bind("<Control-Button-1>", self._show_context_menu)

        self.status_bar = tk.Label(
            self.root,
            text="Ready. Paste your DataNodes links above and click 'Start 1-by-1 Auto-Grab' to resolve cleanly.",
            bg="#11111b",
            fg=self.fg_sub,
            font=("Helvetica", 9),
            anchor=tk.W,
            padx=10,
            pady=4
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_context_menu(self):
        self.menu = tk.Menu(self.root, tearoff=0, bg="#2b2d42", fg="#edf2f4", activebackground="#45475a", activeforeground="#89b4fa")
        self.menu.add_command(label="▶ Start / Resume This Part", command=self._action_start_single)
        self.menu.add_command(label="⏸ Pause This Part", command=self._action_pause_single)
        self.menu.add_command(label="🔄 Refresh / Update Expired Link", command=self._action_refresh_link)
        self.menu.add_command(label="🔁 Restart from 0%", command=self._action_restart_single)
        self.menu.add_separator()
        self.menu.add_command(label="📋 Copy Link", command=self._action_copy_link)
        self.menu.add_command(label="📂 Open File in Folder", command=self._action_show_in_folder)
        self.menu.add_separator()
        self.menu.add_command(label="🗑️ Remove from Queue", command=self._action_remove_from_queue)
        self.menu.add_command(label="❌ Delete File & Remove", command=self._action_delete_file_and_remove)

    def _show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.selected_item_id = int(row_id)
            self.menu.post(event.x_root, event.y_root)

    def _action_start_single(self):
        if self.selected_item_id:
            self.manager.start_single_item(self.selected_item_id, self._on_item_update)
            self.status_bar.config(text=f"Started download for part #{self.selected_item_id}")

    def _action_pause_single(self):
        if self.selected_item_id:
            self.manager.pause_single_item(self.selected_item_id, self._on_item_update)
            self.status_bar.config(text=f"Paused part #{self.selected_item_id}")

    def _action_refresh_link(self):
        if self.selected_item_id:
            item = self.manager.get_item(self.selected_item_id)
            if item:
                new_url = simpledialog.askstring(
                    "Refresh Expired Link",
                    f"Paste the new fresh direct link for:\n{item.filename}\n\n(It will resume from {format_size(item.downloaded_size)} without restarting from 0%!)",
                    parent=self.root
                )
                if new_url and new_url.strip().startswith("http"):
                    self.manager.update_item_url(self.selected_item_id, new_url.strip(), self._on_item_update)
                    self.status_bar.config(text=f"Updated link for {item.filename}. Resuming...")

    def _action_restart_single(self):
        if self.selected_item_id:
            if messagebox.askyesno("Restart Download", "Are you sure you want to delete downloaded progress and restart this part from 0%?"):
                self.manager.restart_single_item(self.selected_item_id, self._on_item_update)
                self.status_bar.config(text=f"Restarted part #{self.selected_item_id} from 0%")

    def _action_copy_link(self):
        if self.selected_item_id:
            item = self.manager.get_item(self.selected_item_id)
            if item:
                self.root.clipboard_clear()
                self.root.clipboard_append(item.url)
                self.status_bar.config(text=f"Copied link for part #{self.selected_item_id} to clipboard")

    def _action_show_in_folder(self):
        if self.selected_item_id:
            item = self.manager.get_item(self.selected_item_id)
            if item and os.path.exists(item.filepath):
                if sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", item.filepath])
                elif sys.platform == "win32":
                    subprocess.Popen(f'explorer /select,"{os.path.normpath(item.filepath)}"')
                else:
                    self._open_dest_folder()
            else:
                self._open_dest_folder()

    def _action_remove_from_queue(self):
        if self.selected_item_id:
            iid_str = str(self.selected_item_id)
            self.manager.remove_item(self.selected_item_id, delete_disk_file=False)
            if self.tree.exists(iid_str):
                self.tree.delete(iid_str)
            self.status_bar.config(text=f"Removed part #{self.selected_item_id} from queue.")
            self.selected_item_id = None

    def _action_delete_file_and_remove(self):
        if self.selected_item_id:
            item = self.manager.get_item(self.selected_item_id)
            fname = item.filename if item else f"Part #{self.selected_item_id}"
            if messagebox.askyesno("Delete File", f"Are you sure you want to permanently delete:\n\n{fname}\n\nand remove it from the queue?"):
                iid_str = str(self.selected_item_id)
                self.manager.remove_item(self.selected_item_id, delete_disk_file=True)
                if self.tree.exists(iid_str):
                    self.tree.delete(iid_str)
                self.status_bar.config(text=f"Deleted file and removed part #{self.selected_item_id}.")
                self.selected_item_id = None

    def _clean_queue(self):
        self.manager.clear_completed_or_invalid()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._load_saved_session()
        self.status_bar.config(text="Cleaned completed and invalid webpage links from queue.")

    def _toggle_auto_grab(self):
        if getattr(self, "auto_grab_active", False):
            self.auto_grab_active = False
            self.auto_grab_btn.config(text="🌐 Start 1-by-1 Auto-Grab", bg=self.accent_purple)
            self.status_bar.config(text="Auto-grab stopped.")
            return

        raw_text = self.txt_links.get("1.0", tk.END).strip()
        urls = [line.strip() for line in raw_text.splitlines() if line.strip().startswith("http")]
        if not urls:
            messagebox.showinfo(
                "No Links",
                "Please paste your FitGirl DataNodes links into the text box first!"
            )
            return

        self.auto_grab_active = True
        self.auto_grab_btn.config(text="⏹ Stop Auto-Grab", bg=self.accent_red)
        self._open_next_auto_link()

    def _open_next_auto_link(self):
        if not getattr(self, "auto_grab_active", False):
            return

        raw_text = self.txt_links.get("1.0", tk.END).strip()
        urls = [line.strip() for line in raw_text.splitlines() if line.strip().startswith("http")]
        if not urls:
            self.auto_grab_active = False
            self.auto_grab_btn.config(text="🌐 Start 1-by-1 Auto-Grab", bg=self.accent_purple)
            self.status_bar.config(text="🎉 All links successfully resolved and queued for download!")
            return

        next_url = urls[0]
        remaining = urls[1:]

        self.txt_links.delete("1.0", tk.END)
        if remaining:
            self.txt_links.insert(tk.END, "\n".join(remaining))

        self.status_bar.config(
            text=f"🌐 Resolving {os.path.basename(next_url)[:35]}... (Active tab ensures Cloudflare passes cleanly)"
        )
        webbrowser.open(next_url)

    def _open_dest_folder(self):
        folder = self.dest_dir_var.get()
        if os.path.exists(folder):
            if sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            elif sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])

    def _browse_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.dest_dir_var.get())
        if chosen:
            self.dest_dir_var.set(chosen)

    def _update_concurrency(self):
        try:
            val = self.concurrent_var.get()
            self.manager.max_concurrent = max(1, min(val, 5))
        except Exception:
            pass

    def _start_downloading(self):
        if not self.manager.items:
            messagebox.showinfo("Queue Empty", "No direct downloads in queue. Paste links above and click 'Start 1-by-1 Auto-Grab'!")
            return

        self.status_bar.config(text=f"Downloading in progress (Max {self.manager.max_concurrent} simultaneous downloads)...")
        self.manager.resume_all(self._on_item_update)

    def _retry_failed(self):
        self.status_bar.config(text="Retrying all failed files...")
        self.manager.retry_failed(self._on_item_update)

    def _pause_all(self):
        self.status_bar.config(text="Downloads paused.")
        self.manager.pause_all(self._on_item_update)

    def _on_item_update(self, item):
        self.root.after(0, self._sync_tree_item, item)

    def _sync_tree_item(self, item):
        item_id_str = str(item.item_id)
        if not self.tree.exists(item_id_str):
            return

        prog_pct = 0
        if item.total_size > 0:
            prog_pct = int((item.downloaded_size / item.total_size) * 100)

        size_str = (
            f"{format_size(item.downloaded_size)} / {format_size(item.total_size)}"
            if item.total_size > 0
            else format_size(item.downloaded_size)
        )
        speed_str = format_speed(item.speed) if item.speed > 0 else "-"
        eta_str = format_time(item.eta) if item.eta > 0 else "--:--"

        tag = "queued"
        if "File Not Found" in item.status or "404" in item.status:
            tag = "file_not_found"
        elif "Failed" in item.status:
            tag = "failed"
        elif item.status == "Completed":
            tag = "completed"
        elif item.status == "Downloading":
            tag = "downloading"
        elif item.status == "Paused":
            tag = "paused"

        self.tree.item(
            item_id_str,
            values=(
                item.item_id,
                item.filename,
                size_str,
                f"{prog_pct}%",
                speed_str,
                eta_str,
                item.status
            ),
            tags=(tag,)
        )

    def _start_clipboard_watcher(self):
        def watcher():
            try:
                if self.clipboard_watch_active.get():
                    clip = self.root.clipboard_get().strip()
                    if clip and clip != self.last_clipboard_val:
                        self.last_clipboard_val = clip
                        if clip.startswith("http://") or clip.startswith("https://"):
                            if is_direct_download_url(clip):
                                if any(x in clip.lower() for x in [".rar", "/d/", "download", "fitgirl", "proxy", "tunnel"]):
                                    dest_dir = self.dest_dir_var.get()
                                    item = self.manager.add_url(clip, dest_dir)
                                    item_id_str = str(item.item_id)
                                    if not self.tree.exists(item_id_str):
                                        self.tree.insert(
                                            "",
                                            tk.END,
                                            iid=item_id_str,
                                            values=(
                                                item.item_id,
                                                item.filename,
                                                "0 B",
                                                "0%",
                                                "-",
                                                "--:--",
                                                item.status
                                            )
                                        )
                                        self.status_bar.config(
                                            text=f"📋 Direct link received: {item.filename[:45]}"
                                        )
                                        self.manager.start_next_downloads(self._on_item_update)

                                    if getattr(self, "auto_grab_active", False):
                                        self.root.after(3000, self._open_next_auto_link)
                            else:
                                existing_text = self.txt_links.get("1.0", tk.END).strip()
                                if clip not in existing_text:
                                    self.txt_links.insert(tk.END, clip + "\n")
                                    self.status_bar.config(
                                        text=f"📋 DataNodes webpage link added to text box."
                                    )
            except Exception:
                pass
            self.root.after(1000, watcher)

        self.root.after(1000, watcher)


def main():
    root = tk.Tk()
    app = FitGirlDownloaderGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
