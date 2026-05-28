OLLAMA_DEFAULT_PORT = 11434
OLLAMA_MIN_VERSION = "0.3.0"
OLLAMA_DOCKER_IMAGE = "ollama/ollama:0.9.0"
OLLAMA_DOCKER_CONTAINER = "local-coder-ollama"
OLLAMA_DOCKER_VOLUME = "local-coder-ollama-data"

BASE_MODEL = "qwen2.5-coder:7b"
DEFAULT_MODEL_ALIAS = "qwen2.5-coder-local"
DEFAULT_CONTEXT_SIZE = 16384

# Model presets: name → {base, alias, ctx, description}
KNOWN_MODELS = {
    "qwen2.5-coder:7b": {
        "base": "qwen2.5-coder:7b",
        "alias": "qwen2.5-coder-local",
        "ctx": 16384,
        "description": "Default — good balance of speed and quality on CPU",
    },
    "qwen2.5-coder:14b": {
        "base": "qwen2.5-coder:14b",
        "alias": "qwen2.5-coder-14b",
        "ctx": 16384,
        "description": "Better quality, needs ~10GB RAM, slow on CPU",
    },
    "deepseek-coder:6.7b": {
        "base": "deepseek-coder:6.7b",
        "alias": "deepseek-coder-local",
        "ctx": 16384,
        "description": "Alternative small model, strong on code completion",
    },
    "deepseek-coder-v2:16b": {
        "base": "deepseek-coder-v2:16b",
        "alias": "deepseek-coder-v2",
        "ctx": 32768,
        "description": "Larger DeepSeek v2, needs GPU or high RAM",
    },
    "codellama:7b": {
        "base": "codellama:7b",
        "alias": "codellama-local",
        "ctx": 8192,
        "description": "Meta CodeLlama 7B, fallback option",
    },
    "llama3.2:3b": {
        "base": "llama3.2:3b",
        "alias": "llama3-fast",
        "ctx": 8192,
        "description": "Very fast, small, general purpose — good for quick tasks",
    },
}

AIDER_WRAPPER_TEMPLATE = """\
#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
export OLLAMA_API_BASE="http://localhost:{port}"
exec aider --model ollama/{model} --no-auto-commits --yes-always "$@"
"""

GOOSE_WRAPPER_TEMPLATE = """\
#!/usr/bin/env bash
GOOSE="$HOME/.local/bin/goose"
if [[ "$1" == "run" ]]; then
    shift
    exec $GOOSE run \\
        --provider ollama --model {model} \\
        --no-profile --with-builtin developer \\
        "$@"
else
    exec $GOOSE session \\
        --provider ollama --model {model} \\
        "$@"
fi
"""
