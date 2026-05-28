import json
import os
import stat
import sys
import urllib.request
from pathlib import Path

from config import GOOSE_WRAPPER_TEMPLATE, OLLAMA_DEFAULT_PORT

WRAPPER_PATH = Path("/usr/local/bin/goose-local")
GOOSE_BINARY = Path.home() / ".local/bin/goose"
GOOSE_RELEASES_URL = "https://api.github.com/repos/block/goose/releases/latest"


def install_goose():
    if GOOSE_BINARY.exists():
        print(f"[goose] Already installed at {GOOSE_BINARY}")
        return

    print("[goose] Fetching latest release info...")
    asset_url = _get_release_asset_url()
    if not asset_url:
        print("[goose] Could not find a Linux x86_64 binary. Install manually from https://github.com/block/goose/releases")
        sys.exit(1)

    print(f"[goose] Downloading {asset_url}...")
    GOOSE_BINARY.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(asset_url, GOOSE_BINARY)
    GOOSE_BINARY.chmod(GOOSE_BINARY.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    print(f"[goose] Installed to {GOOSE_BINARY}")


def write_goose_wrapper(model: str, port=OLLAMA_DEFAULT_PORT):
    content = GOOSE_WRAPPER_TEMPLATE.format(model=model, port=port)
    WRAPPER_PATH.write_text(content)
    WRAPPER_PATH.chmod(0o755)
    print(f"[goose] Wrapper written to {WRAPPER_PATH} (model={model})")


def _get_release_asset_url() -> str | None:
    try:
        req = urllib.request.Request(GOOSE_RELEASES_URL,
                                     headers={"User-Agent": "local-coder-setup"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        for asset in data.get("assets", []):
            name = asset["name"].lower()
            if "linux" in name and ("x86_64" in name or "amd64" in name) and name.endswith((".tar.gz", ".gz", "")):
                return asset["browser_download_url"]
    except Exception as e:
        print(f"[goose] Release fetch failed: {e}")
    return None
