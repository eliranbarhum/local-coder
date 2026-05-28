import subprocess
import sys
from pathlib import Path

from config import AIDER_WRAPPER_TEMPLATE, OLLAMA_DEFAULT_PORT

WRAPPER_PATH = Path("/usr/local/bin/aider-local")


def install_aider():
    print("[aider] Installing aider-chat...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--user", "--quiet", "aider-chat"], check=True)
    print("[aider] Installed.")


def write_aider_wrapper(model: str, port=OLLAMA_DEFAULT_PORT):
    content = AIDER_WRAPPER_TEMPLATE.format(model=model, port=port)
    _write_executable(WRAPPER_PATH, content)
    print(f"[aider] Wrapper written to {WRAPPER_PATH} (model={model})")


def _write_executable(path: Path, content: str):
    path.write_text(content)
    path.chmod(0o755)
