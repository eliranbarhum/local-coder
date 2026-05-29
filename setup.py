#!/usr/bin/env python3
"""
local-coder: offline LLM-assisted coding
Default backend: llama.cpp (llama-server)
Optional backend: Ollama (--backend ollama)
"""

import argparse
import sys
from pathlib import Path

from config import (
    DEFAULT_MODEL,
    KNOWN_MODELS,
    LLAMA_SERVER_HOST,
    LLAMA_SERVER_PORT,
    MODELS_DIR,
    OLLAMA_DEFAULT_PORT,
    ACTIVE_MODEL_FILE,
)
from install.aider import install_aider, write_aider_wrapper
from install.goose import install_goose, write_goose_wrapper
from install.llama import download_binary, is_running, start_server, stop_server
from install.model import (
    delete_model,
    download_gguf,
    get_active_model,
    get_model_ctx,
    get_model_path,
    list_local_models,
    ollama_create,
    ollama_delete,
    ollama_list,
    ollama_pull,
    register_model,
    set_active_model,
)
from install.ollama import ensure_ollama, ollama_health


def cmd_install(args):
    backend = args.backend
    print(f"\n=== local-coder setup (backend: {backend}) ===\n")

    if backend == "llama":
        _install_llama(args)
    else:
        _install_ollama(args)

    if not args.skip_aider:
        install_aider()
    if not args.skip_goose:
        install_goose()

    alias = _get_alias(args)
    write_aider_wrapper(alias, backend=backend, port=_get_port(args))
    write_goose_wrapper(alias, backend=backend, port=_get_port(args))

    print("\n[done] Setup complete.")
    print(f"  aider-local [files]           — Aider with {alias}")
    print(f"  goose-local run -t \"...\"       — Goose one-shot task")
    print(f"  python setup.py status        — check everything")
    print(f"  python setup.py model list    — installed models")
    print(f"  python setup.py model switch  — change active model")


def _install_llama(args):
    download_binary()

    preset_name = args.model or DEFAULT_MODEL
    preset = _resolve_preset(preset_name)
    alias = args.alias or preset["alias"]
    ctx = args.ctx or preset["ctx"]

    if not args.skip_model:
        hf_repo = args.hf_repo or preset.get("hf_repo")
        hf_file = args.hf_file or preset.get("hf_file")
        model_path = download_gguf(preset_name, hf_repo=hf_repo, hf_file=hf_file)
        register_model(preset_name, model_path, alias, ctx)
        set_active_model(alias)
        start_server(model_path, ctx, port=args.port or LLAMA_SERVER_PORT)
    else:
        # try to start with whatever is active
        active = get_active_model()
        model_path = get_model_path(active)
        if model_path:
            ctx = get_model_ctx(active)
            start_server(model_path, ctx, port=args.port or LLAMA_SERVER_PORT)


def _install_ollama(args):
    port = args.port or OLLAMA_DEFAULT_PORT
    if not ensure_ollama(port=port, docker=True):
        print("[error] Could not start Ollama.")
        sys.exit(1)

    preset_name = args.model or DEFAULT_MODEL
    preset = _resolve_preset(preset_name)
    alias = args.alias or preset.get("ollama_tag", preset_name).replace(":", "-") + "-local"
    ctx = args.ctx or preset.get("ollama_ctx", 16384)
    tag = preset.get("ollama_tag", preset_name)

    if not args.skip_model:
        ollama_pull(tag, port=port)
        ollama_create(alias, tag, ctx, port=port)
        set_active_model(alias)


def cmd_status(args):
    backend = _detect_backend()
    print(f"\nBackend : {backend}")

    if backend == "llama":
        port = args.port or LLAMA_SERVER_PORT
        running = is_running(port)
        print(f"Server  : {'running on :' + str(port) if running else 'stopped'}")
        print(f"Models  : {MODELS_DIR}")
        active = get_active_model()
        for m in list_local_models():
            tag = " <-- active" if m["alias"] == active else ""
            size = _file_size(Path(m["path"]))
            print(f"  {m['alias']:<30} {size}{tag}")
    else:
        port = args.port or OLLAMA_DEFAULT_PORT
        running = ollama_health(port)
        print(f"Ollama  : {'running on :' + str(port) if running else 'stopped'}")
        if running:
            active = get_active_model()
            for m in ollama_list(port):
                tag = " <-- active" if m["name"].split(":")[0] == active else ""
                print(f"  {m['name']:<35} ({_human_size(m['size'])}){tag}")

    from shutil import which
    print(f"Aider   : {which('aider-local') or 'not installed'}")
    print(f"Goose   : {which('goose-local') or 'not installed'}")
    print()


