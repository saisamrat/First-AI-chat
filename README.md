# First AI Chat

A small async CLI chat app built as a practice exercise for Python's `asyncio`, `async`/`await`, and `httpx` — streaming responses from [Groq](https://groq.com)'s OpenAI-compatible API, with conversation history, background autosave, and non-blocking logging.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/)
- A Groq API key ([console.groq.com](https://console.groq.com) → API Keys)

## Setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Create a `.env` file in the project root with your API key (never commit this — it's already in `.gitignore`):
   ```bash
   echo 'GROQ_API_KEY=your-key-here' > .env
   ```

3. Review `config.toml` — the defaults point at Groq's `llama-3.3-70b-versatile` model and read the key from the `GROQ_API_KEY` environment variable named in `config.toml`'s `[api] key_env_var`.

## Running

Load `.env` into your shell, then run the app:

```bash
set -a && source .env && set +a
uv run python3 src/main.py
```

Optional flags:

| Flag | Description |
|---|---|
| `--config <path>` | Use a different config file (default: `config.toml`) |
| `--resume <id>` | Resume a previously saved conversation |

## Using the app

Type normally to chat. Available commands:

| Command | Description |
|---|---|
| `/history` | List saved conversations (id + title) |
| `/load <id>` | Switch to a saved conversation |
| `/save` | Force an immediate save |
| `/clear` | Start a new, empty conversation |
| `/quit` | Exit (flushes any pending autosave first) |

## Project layout

```
config.toml           # app configuration (model, timeouts, log level, ...)
.env                  # GROQ_API_KEY (gitignored, not committed)
src/
  models.py           # Message / Conversation dataclasses
  config.py           # loads + validates config.toml
  logging_setup.py     # non-blocking (queue-based) logging
  history.py          # async save/load/list of conversations as JSON
  api_client.py        # httpx streaming client for the Groq API
  main.py              # CLI loop wiring everything together
data/history/          # saved conversation JSON files
logs/chat.log          # app log output
tests/                # pytest test suite (see below)
```

## Testing

The test suite is split into two groups:

- **Fast/offline tests** (default) — everything except live network calls; `httpx.MockTransport` stands in for the real Groq API.
- **Integration test** — one real end-to-end test against the live Groq API, gated behind a `pytest` marker so it never runs by accident.

```bash
# fast, offline, no API key needed
uv run pytest

# the real end-to-end test — needs GROQ_API_KEY set
set -a && source .env && set +a
uv run pytest -m integration
```
