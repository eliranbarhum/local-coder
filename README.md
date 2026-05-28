# local-coder

Offline LLM-assisted coding on your own machine. Installs and manages [Ollama](https://ollama.com), [Aider](https://aider.chat), and [Goose](https://github.com/block/goose) — no cloud API keys required.

## What it does

- Starts an Ollama instance (Docker or native)
- Pulls a code-focused model (default: `qwen2.5-coder:7b`)
- Creates a custom model variant with a 16K context window
- Installs Aider and Goose
- Writes `aider-local` and `goose-local` wrapper scripts wired to the active model
- Lets you add, switch, and remove models at any time — wrappers update automatically

## Requirements

- Linux x86_64
- Python 3.10+
- Docker (recommended) **or** curl for native Ollama install
- ~5GB disk for the default model

## Quick start

```bash
git clone https://github.com/yourname/local-coder
cd local-coder
python setup.py install
```

That's it. When it finishes:

```bash
aider-local myfile.py                      # Aider editing session
goose-local run -t "review this file"      # Goose one-shot task
goose-local                                # Goose interactive session
```

## Install options

```bash
# Use native Ollama binary instead of Docker
python setup.py install --native

# Custom model, alias, and context window
python setup.py install --base-model qwen2.5-coder:14b --alias my-model --ctx 32768

# Skip steps you already did
python setup.py install --skip-model
python setup.py install --skip-aider --skip-goose
```

## Check status

```bash
python setup.py status
```

```
Ollama  : running on :11434
Models  :
  qwen2.5-coder-local  (4.7GB) <-- active
  deepseek-coder-local (3.8GB)
Aider   : /usr/local/bin/aider-local
Goose   : /usr/local/bin/goose-local
```

## Model management

### List installed models

```bash
python setup.py model list
```

### See available presets

```bash
python setup.py model presets
```

| Name | Base | Context | Notes |
|------|------|---------|-------|
| qwen2.5-coder:7b | qwen2.5-coder:7b | 16K | Default — good on CPU |
| qwen2.5-coder:14b | qwen2.5-coder:14b | 16K | Better quality, needs ~10GB RAM |
| deepseek-coder:6.7b | deepseek-coder:6.7b | 16K | Strong on code completion |
| deepseek-coder-v2:16b | deepseek-coder-v2:16b | 32K | Large, needs GPU |
| codellama:7b | codellama:7b | 8K | Meta fallback |
| llama3.2:3b | llama3.2:3b | 8K | Very fast, general purpose |

### Add a model

```bash
# From a preset
python setup.py model add qwen2.5-coder:14b

# Add and immediately switch wrappers to it
python setup.py model add deepseek-coder:6.7b --activate

# Any Ollama model tag, with custom settings
python setup.py model add mistral:7b --alias mistral-local --ctx 8192 --activate
```

### Switch active model

Updates both `aider-local` and `goose-local` wrappers instantly:

```bash
python setup.py model switch deepseek-coder-local
```

### Remove a model

```bash
python setup.py model remove codellama-local
```

## Using the tools

### Aider

Aider reads files you give it and edits them in response to instructions.

```bash
# Review a file
aider-local --read services/main.py --message "find security issues"

# Edit a file
aider-local services/main.py

# Multi-file edit
aider-local src/auth.py src/models.py
```

### Goose

Goose runs autonomously — it reads files, runs shell commands, and writes code on its own.

```bash
# One-shot task (non-interactive)
goose-local run -t "review services/main.py for security issues and list findings"
goose-local run -t "add input validation to the /create endpoint in services/api.py"

# Interactive session
goose-local
```

**Note on speed:** Both tools run on CPU by default. Expect 60–90 seconds per LLM call. A typical file review takes 3–5 minutes.

## Performance by model (CPU, no GPU)

| Model | First token | Simple task | File review |
|-------|-------------|-------------|-------------|
| qwen2.5-coder:7b | ~60s | ~2 min | ~5–8 min |
| qwen2.5-coder:14b | ~120s | ~4 min | ~10–15 min |
| llama3.2:3b | ~20s | ~45s | ~2–3 min |

## Uninstall

Removes the wrapper scripts. Ollama and models are left intact.

```bash
python setup.py uninstall
```

To also remove the Ollama container and all downloaded models:

```bash
docker stop local-coder-ollama && docker rm local-coder-ollama
docker volume rm local-coder-ollama-data
```

## Configuration

Default values are in `config.py`. Change them before running `install` if you want different defaults:

```python
BASE_MODEL = "qwen2.5-coder:7b"     # model to pull on first install
DEFAULT_MODEL_ALIAS = "qwen2.5-coder-local"
DEFAULT_CONTEXT_SIZE = 16384
OLLAMA_DEFAULT_PORT = 11434
```

To add your own model preset, add an entry to `KNOWN_MODELS` in `config.py`.
