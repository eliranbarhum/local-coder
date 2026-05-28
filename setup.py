#!/usr/bin/env python3
"""
local-coder: installer and manager for offline LLM-assisted coding
Tools: Ollama, Aider, Goose  |  Default model: qwen2.5-coder:7b
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from config import (
    AIDER_WRAPPER_TEMPLATE,
    BASE_MODEL,
    DEFAULT_CONTEXT_SIZE,
    DEFAULT_MODEL_ALIAS,
    GOOSE_WRAPPER_TEMPLATE,
    KNOWN_MODELS,
    OLLAMA_DEFAULT_PORT,
    OLLAMA_DOCKER_IMAGE,
    OLLAMA_MIN_VERSION,
)
from install.aider import install_aider, write_aider_wrapper
from install.goose import install_goose, write_goose_wrapper
from install.model import create_model, delete_model, list_models, pull_base_model, set_active_model
from install.ollama import ensure_ollama, ollama_health


def cmd_install(args):
    print("\n=== local-coder setup ===\n")

    if not ensure_ollama(port=args.port, docker=not args.native):
        print("[error] Could not start Ollama. Aborting.")
        sys.exit(1)

    base = args.base_model or BASE_MODEL
    alias = args.alias or DEFAULT_MODEL_ALIAS
    ctx = args.ctx or DEFAULT_CONTEXT_SIZE

    if not args.skip_model:
        pull_base_model(base, port=args.port)
        create_model(alias, base, ctx, port=args.port)
        set_active_model(alias)

    if not args.skip_aider:
        install_aider()
        write_aider_wrapper(alias, port=args.port)

    if not args.skip_goose:
        install_goose()
        write_goose_wrapper(alias, port=args.port)

    print("\n[done] Setup complete.")
    print(f"  aider-local [files]           — Aider with {alias}")
    print(f"  goose-local run -t \"...\"       — Goose one-shot task")
    print(f"  python setup.py status        — check everything is running")
    print(f"  python setup.py model list    — see installed models")


def cmd_status(args):
    port = args.port or OLLAMA_DEFAULT_PORT
    print(f"\nOllama  : ", end="")
    if ollama_health(port):
        print(f"running on :{port}")
    else:
        print("not running")
        return

    print("Models  :")
    for m in list_models(port):
        active = " <-- active" if m["name"] == _read_active_model() else ""
        print(f"  {m['name']}  ({_human_size(m['size'])}){active}")

    print("Aider   :", shutil.which("aider-local") or "not found")
    print("Goose   :", shutil.which("goose-local") or "not found")
    print()


def cmd_model(args):
    port = args.port or OLLAMA_DEFAULT_PORT

    if args.model_cmd == "list":
        if not ollama_health(port):
            print("[error] Ollama is not running.")
            sys.exit(1)
        for m in list_models(port):
            active = " <-- active" if m["name"] == _read_active_model() else ""
            print(f"  {m['name']}  ({_human_size(m['size'])}){active}")

    elif args.model_cmd == "add":
        # Pull a known preset or a raw Ollama model tag
        base = args.base or args.name
        alias = args.alias or args.name.replace(":", "-").replace("/", "-")
        ctx = args.ctx or DEFAULT_CONTEXT_SIZE

        if not ollama_health(port):
            print("[error] Ollama is not running.")
            sys.exit(1)

        if args.name in KNOWN_MODELS:
            preset = KNOWN_MODELS[args.name]
            base = preset["base"]
            ctx = args.ctx or preset["ctx"]
            alias = args.alias or preset["alias"]
            print(f"[model] Using preset '{args.name}': base={base}, ctx={ctx}, alias={alias}")

        pull_base_model(base, port=port)
        create_model(alias, base, ctx, port=port)

        if args.activate:
            _switch_to(alias, port)

    elif args.model_cmd == "switch":
        _switch_to(args.name, port)

    elif args.model_cmd == "remove":
        delete_model(args.name, port=port)
        print(f"[model] Removed {args.name}")

    elif args.model_cmd == "presets":
        print("\nKnown model presets:\n")
        print(f"  {'NAME':<28} {'BASE':<35} {'CTX'}")
        print("  " + "-" * 72)
        for name, p in KNOWN_MODELS.items():
            print(f"  {name:<28} {p['base']:<35} {p['ctx']}")
        print()


def _switch_to(alias, port):
    models = [m["name"].split(":")[0] for m in list_models(port)]
    if alias not in models and f"{alias}:latest" not in [m["name"] for m in list_models(port)]:
        print(f"[error] Model '{alias}' not found. Run: python setup.py model list")
        sys.exit(1)
    set_active_model(alias)
    write_aider_wrapper(alias, port=port)
    write_goose_wrapper(alias, port=port)
    print(f"[model] Switched to {alias}. Wrappers updated.")


def cmd_uninstall(args):
    for w in ["aider-local", "goose-local"]:
        p = Path("/usr/local/bin") / w
        if p.exists():
            p.unlink()
            print(f"[removed] {p}")
    print("[info] Ollama container/process not removed. Stop it manually if needed.")


def _read_active_model():
    p = Path.home() / ".local-coder" / "active_model"
    return p.read_text().strip() if p.exists() else DEFAULT_MODEL_ALIAS


def _human_size(b):
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"


def main():
    parser = argparse.ArgumentParser(prog="setup.py", description="local-coder manager")
    parser.add_argument("--port", type=int, default=OLLAMA_DEFAULT_PORT)
    sub = parser.add_subparsers(dest="cmd")

    # install
    p_install = sub.add_parser("install", help="full setup")
    p_install.add_argument("--native", action="store_true", help="install Ollama natively instead of Docker")
    p_install.add_argument("--base-model", help=f"base model to pull (default: {BASE_MODEL})")
    p_install.add_argument("--alias", help=f"alias for the custom model (default: {DEFAULT_MODEL_ALIAS})")
    p_install.add_argument("--ctx", type=int, help=f"context window size (default: {DEFAULT_CONTEXT_SIZE})")
    p_install.add_argument("--skip-model", action="store_true")
    p_install.add_argument("--skip-aider", action="store_true")
    p_install.add_argument("--skip-goose", action="store_true")
    p_install.set_defaults(func=cmd_install)

    # status
    p_status = sub.add_parser("status", help="show what is running")
    p_status.set_defaults(func=cmd_status)

    # model
    p_model = sub.add_parser("model", help="manage models")
    p_model.add_argument("--port", type=int)
    ms = p_model.add_subparsers(dest="model_cmd")

    ms.add_parser("list", help="list installed models")
    ms.add_parser("presets", help="show known model presets")

    p_add = ms.add_parser("add", help="pull and register a model")
    p_add.add_argument("name", help="preset name or ollama model tag (e.g. deepseek-coder:6.7b)")
    p_add.add_argument("--base", help="override base model tag")
    p_add.add_argument("--alias", help="alias for wrapper scripts")
    p_add.add_argument("--ctx", type=int, help="context window size")
    p_add.add_argument("--activate", action="store_true", help="switch wrappers to this model after adding")

    p_switch = ms.add_parser("switch", help="switch active model (updates wrappers)")
    p_switch.add_argument("name", help="model alias to activate")

    p_remove = ms.add_parser("remove", help="delete a model from Ollama")
    p_remove.add_argument("name")

    p_model.set_defaults(func=cmd_model)

    # uninstall
    p_un = sub.add_parser("uninstall", help="remove wrapper scripts")
    p_un.set_defaults(func=cmd_uninstall)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
