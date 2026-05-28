import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from config import DEFAULT_MODEL_ALIAS, OLLAMA_DEFAULT_PORT

_ACTIVE_MODEL_FILE = Path.home() / ".local-coder" / "active_model"

MODELFILE_TEMPLATE = """\
FROM {base}
PARAMETER num_ctx {ctx}
SYSTEM "You are an expert software engineer. Be precise and concise."
"""


def pull_base_model(base: str, port=OLLAMA_DEFAULT_PORT):
    print(f"[model] Pulling {base} (this may take several minutes)...")
    subprocess.run(["ollama", "pull", base], check=True,
                   env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"})


def create_model(alias: str, base: str, ctx: int, port=OLLAMA_DEFAULT_PORT):
    modelfile = MODELFILE_TEMPLATE.format(base=base, ctx=ctx)
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False) as f:
        f.write(modelfile)
        mf_path = f.name
    print(f"[model] Creating '{alias}' (base={base}, ctx={ctx})...")
    subprocess.run(["ollama", "create", alias, "-f", mf_path], check=True,
                   env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"})
    __import__("os").unlink(mf_path)
    print(f"[model] '{alias}' created.")


def delete_model(name: str, port=OLLAMA_DEFAULT_PORT):
    subprocess.run(["ollama", "rm", name], check=True,
                   env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"})


def list_models(port=OLLAMA_DEFAULT_PORT) -> list[dict]:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=5) as r:
            return json.loads(r.read())["models"]
    except Exception:
        return []


def set_active_model(alias: str):
    _ACTIVE_MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ACTIVE_MODEL_FILE.write_text(alias)
    print(f"[model] Active model set to '{alias}'")


def get_active_model() -> str:
    if _ACTIVE_MODEL_FILE.exists():
        return _ACTIVE_MODEL_FILE.read_text().strip()
    return DEFAULT_MODEL_ALIAS
