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


def install_aider():
    print("[aider] Installing aider-chat...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "--quiet", "aider-chat"],
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
    AIDER_WRAPPER.write_text(content)
    AIDER_WRAPPER.chmod(0o755)
    print(f"[aider] Wrapper written: {AIDER_WRAPPER}  (backend={backend}, model={alias})")
