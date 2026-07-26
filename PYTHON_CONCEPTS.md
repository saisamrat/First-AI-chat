# Python Concepts Used in This Project

A reference of every Python concept this project touches, with a short explanation and exactly where it shows up — for reviewing later without re-reading the whole codebase.

**Contents**
- [Data modeling](#data-modeling)
- [Core language mechanics](#core-language-mechanics)
- [Files, OS, and JSON](#files-os-and-json)
- [Exception handling](#exception-handling)
- [Async fundamentals](#async-fundamentals)
- [Async I/O patterns](#async-io-patterns)
- [Networking and streaming](#networking-and-streaming)
- [Logging and threading](#logging-and-threading)
- [CLI plumbing](#cli-plumbing)
- [Testing](#testing)
- [Recurring gotchas worth re-reading](#recurring-gotchas-worth-re-reading)

## Data modeling

### `@dataclass`
Auto-generates `__init__`, `__repr__`, and `__eq__` from declared fields, so you don't hand-write boilerplate constructors.
- [`src/models.py:7`](src/models.py) — `Message`
- [`src/models.py:21`](src/models.py) — `Conversation`
- [`src/config.py:9`](src/config.py) — `Config`

### `field(default_factory=...)`
For a default value that must be *computed fresh per instance* (current time, a new random id) rather than a fixed constant evaluated once at class definition.
- [`src/models.py:10`](src/models.py) — `timestamp` defaults to `datetime.now(timezone.utc).isoformat()`
- [`src/models.py:22`](src/models.py) — `id` defaults to a fresh `uuid.uuid4().hex[:8]`
- [`src/models.py:24`](src/models.py) — `messages` defaults to a new empty list (never share a mutable default across instances)

### `@classmethod`
A method bound to the *class*, not an instance (`cls` instead of `self`) — used to build a new instance from external data rather than operate on an existing one.
- [`src/models.py:15-17`](src/models.py) — `Message.from_dict`
- [`src/models.py:38-44`](src/models.py) — `Conversation.from_dict`

### Type hints
`str`, `int`, `float`, `bool`, `list[dict]`, `list[Message]`, `AsyncIterator[str]` — annotate expected types; not enforced at runtime, but document intent and let editors/linters catch mismatches.
- Throughout every module's function signatures.

### `uuid.uuid4().hex[:8]`
Generates a random UUID, converts to hex text, takes the first 8 characters — a short, good-enough-for-this-app unique id.
- [`src/models.py:3,22`](src/models.py)

### `datetime.now(timezone.utc).isoformat()`
Timezone-aware current timestamp, serialized to a sortable ISO-8601 string.
- [`src/models.py:2,10`](src/models.py)

## Core language mechanics

### List comprehensions
`[expr for item in iterable]` — builds a new list without a manual `for` + `.append()` loop.
- [`src/models.py:35`](src/models.py) — `[message.to_dict() for message in self.messages]`
- [`src/models.py:43`](src/models.py) — `[Message.from_dict(m) for m in data["messages"]]`
- [`src/history.py:58`](src/history.py) — filtering filenames to `.json` only

### List/string slicing (`[start:stop]`)
Extracting a sub-range. The recurring bug source in this project was confusing **slicing** (`x[a:b]`, a range) with **indexing** (`x[a]`, one element) — dropping the trailing colon silently changes the meaning.
- [`src/api_client.py:11`](src/api_client.py) — `conversation.messages[-max_history_messages:]` (last N messages)
- [`src/api_client.py:42`](src/api_client.py) — `line[len("data: "):]` (strip a fixed-length prefix)

### f-strings
`f"{value}"` — inline expression interpolation into a string.
- Throughout; e.g. [`src/history.py:15,19`](src/history.py), [`src/main.py:44,50,56,59,62,73`](src/main.py)

### String methods: `.strip()`, `.startswith()`, `.split(maxsplit=1)`, `.endswith()`
Trimming whitespace, prefix checks, splitting a command from its argument on the *first* space only, and filtering by suffix.
- [`src/main.py:33,37`](src/main.py) — parsing `"/load abc123"` into `command="/load"`, `arg="abc123"`
- [`src/api_client.py:38,40`](src/api_client.py) — detecting blank lines / the `"data: "` SSE prefix
- [`src/history.py:58`](src/history.py) — `.endswith(".json")`

## Files, OS, and JSON

### `with open(...) as f:` (context managers)
Guarantees a resource (here, a file handle) is closed even if an exception happens mid-block — equivalent to a `try`/`finally`. Same idea reused for `async with` on locks and HTTP clients (see below).
- [`src/config.py:27`](src/config.py) — reading TOML in binary mode
- [`src/history.py:27,45`](src/history.py) — writing/reading JSON files

### `os.makedirs(path, exist_ok=True)`
Creates a directory (and parents) if missing; `exist_ok=True` avoids an error if it already exists.
- [`src/logging_setup.py:10`](src/logging_setup.py) — ensures `logs/` exists before creating the log file
- [`src/history.py:16`](src/history.py) — ensures the history directory exists before saving

### `os.environ.get(...)` — reading secrets from the environment
Keeps API keys out of source/config files; only the *name* of the env var lives in `config.toml`, the real value is read at runtime.
- [`src/config.py:39`](src/config.py)

### `os.listdir` / `os.path.isdir`
Listing directory contents and checking existence before touching the filesystem.
- [`src/history.py:54,58`](src/history.py)

### `tomllib` (stdlib, Python 3.11+)
Parses TOML config files. Requires binary file mode (`"rb"`), unlike `json.load`.
- [`src/config.py:27-28`](src/config.py)

### `json.dump` / `json.load` / `json.loads`
Serializing Python dicts to JSON text (`dump`, to a file) and parsing JSON text back (`load`, from a file handle; `loads`, from a string already in memory).
- [`src/history.py:28`](src/history.py) — `json.dump` (write)
- [`src/history.py:46`](src/history.py) — `json.load` (read from file)
- [`src/api_client.py:44`](src/api_client.py) — `json.loads` (parse an SSE event's JSON text)

## Exception handling

### `try` / `except` / custom error messages
Catching a specific failure and re-raising with clearer context, rather than letting a cryptic low-level error surface.
- [`src/config.py:30-36`](src/config.py) — `KeyError` on a missing TOML section → `RuntimeError` with a readable message
- [`src/main.py:54-60`](src/main.py) — `FileNotFoundError` on `/load <bad-id>` → friendly "no conversation found" message
- [`src/main.py:68-75`](src/main.py) — `httpx.HTTPStatusError` / `TimeoutException` / `RequestError` around the streaming call → logged + printed, loop continues instead of crashing

### `raise ... from e`
Preserves the original exception as context (`__cause__`) while raising a new, more meaningful one.
- [`src/config.py:36`](src/config.py)

## Async fundamentals

### `async def` / coroutine functions
A function whose body can pause and resume around I/O. Calling it doesn't run the body — it returns a coroutine object that must be `await`ed (or scheduled as a task) to actually execute. Forgetting this was the single most common bug in this project — see [gotchas](#recurring-gotchas-worth-re-reading) below.
- [`src/history.py:14,32`](src/history.py), [`src/api_client.py:21`](src/api_client.py), [`src/main.py:19`](src/main.py)

### `await`
Pauses the current coroutine until the awaited call completes, yielding control back to the event loop in the meantime so other work can proceed.
- Throughout `main()`'s loop and both `history.py` functions.

### `asyncio.run(coro)`
The top-level entry point that creates an event loop and runs a coroutine to completion. Everything using `await` only works because something like this is running underneath it.
- [`src/main.py`](src/main.py) — bottom, `if __name__ == "__main__":` block

## Async I/O patterns

### `async with` (async context managers)
Same guarantee as `with`, but for objects whose setup/teardown is itself asynchronous (acquiring a lock without blocking the event loop, opening a network connection).
- [`src/history.py:18,36`](src/history.py) — `async with _save_lock:`
- [`src/api_client.py:34-35`](src/api_client.py) — `async with httpx.AsyncClient(...)`, `async with client.stream(...)`

### `asyncio.Lock`
Mutual exclusion for async code — ensures only one coroutine at a time enters the protected section, so two overlapping saves to the same file can't interleave and corrupt it.
- [`src/history.py:11`](src/history.py) — created once, at module level, shared across every call

### `asyncio.to_thread(func, *args)`
Runs a **blocking** (regular, synchronous) function in a background thread pool without stalling the event loop. Essential because `open()`/`json.dump()`/`json.load()` are blocking calls that would otherwise freeze the whole app while writing/reading a file.
- [`src/history.py:20,38`](src/history.py)

### Async generators (`async def` + `yield`)
A function that produces a *stream* of values over time instead of one return value — the caller drives it with `async for` and gets each value as it becomes available.
- [`src/api_client.py:21-46`](src/api_client.py) — `stream_reply` yields text chunks as they arrive from Groq

### `async for`
Iterating something that may need to `await` internally to produce each next item (as opposed to a plain `for` over data already sitting in memory).
- [`src/api_client.py:37`](src/api_client.py) — reading response lines as they stream in
- [`src/main.py:69`](src/main.py) — consuming `stream_reply`'s chunks

### `asyncio.create_task(coro)`
Schedules a coroutine to run **concurrently**, without waiting for it — "fire and forget." This is what lets autosave happen in the background while the user is already typing the next message.
- [`src/main.py:80`](src/main.py) — autosave scheduled after each successful turn

**Gotcha to remember:** a task needs a live reference kept somewhere, or it can be garbage-collected mid-flight before completing. `main.py` keeps `pending_save_task` in a variable across loop iterations specifically for this reason, and `await`s it before shutdown so the very last save isn't lost.

## Networking and streaming

### `httpx.AsyncClient` + `.stream(method, url, ...)`
An async HTTP client whose `.stream()` method opens a response you read incrementally, rather than downloading the whole body up front like a normal `.get()`/`.post()`.
- [`src/api_client.py:34-35`](src/api_client.py)

### Server-Sent Events (SSE) parsing
A plain-text streaming protocol: each event is a line prefixed `data: `, terminated by a literal `data: [DONE]` line. Common across most LLM provider streaming APIs, not just Groq.
- [`src/api_client.py:37-46`](src/api_client.py)

### `response.raise_for_status()`
Raises `httpx.HTTPStatusError` on a 4xx/5xx response (e.g. bad API key → 401) instead of silently continuing.
- [`src/api_client.py:36`](src/api_client.py)

## Logging and threading

### `logging` module basics — `Formatter`, `Handler`, `Logger`
Three separate responsibilities: what a log line looks like, where it goes, and what triggers it. Configuring handlers once on the *root* logger means every module can just call `logging.getLogger(__name__)` and inherit the setup.
- [`src/logging_setup.py`](src/logging_setup.py) — whole file

### `queue.Queue`
A thread-safe hand-off point between a fast producer (code calling `logger.info(...)`) and a slower consumer (the thread that actually writes to disk).
- [`src/logging_setup.py:17`](src/logging_setup.py)

### `logging.handlers.QueueHandler` / `QueueListener`
`QueueHandler` makes logging calls non-blocking (they just drop a record on the queue). `QueueListener` runs a **separate background thread** that drains the queue and does the real (blocking) file write.
- [`src/logging_setup.py:18,24-25`](src/logging_setup.py)

**Concept worth re-reading:** this is a genuinely different concurrency model from `asyncio` — a real OS thread, not a coroutine on the single-threaded event loop. Two different tools for two different problems (offloading blocking work vs. cooperatively waiting on I/O).

## CLI plumbing

### `argparse`
Declarative command-line argument parsing: `ArgumentParser`, `add_argument(...)`, `.parse_args()` returns a `Namespace` with one attribute per flag.
- [`src/main.py:12-17`](src/main.py) — `--config`, `--resume`

### `if __name__ == "__main__":`
Runs a block only when the file is executed directly, not when imported (e.g. by the test suite, which imports `main` as a module without triggering `asyncio.run(...)`).
- [`src/main.py`](src/main.py) — bottom of file

## Testing

### `pytest` fixtures — `tmp_path`, `monkeypatch`, `capsys`
`tmp_path` gives each test a throwaway directory; `monkeypatch` temporarily overrides env vars, `sys.argv`, `builtins.input`, or module attributes (auto-reverted after the test); `capsys` captures stdout/stderr for assertions.
- Used throughout `tests/*.py`

### `pytest-asyncio`
Lets `async def test_...` functions run directly as tests (`asyncio_mode = "auto"` in `pyproject.toml` means no extra decorator needed).
- `tests/test_history.py`, `tests/test_api_client.py`, `tests/test_main.py`, `tests/test_integration.py`

### `httpx.MockTransport`
Replaces the real network layer under `httpx.AsyncClient` with a fake handler function, so `stream_reply` can be tested against controlled fake SSE responses with zero real network calls.
- `tests/test_api_client.py`

### Custom pytest markers (`@pytest.mark.integration`)
Tags a test so it can be excluded from the default run (`addopts = "-m 'not integration'"` in `pyproject.toml`) and only run explicitly (`pytest -m integration`) — used for the one test that hits the real Groq API.
- `tests/test_integration.py`, registered in `pyproject.toml`

## Recurring gotchas worth re-reading

These specific mistakes came up more than once during development — worth a deliberate re-read before writing new async code:

1. **Calling an `async def` function without `await`** doesn't run it — it silently returns an unexecuted coroutine object (Python even warns: `RuntimeWarning: coroutine '...' was never awaited`). Happened with `load_conversation(...)` in `main.py` before the fix.
2. **Passing a function *reference* instead of *calling* it.** `asyncio.run(main)` vs `asyncio.run(main())`; `os.makedirs` (no parens — does nothing) vs `os.makedirs(path, exist_ok=True)`. Same root cause as #1: forgetting the `()`.
3. **Slicing vs. indexing.** `x[len(prefix):]` (slice, "everything after") vs `x[len(prefix)]` (index, one character). A single missing colon changes the meaning completely.
4. **`break`/`continue` placement inside nested loops.** A `continue` inside a `for` loop only affects that `for` loop, not an outer `while` — it does *not* skip code after the `for` loop the way you might expect.
5. **Every branch of a command dispatcher needs an explicit exit** (`break`/`continue`/`return`). Without one, execution falls through into whatever code comes next in the same block — which, in `main.py`, meant slash commands were briefly getting sent to Groq as chat messages.
