"""
llama-server: download binary, start/stop server, health check.
"""

import json
import os
import signal
import subprocess
import sys
import tarfile
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
    archive_path = BIN_DIR / asset_name

    print(f"[llama] Downloading {asset_name}...")
    _download_with_progress(asset_url, archive_path)

    print("[llama] Extracting llama-server...")
    found_binary = False
    if asset_name.endswith(".tar.gz") or asset_name.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            members = tf.getmembers()
            for m in members:
                if not m.isfile():
                    continue
                basename = Path(m.name).name
                dest = BIN_DIR / basename
                f = tf.extractfile(m)
                if f is None:
                    continue
                dest.write_bytes(f.read())
                if basename == "llama-server":
                    dest.chmod(0o755)
                    found_binary = True
                elif basename.endswith(".so") or basename.endswith(".dylib"):
                    dest.chmod(0o644)
    else:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                basename = Path(name).name
                if not basename:
                    continue
                dest = BIN_DIR / basename
                dest.write_bytes(zf.read(name))
                if basename == "llama-server":
                    dest.chmod(0o755)
                    found_binary = True
                elif basename.endswith(".so") or basename.endswith(".dylib"):
                    dest.chmod(0o644)

    archive_path.unlink()
    if not found_binary:
        print("[llama] llama-server not found in archive.")
        return False
    _create_soname_symlinks()
    print(f"[llama] Binary installed at {LLAMA_BIN}")
    return True


def _create_soname_symlinks():
    """Create .so.N symlinks for versioned shared libraries (e.g. libfoo.so.1.2.3 → libfoo.so.1)."""
    import re
    for p in BIN_DIR.glob("*.so.*"):
        m = re.match(r"^(.+\.so\.\d+)\.\d+\.\d+$", p.name)
        if m:
            link = BIN_DIR / m.group(1)
            if not link.exists():
                link.symlink_to(p.name)


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

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(BIN_DIR) + ":" + env.get("LD_LIBRARY_PATH", "")
    print(f"[llama] Starting server (model={model_path.name}, ctx={ctx_size}, threads={threads})...")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
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


def _wait_for_server(port, timeout=120) -> bool:
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
            is_linux = "linux" in name or "ubuntu" in name
            is_x64 = "x64" in name or "amd64" in name or "x86_64" in name
            is_archive = name.endswith(".zip") or name.endswith(".tar.gz") or name.endswith(".tgz")
            # Skip GPU-specific builds (rocm, cuda, vulkan, openvino) for the default CPU build
            is_gpu = any(g in name for g in ("rocm", "cuda", "vulkan", "openvino", "hip"))
            if is_linux and is_x64 and is_archive and not is_gpu:
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