def cmd_server(args):
    if args.server_cmd == "start":
        active = get_active_model()
        model_path = get_model_path(active)
        if not model_path:
            print(f"[error] No model found for '{active}'. Run: python setup.py model list")
            sys.exit(1)
        ctx = get_model_ctx(active)
        start_server(model_path, ctx, port=args.port or LLAMA_SERVER_PORT)

    elif args.server_cmd == "stop":
        stop_server()

    elif args.server_cmd == "restart":
        stop_server()
        import time; time.sleep(1)
        active = get_active_model()
        model_path = get_model_path(active)
        if model_path:
            ctx = get_model_ctx(active)
            start_server(model_path, ctx, port=args.port or LLAMA_SERVER_PORT)

    elif args.server_cmd == "status":
        port = args.port or LLAMA_SERVER_PORT
        if is_running(port):
            print(f"[llama] Running on :{port}, model={get_active_model()}")
        else:
            print("[llama] Not running.")


def cmd_model(args):
    backend = args.backend or _detect_backend()
    port = args.port or (LLAMA_SERVER_PORT if backend == "llama" else OLLAMA_DEFAULT_PORT)

    if args.model_cmd == "list":
        active = get_active_model()
        if backend == "llama":
            models = list_local_models()
            if not models:
                print("No models downloaded yet.")
            for m in models:
                tag = " <-- active" if m["alias"] == active else ""
                size = _file_size(Path(m["path"]))
                print(f"  {m['alias']:<30} {size}  ctx={m['ctx']}{tag}")
        else:
            for m in ollama_list(port):
                tag = " <-- active" if m["name"].split(":")[0] == active else ""
                print(f"  {m['name']:<35} ({_human_size(m['size'])}){tag}")

    elif args.model_cmd == "presets":
        print(f"\n{'NAME':<25} {'ALIAS':<25} {'SIZE':>6}  {'CTX':>6}  DESCRIPTION")
        print("-" * 85)
        for name, p in KNOWN_MODELS.items():
            print(f"{name:<25} {p['alias']:<25} {p['size_gb']:>5.1f}GB  {p['ctx']:>6}  {p['description']}")
        print()

    elif args.model_cmd == "add":
        preset_name = args.name
        preset = _resolve_preset(preset_name, allow_unknown=True)
        alias = args.alias or preset.get("alias", preset_name.replace(":", "-"))
        ctx = args.ctx or preset.get("ctx", 16384)

        if backend == "llama":
            hf_repo = args.hf_repo or preset.get("hf_repo")
            hf_file = args.hf_file or preset.get("hf_file")
            if not hf_repo or not hf_file:
                print("[error] Unknown preset. Provide --hf-repo and --hf-file.")
                sys.exit(1)
            model_path = download_gguf(preset_name, hf_repo=hf_repo, hf_file=hf_file)
            register_model(preset_name, model_path, alias, ctx)
            if args.activate:
                _switch_llama(alias, port)
        else:
            tag = preset.get("ollama_tag", preset_name)
            ollama_pull(tag, port=port)
            ollama_create(alias, tag, ctx, port=port)
            if args.activate:
                _switch_ollama(alias, port)

    elif args.model_cmd == "switch":
        if backend == "llama":
            _switch_llama(args.name, port)
        else:
            _switch_ollama(args.name, port)

    elif args.model_cmd == "remove":
        if backend == "llama":
            delete_model(args.name)
        else:
            ollama_delete(args.name, port=port)
            print(f"[model] Removed {args.name}")


def cmd_uninstall(args):
    stop_server()
    from config import AIDER_WRAPPER, GOOSE_WRAPPER
    for w in [AIDER_WRAPPER, GOOSE_WRAPPER]:
        if w.exists():
            w.unlink()
            print(f"[removed] {w}")
    print("[info] Models and binaries in ~/.local-coder are kept. Delete manually if needed.")


def _switch_llama(alias: str, port: int):
    model_path = get_model_path(alias)
    if not model_path:
        print(f"[error] '{alias}' not found. Run: python setup.py model list")
        sys.exit(1)
    ctx = get_model_ctx(alias)
    stop_server()
    import time; time.sleep(1)
    start_server(model_path, ctx, port=port)
    set_active_model(alias)
    backend = _detect_backend()
    write_aider_wrapper(alias, backend=backend, port=port)
    write_goose_wrapper(alias, backend=backend, port=port)
    print(f"[model] Switched to {alias}. Server restarted, wrappers updated.")


