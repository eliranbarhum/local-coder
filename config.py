from pathlib import Path

# Directories
LOCAL_CODER_DIR = Path.home() / ".local-coder"
MODELS_DIR = LOCAL_CODER_DIR / "models"
BIN_DIR = LOCAL_CODER_DIR / "bin"
PID_FILE = LOCAL_CODER_DIR / "llama-server.pid"
ACTIVE_MODEL_FILE = LOCAL_CODER_DIR / "active_model"
MODELS_INDEX = LOCAL_CODER_DIR / "models.json"

# llama-server defaults
LLAMA_SERVER_PORT = 8080
LLAMA_SERVER_HOST = "127.0.0.1"
LLAMA_API_BASE = f"http://{LLAMA_SERVER_HOST}:{LLAMA_SERVER_PORT}/v1"
LLAMA_GITHUB_REPO = "ggml-org/llama.cpp"

# Ollama (optional backend)
OLLAMA_DEFAULT_PORT = 11434
OLLAMA_MIN_VERSION = "0.3.0"
OLLAMA_DOCKER_IMAGE = "ollama/ollama:0.9.0"
OLLAMA_DOCKER_CONTAINER = "local-coder-ollama"
OLLAMA_DOCKER_VOLUME = "local-coder-ollama-data"

# Wrapper script paths
WRAPPER_DIR = Path("/usr/local/bin")
AIDER_WRAPPER = WRAPPER_DIR / "aider-local"
GOOSE_WRAPPER = WRAPPER_DIR / "goose-local"

# Default model
DEFAULT_MODEL = "qwen2.5-coder:7b"

# Model registry — HuggingFace GGUF sources
KNOWN_MODELS = {
    "qwen2.5-coder:7b": {
        "hf_repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "hf_file": "qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        "alias": "qwen2.5-coder-7b",
        "ctx": 16384,
        "size_gb": 4.7,
        "description": "Default — good balance of speed and quality on CPU",
        # Ollama fallback tag (used with --backend ollama)
        "ollama_tag": "qwen2.5-coder:7b",
        "ollama_ctx": 16384,
    },
    "qwen2.5-coder:14b": {
        "hf_repo": "Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        "hf_file": "qwen2.5-coder-14b-instruct-q4_k_m.gguf",
        "alias": "qwen2.5-coder-14b",
        "ctx": 16384,
        "size_gb": 8.7,
        "description": "Better quality, needs ~9GB RAM, slow on CPU",
        "ollama_tag": "qwen2.5-coder:14b",
        "ollama_ctx": 16384,
    },
    "deepseek-coder:6.7b": {
        "hf_repo": "TheBloke/deepseek-coder-6.7B-instruct-GGUF",
        "hf_file": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "alias": "deepseek-coder",
        "ctx": 16384,
        "size_gb": 3.8,
        "description": "Alternative — strong on code completions",
        "ollama_tag": "deepseek-coder:6.7b",
        "ollama_ctx": 16384,
    },
    "codellama:7b": {
        "hf_repo": "TheBloke/CodeLlama-7B-Instruct-GGUF",
        "hf_file": "codellama-7b-instruct.Q4_K_M.gguf",
        "alias": "codellama",
        "ctx": 8192,
        "size_gb": 3.8,
        "description": "Meta CodeLlama — reliable fallback",
        "ollama_tag": "codellama:7b",
        "ollama_ctx": 8192,
    },
    "llama3.2:3b": {
        "hf_repo": "bartowski/Llama-3.2-3B-Instruct-GGUF",
        "hf_file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
        "alias": "llama3-fast",
        "ctx": 8192,
        "size_gb": 2.0,
        "description": "Very fast, good for quick tasks",
        "ollama_tag": "llama3.2:3b",
        "ollama_ctx": 8192,
    },
}

# Wrapper templates
AIDER_WRAPPER_LLAMA = """\
#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
export OPENAI_API_KEY=none
export OPENAI_API_BASE=http://{host}:{port}/v1
exec aider --model openai/{alias} \\
    --no-show-model-warnings \\
    --no-auto-commits \\
    --yes-always \\
    --timeout 3600 \\
    "$@"
"""

GOOSE_WRAPPER_LLAMA = """\
#!/usr/bin/env bash
GOOSE="$HOME/.local/bin/goose"
export OPENAI_API_KEY=none
export OPENAI_BASE_URL=http://{host}:{port}/v1
if [[ "$1" == "run" ]]; then
    shift
    exec $GOOSE run \\
        --provider openai --model {alias} \\
        --no-profile --with-builtin developer \\
        "$@"
else
    exec $GOOSE session \\
        --provider openai --model {alias} \\
        "$@"
fi
"""

AIDER_WRAPPER_OLLAMA = """\
#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_API_BASE=http://localhost:{port}
exec aider --model ollama/{alias} \\
    --no-auto-commits \\
    --yes-always \\
    --timeout 3600 \\
    "$@"
"""

GOOSE_WRAPPER_OLLAMA = """\
#!/usr/bin/env bash
GOOSE="$HOME/.local/bin/goose"
if [[ "$1" == "run" ]]; then
    shift
    exec $GOOSE run \\
        --provider ollama --model {alias} \\
        --no-profile --with-builtin developer \\
        "$@"
else
    exec $GOOSE session \\
        --provider ollama --model {alias} \\
        "$@"
fi
"""
