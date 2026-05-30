import json
import stat
import sys
import urllib.request
from pathlib import Path

from config import (
    GOOSE_WRAPPER,
    GOOSE_WRAPPER_LLAMA,
    GOOSE_WRAPPER_OLLAMA,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
    OLLAMA_DEFAULT_PORT,
)

GOOSE_BINARY = Path.home() / ".local/bin/goose"
GOOSE_RELEASES_URL = "https://api.github.com/repos/block/goose/releases/latest"


def install_goose():
    if GOOSE_BINARY.exists():
        print(f"[goose] Already installed at {GOOSE_BINARY}")
        return

    print("[goose] Fetching latest release...")
    asset_url = _find_release_asset()
    if not asset_url:
        print("[goose] Could not find Linux x86_64 binary.")
        print("        Install manually: https://github.com/block/goose/releases")
        sys.exit(1)

    print(f"[goose] Downloading...")
    GOOSE_BINARY.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(asset_url, GOOSE_BINARY)
    GOOSE_BINARY.chmod(GOOSE_BINARY.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"[goose] Installed at {GOOSE_BINARY}")


def write_goose_wrapper(alias: str, backend: str = "llama",
                        port: int = None, host: str = None):
    if backend == "llama":
        content = GOOSE_WRAPPER_LLAMA.format(
            alias=alias,
            host=host or LLAMA_SERVER_HOST,
            port=port or LLAMA_SERVER_PORT,
        )
    else:
        content = GOOSE_WRAPPER_OLLAMA.format(
            alias=alias,
            port=port or OLLAMA_DEFAULT_PORT,
        )
    _write_wrapper(GOOSE_WRAPPER, content)
    print(f"[goose] Wrapper written: {GOOSE_WRAPPER}  (backend={backend}, model={alias})")


def _write_wrapper(path, content: str):
    import subprocess, tempfile
    try:
        path.write_text(content)
        path.chmod(0o755)
    except PermissionError:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as f:
            f.write(content)
            tmp = f.name
        subprocess.run(["sudo", "cp", tmp, str(path)], check=True)
        subprocess.run(["sudo", "chmod", "+x", str(path)], check=True)
        Path(tmp).unlink(missing_ok=True)


def _find_release_asset() -> str | None:
    try:
        req = urllib.request.Request(
            GOOSE_RELEASES_URL, headers={"User-Agent": "local-coder"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for asset in data.get("assets", []):
            name = asset["name"].lower()
            if "linux" in name and ("x86_64" in name or "amd64" in name or "x64" in name):
                return asset["browser_download_url"]
    except Exception as e:
        print(f"[goose] Release fetch failed: {e}")
    return None
