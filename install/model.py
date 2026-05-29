"""
Model management: download GGUFs from HuggingFace, track active model.
Works for both llama.cpp (GGUF files) and Ollama backends.
"""

import json
import subprocess
import urllib.request
from pathlib import Path

from config import (
    ACTIVE_MODEL_FILE,
    DEFAULT_MODEL,
    KNOWN_MODELS,
    LOCAL_CODER_DIR,
    MODELS_DIR,
    MODELS_INDEX,
    OLLAMA_DEFAULT_PORT,
)

HF_BASE = "https://huggingface.co"


# ── GGUF / llama.cpp ──────────────────────────────────────────────────────────

def download_gguf(preset_name: str, hf_repo: str = None, hf_file: str = None) -> Path:
    """Download a GGUF file from HuggingFace. Returns the local path."""
    if preset_name in KNOWN_MODELS and not hf_repo:
        preset = KNOWN_MODELS[preset_name]
        hf_repo = preset["hf_repo"]
        hf_file = preset["hf_file"]

    if not hf_repo or not hf_file:
        raise ValueError(f"Unknown model '{preset_name}'. Use 'python setup.py model presets' to see options.")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODELS_DIR / hf_file

    if dest.exists():
        print(f"[model] Already downloaded: {dest}")
        return dest

    url = f"{HF_BASE}/{hf_repo}/resolve/main/{hf_file}"
    print(f"[model] Downloading {hf_file} from {hf_repo}...")
    print(f"[model] Source: {url}")

    def _report(block, block_size, total):
        if total > 0:
            mb_done = block * block_size / 1024 / 1024
            mb_total = total / 1024 / 1024
            pct = min(100, int(mb_done * 100 / mb_total))
            print(f"\r[model] {pct}%  {mb_done:.0f}MB / {mb_total:.0f}MB", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=_report)
    print(f"\n[model] Saved to {dest}")
    return dest


def register_model(preset_name: str, model_path: Path, alias: str, ctx: int):
    """Add a model to the local index."""
    index = _load_index()
    index[alias] = {
        "preset": preset_name,
        "path": str(model_path),
        "alias": alias,
        "ctx": ctx,
    }
    _save_index(index)


def list_local_models() -> list[dict]:
    return list(_load_index().values())


def get_model_path(alias: str) -> Path | None:
    index = _load_index()
    if alias in index:
        p = Path(index[alias]["path"])
        return p if p.exists() else None
    # also accept filename directly
    p = MODELS_DIR / alias
    return p if p.exists() else None


def get_model_ctx(alias: str) -> int:
    index = _load_index()
    return index.get(alias, {}).get("ctx", 16384)


def delete_model(alias: str):
    index = _load_index()
    if alias not in index:
        print(f"[model] '{alias}' not in index.")
        return
    path = Path(index[alias]["path"])
    if path.exists():
        path.unlink()
        print(f"[model] Deleted {path}")
    del index[alias]
    _save_index(index)
    print(f"[model] Removed '{alias}' from index.")


def set_active_model(alias: str):
    LOCAL_CODER_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_MODEL_FILE.write_text(alias)
    print(f"[model] Active model: {alias}")


def get_active_model() -> str:
    if ACTIVE_MODEL_FILE.exists():
        return ACTIVE_MODEL_FILE.read_text().strip()
    return KNOWN_MODELS.get(DEFAULT_MODEL, {}).get("alias", "qwen2.5-coder-7b")


def _load_index() -> dict:
    if MODELS_INDEX.exists():
        return json.loads(MODELS_INDEX.read_text())
    return {}


def _save_index(index: dict):
    MODELS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    MODELS_INDEX.write_text(json.dumps(index, indent=2))


# ── Ollama backend ────────────────────────────────────────────────────────────

def ollama_pull(tag: str, port=OLLAMA_DEFAULT_PORT):
    print(f"[model] Pulling {tag} via Ollama...")
    subprocess.run(
        ["ollama", "pull", tag], check=True,
        env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"},
    )


def ollama_create(alias: str, base: str, ctx: int, port=OLLAMA_DEFAULT_PORT):
    import tempfile
    modelfile = f"FROM {base}\nPARAMETER num_ctx {ctx}\n"
    with tempfile.NamedTemporaryFile("w", suffix=".Modelfile", delete=False) as f:
        f.write(modelfile)
        mf_path = f.name
    print(f"[model] Creating Ollama model '{alias}'...")
    subprocess.run(
        ["ollama", "create", alias, "-f", mf_path], check=True,
        env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"},
    )
    __import__("os").unlink(mf_path)


def ollama_list(port=OLLAMA_DEFAULT_PORT) -> list[dict]:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=5) as r:
            return json.loads(r.read())["models"]
    except Exception:
        return []


def ollama_delete(name: str, port=OLLAMA_DEFAULT_PORT):
    subprocess.run(
        ["ollama", "rm", name], check=True,
        env={**__import__("os").environ, "OLLAMA_HOST": f"http://localhost:{port}"},
    )
