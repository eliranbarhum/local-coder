"""
llama-server: download binary, start/stop server, health check.
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

from config import BIN_DIR, LLAMA_GITHUB_REPO, LLAMA_SERVER_HOST, LLAMA_SERVER_PORT, PID_FILE

LLAMA_BIN = BIN_DIR / "llama-server"


def ensure_binary() -> bool:
    if LLAMA_BIN.exists():
        print(f"[llama] Binary already at {LLAMA_BIN}")
        return True
    return download_binary()


def download_binary() -> bool:
    print("[llama] Fetching latest release from GitHub...")
    asset_url, asset_name = _find_release_asset()
    if not asset_url:
        print("[llama] Could not find a Linux x86_64 binary. Build from source:")
        print("        https://github.com/ggml-org/llama.cpp#build")
        return False

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = BIN_DIR / asset_name

    print(f"[llama] Downloading {asset_name}...")
    _download_with_progress(asset_url, zip_path)

    print("[llama] Extracting llama-server...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        candidates = [n for n in zf.namelist() if n.endswith("llama-server") or n.endswith("llama-server.exe")]
        if not candidates:
            # newer releases use 'llama-server' at root or in bin/
            candidates = [n for n in zf.namelist() if "llama-server" in n]
        if not candidates:
            print(f"[llama] llama-server not found in archive. Contents: {zf.namelist()[:10]}")
            return False
        member = candidates[0]
        data = zf.read(member)
        LLAMA_BIN.write_bytes(data)
        LLAMA_BIN.chmod(0o755)

    zip_path.unlink()
    print(f"[llama] Binary installed at {LLAMA_BIN}")
    return True


def start_server(model_path: Path, ctx_size: int, port=LLAMA_SERVER_PORT,
                 host=LLAMA_SERVER_HOST, threads: int = None) -> bool:
    if is_running(port):
        print(f"[llama] Server already running on :{port}")
        return True

    if not LLAMA_BIN.exists():
        print("[llama] Binary not found. Run: python setup.py install")
        return False

    if threads is None:
        threads = os.cpu_count() or 4

    cmd = [
        str(LLAMA_BIN),
        "-m", str(model_path),
        "--ctx-size", str(ctx_size),
        "--port", str(port),
        "--host", host,
        "--threads", str(threads),
        "--parallel", "1",
        "-n", "-1",
        "--log-disable",
    ]

    print(f"[llama] Starting server (model={model_path.name}, ctx={ctx_size}, threads={threads})...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(proc.pid))

    return _wait_for_server(port)


def stop_server():
    pid = _read_pid()
    if pid is None:
        print("[llama] No server PID found.")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"[llama] Stopped server (PID {pid})")
    except ProcessLookupError:
        print(f"[llama] Process {pid} not found (already stopped?)")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


def is_running(port=LLAMA_SERVER_PORT) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _wait_for_server(port, timeout=60) -> bool:
    print("[llama] Waiting for server", end="", flush=True)
    for _ in range(timeout):
        if is_running(port):
            print(" ready.")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" timed out.")
    return False


def _read_pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except ValueError:
        return None


def _find_release_asset() -> tuple[str, str]:
    try:
        req = urllib.request.Request(
            f"https://api.github.com/repos/{LLAMA_GITHUB_REPO}/releases/latest",
            headers={"User-Agent": "local-coder"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for asset in data.get("assets", []):
            name = asset["name"].lower()
            if "linux" in name and ("x64" in name or "amd64" in name or "x86_64" in name) and name.endswith(".zip"):
                return asset["browser_download_url"], asset["name"]
    except Exception as e:
        print(f"[llama] GitHub API error: {e}")
    return None, None


def _download_with_progress(url: str, dest: Path):
    def _report(block, block_size, total):
        if total > 0:
            pct = min(100, block * block_size * 100 // total)
            print(f"\r[llama] {pct}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_report)
    print()
