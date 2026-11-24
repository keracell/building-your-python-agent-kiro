# Log Triage server

An MCP server that lets an AI agent investigate a folder of logs. This stage is the skeleton: the server starts over stdio with its name, version and instructions, and registers no tools yet.

## Install
Run from the repository root. You need Python 3.13 and uv.

```bash
uv sync --project solution
```

## Run
```bash
uv run --project solution log-triage --root s3_logs
```

The server speaks MCP over stdin and stdout, so it prints nothing and waits for input. Stop it with Ctrl+C. Diagnostics go to stderr.

| Flag | Meaning | Default |
|---|---|---|
| `--root DIR` | The log root. Required | none |
| `--reports DIR` | Where findings will be written | `reports` in the working directory |
| `--read-only` | Do not register the write tool | off |
| `--scan-ttl SECONDS` | How long a `scan_id` from `summarize_logs` works, 1 or more | `900` |
| `--log-level LEVEL` | The server's own logging threshold: `debug`, `info`, `warning` or `error`. Log lines go to stderr; at `debug` every tool call writes one `tool=<name>` line | `warning` |

If `--root` is missing or not a readable folder, the server prints `log root "<DIR>" is not a readable folder` on stderr and exits with code 2.

## Check
```bash
uv run --project 1-surface-and-contract/checks pytest 1-surface-and-contract/checks
```
At this stage `test_t2_server.py` passes and the later files still fail.

## Test
The server's own tests live in `solution/tests/`. `uv sync --project solution` installs the dev group (pytest and pytest-asyncio).

```bash
uv run --project solution pytest solution/tests
```

One layer at a time:

```bash
uv run --project solution pytest solution/tests/unit
```

The unit tests call the reader and the grouping rules directly, on small hand-built files, with no MCP in between.

## Probe
`scripts/probe.py` is a scripted client that behaves like a careless host. It starts the server over stdio (with `--scan-ttl 1` and a temporary reports folder), sends five requests on one session and prints one line per step. It exits 0 only when every step got the answer `3-testing-and-debugging/probe-expected.md` names, and 1 otherwise.

```bash
uv run --project solution python solution/scripts/probe.py --root s3_logs
```
