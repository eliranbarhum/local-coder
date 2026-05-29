# local-coder

Offline LLM-assisted coding on your own machine. No cloud API keys, no Docker required.

**Default backend: [llama.cpp](https://github.com/ggml-org/llama.cpp)** — downloads a prebuilt binary and a GGUF model from HuggingFace. The model stays in RAM as long as the server runs. No timeouts, no model unloading, no wrappers around wrappers.

Optional backend: Ollama (`--backend ollama`) — for people who already have it running.

Tools installed: [Aider](https://aider.chat) and [Goose](https://github.com/block/goose), both wired to `http://localhost:8080/v1`.

## Requirements

- Linux x86_64
- Python 3.10+
- ~5GB disk for the default model

## Quick start

```bash
git clone https://github.com/eliranbarhum/local-coder
cd local-coder
python setup.py install
```

Downloads the llama-server binary, pulls `qwen2.5-coder:7b` from HuggingFace (~4.7GB), starts the server, installs Aider and Goose.

```bash
aider-local myfile.py                      # Aider editing session
goose-local run -t "review this file"      # Goose one-shot task
goose-local                                # Goose interactive session
```

## Install options

```bash
# Different model
python setup.py install --model deepseek-coder:6.7b

# Custom HuggingFace model (not in presets)
python setup.py install --hf-repo TheBloke/Mistral-7B-Instruct-v0.2-GGUF \
                        --hf-file mistral-7b-instruct-v0.2.Q4_K_M.gguf \
                        --alias mistral --ctx 8192

# Use Ollama instead of llama.cpp
python setup.py install --backend ollama

# Skip steps you already did
python setup.py install --skip-model
python setup.py install --skip-aider --skip-goose
```

## Why llama.cpp instead of Ollama?

| | llama.cpp | Ollama |
|--|-----------|--------|
| Docker | Not needed | Optional |
| Model stays in RAM | Yes — until you stop the server | No — unloads after 5 min by default |
| Timeout issues | None | Yes (`OLLAMA_KEEP_ALIVE` workaround needed) |
| Overhead | Direct inference | Wrapper around llama.cpp |
| Model management | Download GGUF once | `ollama pull` from registry |

Ollama is more convenient for pulling many models. For a local coding tool with one active model, llama.cpp is simpler and faster.

## Status

```bash
python setup.py status
```

```
Backend : llama
Server  : running on :8080
Models  : /home/user/.local-coder/models
  qwen2.5-coder-7b               4.7GB  <-- active
  deepseek-coder                 3.8GB
Aider   : /usr/local/bin/aider-local
Goose   : /usr/local/bin/goose-local
```

## Server management

```bash
python setup.py server start     # start with active model
python setup.py server stop      # stop
python setup.py server restart   # stop + start
python setup.py server status    # running?
```

## Model management

### List models

```bash
python setup.py model list
```

### See presets

```bash
python setup.py model presets
```

| Name | Alias | Size | Context | Notes |
|------|-------|------|---------|-------|
| qwen2.5-coder:7b | qwen2.5-coder-7b | 4.7GB | 16K | Default |
| qwen2.5-coder:14b | qwen2.5-coder-14b | 8.7GB | 16K | Better quality |
| deepseek-coder:6.7b | deepseek-coder | 3.8GB | 16K | Strong on completions |
| codellama:7b | codellama | 3.8GB | 8K | Meta fallback |
| llama3.2:3b | llama3-fast | 2.0GB | 8K | Very fast |

### Add a model

```bash
# From a preset — downloads GGUF and registers it
python setup.py model add deepseek-coder:6.7b

# Add and switch to it immediately (stops server, restarts with new model)
python setup.py model add qwen2.5-coder:14b --activate

# Any GGUF from HuggingFace
python setup.py model add my-model \
  --hf-repo TheBloke/Mistral-7B-Instruct-v0.2-GGUF \
  --hf-file mistral-7b-instruct-v0.2.Q4_K_M.gguf \
  --ctx 8192 --activate
```

### Switch active model

Stops llama-server, restarts with the new model, updates both wrappers:

```bash
python setup.py model switch deepseek-coder
```

### Remove a model

```bash
python setup.py model remove codellama
```

## Using the tools

### Aider

Aider reads files you give it and edits them based on your instructions.

```bash
# Review a file
aider-local --read services/main.py --message "find security issues"

# Edit mode (interactive)
aider-local services/main.py

# Multi-file
aider-local src/auth.py src/models.py
```

### Goose

Goose runs autonomously — reads files with shell tools, makes edits, runs commands.

```bash
# One-shot (non-interactive)
goose-local run -t "review services/main.py and list security findings"
goose-local run -t "add input validation to the /create endpoint in api.py"

# Interactive session
goose-local
```

## Performance by model (CPU, no GPU)

| Model | First token | Simple task | File review |
|-------|-------------|-------------|-------------|
| llama3.2:3b | ~15s | ~30s | ~2 min |
| qwen2.5-coder:7b | ~60s | ~2 min | ~5–8 min |
| qwen2.5-coder:14b | ~120s | ~5 min | ~12–18 min |

## Uninstall

```bash
python setup.py uninstall
```

Stops the server and removes `aider-local` / `goose-local`. Models and the llama-server binary in `~/.local-coder` are kept — delete manually if needed:

```bash
rm -rf ~/.local-coder
```

## Configuration

Defaults are in `config.py`. Change before running install:

```python
DEFAULT_MODEL = "qwen2.5-coder:7b"
LLAMA_SERVER_PORT = 8080
```

Add a custom model preset to `KNOWN_MODELS` in `config.py` to make it available via `model add <name>`.