def _switch_ollama(alias: str, port: int):
    set_active_model(alias)
    write_aider_wrapper(alias, backend="ollama", port=port)
    write_goose_wrapper(alias, backend="ollama", port=port)
    print(f"[model] Switched to {alias}. Wrappers updated.")


def _detect_backend() -> str:
    # If llama-server is running, it's llama; otherwise check Ollama
    if is_running(LLAMA_SERVER_PORT):
        return "llama"
    if ollama_health(OLLAMA_DEFAULT_PORT):
        return "ollama"
    return "llama"  # default


def _resolve_preset(name: str, allow_unknown=False) -> dict:
    if name in KNOWN_MODELS:
        return KNOWN_MODELS[name]
    if allow_unknown:
        return {}
    print(f"[error] Unknown preset '{name}'. Run: python setup.py model presets")
    sys.exit(1)


def _get_alias(args) -> str:
    preset = _resolve_preset(args.model or DEFAULT_MODEL)
    return args.alias or preset.get("alias", "local-model")


def _get_port(args) -> int:
    backend = getattr(args, "backend", "llama")
    default = LLAMA_SERVER_PORT if backend == "llama" else OLLAMA_DEFAULT_PORT
    return getattr(args, "port", None) or default


def _file_size(p: Path) -> str:
    if not p.exists():
        return "missing"
    b = p.stat().st_size
    return _human_size(b)


def _human_size(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


def main():
    parser = argparse.ArgumentParser(prog="setup.py", description="local-coder manager")

    sub = parser.add_subparsers(dest="cmd")

    # ── install ────────────────────────────────────────────────────────────────
    p_i = sub.add_parser("install", help="full setup")
    p_i.add_argument("--backend", choices=["llama", "ollama"], default="llama")
    p_i.add_argument("--model", help=f"preset name (default: {DEFAULT_MODEL})")
    p_i.add_argument("--alias", help="custom name for this model")
    p_i.add_argument("--ctx", type=int, help="context window size")
    p_i.add_argument("--port", type=int)
    p_i.add_argument("--hf-repo", dest="hf_repo", help="HuggingFace repo (llama backend)")
    p_i.add_argument("--hf-file", dest="hf_file", help="GGUF filename in the repo")
    p_i.add_argument("--skip-model", action="store_true")
    p_i.add_argument("--skip-aider", action="store_true")
    p_i.add_argument("--skip-goose", action="store_true")
    p_i.set_defaults(func=cmd_install)

    # ── status ─────────────────────────────────────────────────────────────────
    p_s = sub.add_parser("status", help="show what is running")
    p_s.add_argument("--port", type=int)
    p_s.set_defaults(func=cmd_status)

    # ── server ─────────────────────────────────────────────────────────────────
    p_srv = sub.add_parser("server", help="manage llama-server process")
    p_srv.add_argument("--port", type=int)
    srv_sub = p_srv.add_subparsers(dest="server_cmd")
    srv_sub.add_parser("start")
    srv_sub.add_parser("stop")
    srv_sub.add_parser("restart")
    srv_sub.add_parser("status")
    p_srv.set_defaults(func=cmd_server)

    # ── model ──────────────────────────────────────────────────────────────────
    p_m = sub.add_parser("model", help="manage models")
    p_m.add_argument("--backend", choices=["llama", "ollama"])
    p_m.add_argument("--port", type=int)
    m_sub = p_m.add_subparsers(dest="model_cmd")

    m_sub.add_parser("list")
    m_sub.add_parser("presets")

    p_add = m_sub.add_parser("add", help="download and register a model")
    p_add.add_argument("name", help="preset name or HuggingFace model tag")
    p_add.add_argument("--alias")
    p_add.add_argument("--ctx", type=int)
    p_add.add_argument("--hf-repo", dest="hf_repo")
    p_add.add_argument("--hf-file", dest="hf_file")
    p_add.add_argument("--activate", action="store_true")

    p_sw = m_sub.add_parser("switch", help="switch active model (restarts server, updates wrappers)")
    p_sw.add_argument("name")

    p_rm = m_sub.add_parser("remove", help="delete a model")
    p_rm.add_argument("name")

    p_m.set_defaults(func=cmd_model)

    # ── uninstall ──────────────────────────────────────────────────────────────
    p_un = sub.add_parser("uninstall", help="stop server and remove wrappers")
    p_un.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
