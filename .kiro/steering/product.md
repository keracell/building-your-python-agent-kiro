# Product

Release Notes Generator: an AI agent for a development team. It takes a list
of merged pull requests for a sprint and produces a **draft** of release notes
grouped by category. It never publishes a final version.

## Key rules (from AGENTS.md)

- Categories: Features, Fixes, Improvements.
- One sentence per entry, written from the user's perspective.
- Skip PRs tagged `chore`, `internal`, or `deps`.
- Use only the PR title when the description is missing. Never invent details.
- Ambiguous PRs go in Improvements with a note for the reviewer.
- Never publish externally without explicit user approval. Present the draft
  and ask for approval first.
- Empty PR list: stop and report "No merged PRs found".
- Stop after 2 drafting passes and note what is incomplete.
