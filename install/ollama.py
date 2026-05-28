import subprocess
import sys
import time
import urllib.request
import json
from pathlib import Path

from config import (
    OLLAMA_DEFAULT_PORT,
    OLLAMA_DOCKER_CONTAINER,
    OLLAMA_DOCKER_IMAGE,
    OLLAMA_DOCKER_VOLUME,
    OLLAMA_MIN_VERSION,
)


def ollama_health(port=OLLAMA_DEFAULT_PORT) -> bool:
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/api/tags", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def ensure_ollama(port=OLLAMA_DEFAULT_PORT, docker=True) -> bool:
    if ollama_health(port):
        print(f"[ollama] Already running on :{port}")
        return True

    if docker:
        return _start_docker(port)
    else:
        return _install_native(port)


def _start_docker(port):
    if not _docker_available():
        print("[ollama] Docker not found. Try --native or install Docker first.")
        return False

    # check if container already exists (stopped)
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={OLLAMA_DOCKER_CONTAINER}", "--format", "{{.Status}}"],
        capture_output=True, text=True,
    )
    if result.stdout.strip():
        print(f"[ollama] Starting existing container {OLLAMA_DOCKER_CONTAINER}...")
        subprocess.run(["docker", "start", OLLAMA_DOCKER_CONTAINER], check=True)
    else:
        print(f"[ollama] Creating container from {OLLAMA_DOCKER_IMAGE}...")
        subprocess.run([
            "docker", "run", "-d",
            "--name", OLLAMA_DOCKER_CONTAINER,
            "-p", f"{port}:11434",
            "-v", f"{OLLAMA_DOCKER_VOLUME}:/root/.ollama",
            OLLAMA_DOCKER_IMAGE,
        ], check=True)

    return _wait_for_ollama(port)


def _install_native(port):
    print("[ollama] Installing Ollama natively...")
    subprocess.run(
        "curl -fsSL https://ollama.com/install.sh | sh",
        shell=True, check=True,
    )
    subprocess.Popen(["ollama", "serve"])
    return _wait_for_ollama(port)


def _wait_for_ollama(port, timeout=60):
    print(f"[ollama] Waiting for Ollama to start", end="", flush=True)
    for _ in range(timeout):
        if ollama_health(port):
            print(" ready.")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" timed out.")
    return False


def _docker_available():
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0
