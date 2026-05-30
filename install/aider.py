import subprocess
import sys
from pathlib import Path

from config import (
    AIDER_WRAPPER,
    AIDER_WRAPPER_LLAMA,
    AIDER_WRAPPER_OLLAMA,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
    OLLAMA_DEFAULT_PORT,
)


def _ensure_pip():
    """Install pip if missing (Ubuntu ships without it in some variants)."""
    result = subprocess.run(
        [sys.executable, "-m", "pip", "--version"],
        capture_output=True,
    )
    if result.returncode != 0:
        print("[aider] pip not found — installing python3-pip...")
        subprocess.run(["sudo", "apt-get", "install", "-y", "python3-pip"], check=True)


def install_aider():
    _ensure_pip()
    print("[aider] Installing aider-chat...")
    # --break-system-packages required on Ubuntu 22.04+ (PEP 668)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--quiet", "aider-chat"],
        capture_output=True,
    )
    if result.returncode != 0:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "--quiet",
             "--break-system-packages", "aider-chat"],
            check=True,
        )
    print("[aider] Installed.")


def write_aider_wrapper(alias: str, backend: str = "llama",
                        port: int = None, host: str = None):
    if backend == "llama":
        content = AIDER_WRAPPER_LLAMA.format(
            alias=alias,
            host=host or LLAMA_SERVER_HOST,
            port=port or LLAMA_SERVER_PORT,
        )
    else:
        content = AIDER_WRAPPER_OLLAMA.format(
            alias=alias,
            port=port or OLLAMA_DEFAULT_PORT,
        )
    _write_wrapper(AIDER_WRAPPER, content)
    print(f"[aider] Wrapper written: {AIDER_WRAPPER}  (backend={backend}, model={alias})")


def _write_wrapper(path, content: str):
    try:
        path.write_text(content)
        path.chmod(0o755)
    except PermissionError:
        import tempfile
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".sh") as f:
            f.write(content)
            tmp = f.name
        subprocess.run(["sudo", "cp", tmp, str(path)], check=True)
        subprocess.run(["sudo", "chmod", "+x", str(path)], check=True)
        Path(tmp).unlink(missing_ok=True)
