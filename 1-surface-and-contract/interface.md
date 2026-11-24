# Interface worksheet

**Related**:

> [CONTRACT](CONTRACT.md): The surface to compare your answers with, after you fill this in
> [README](README.md): Task 1 asks for this worksheet

Design the server from the questions people will ask it, before you write any code. For each question below, decide how the server should offer the answer, then fill in the row. Fill it in before you open `CONTRACT.md`. Afterwards, compare your rows with the contract and note where you differ and why. Nothing here is graded.

## Links
**Internal**:

- `1-surface-and-contract/CONTRACT.md`
- `docs/log-formats.md`

## How to fill it in
| Column | Write |
|---|---|
| Primitive | `tool`, `resource` or `prompt` |
| Name | The name you'd give it |
| Who decides to use it | `model` (the agent picks it while it works), `application` (the host fetches it for context) or `user` (a person picks it from a menu) |
| Read or write | `read` if it only looks, `write` if it changes something |

## The questions
| # | Question | Primitive | Name | Who decides to use it | Read or write |
|---|---|---|---|---|---|
| 1 | Which log files are there under this folder, and what format is each one? | tool | `list_logs` | model | read |
| 2 | What went wrong in this file or folder during this time window? | tool | `summarize_logs` | model | read |
| 3 | Which lines match this pattern? | tool | `search_logs` | model | read |
| 4 | Record what I concluded, with the evidence for it. | tool | `save_finding` | model | write |

## Your notes
Where your design differs from `CONTRACT.md`, and why:

- **The four rows match the contract.** Primitive (tool), name, who decides (model) and read or write are the same for all four. The contract publishes exactly four tools, with no resources and no prompts. I did not change the table above.
- **The table leaves out what the contract specifies in detail.** It has no columns for these, so none of this counts as a disagreement, but each one is a design decision I had not made:
  - **Paging and bounds:** `list_logs` and `search_logs` take `limit` (up to 500 and 200) and `offset`. Every list reports `total`, `shown` and a `note` that says how to get the next page. `summarize_logs` takes only `limit` (up to 100). The model should never get an unbounded answer.
  - **Annotations:** the three read tools are `readOnlyHint: true`. `save_finding` is `readOnlyHint: false` and `destructiveHint: true`, because the same title overwrites the earlier report. All four set `openWorldHint: false`.
  - **Read-only mode:** `--read-only` does not refuse `save_finding` calls. It leaves the tool unregistered, so the model never sees it.
  - **Structured output:** every tool publishes an output schema and returns structured content plus one text block holding the same JSON.
  - **Server instructions:** the server carries a fixed instruction text (at most 512 characters) that tells the model to start with `list_logs`.
  - **Log root:** every `path` is resolved under `--root`, and a path outside it is refused with a tool error.
- **Filters on two tools.** The contract puts `since`, `until` and `min_level` on both `summarize_logs` and `search_logs`. My table doesn't say which tools filter. It makes sense, because the model often knows the time window before it knows the pattern.

Reasoning behind the design:

- All four are tools because the model decides when to call each one while it investigates. Resources suit context a host loads on its own, and prompts suit workflows a person picks from a menu. Nothing here fits those.
- Questions 1 to 3 only look at the logs, so they are read tools. Splitting discovery, summary and search keeps each decision separate: what exists, what happened, and which lines are the evidence.
- Question 4 is the only one that changes anything, because it writes a report. It is the one tool that should be removable (read-only mode) and should advertise that it writes and can overwrite.
- Caveat: I had read the README's "MCP surface" section before writing this, so it is not a fully blind design.
