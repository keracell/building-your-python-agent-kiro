# Tech

## Stack
- No source code, build system, or dependencies yet. The repo is currently an agent specification.
- Behavior is defined in `AGENTS.md` (role, rules, output format, guardrails). Treat it as the source of truth.
- Input: list of merged PRs (title, description, tags). Output: Markdown document.

## Output format
- Three H2 sections: `## Features`, `## Fixes`, `## Improvements`.
- Each entry is a single bullet: `- <user-facing text>`.
- Optional trailing `## Review notes` for flagged entries.
- No PR numbers, author names, or internal ticket IDs.

## Commands
None defined. Add build, test, and run commands here when code is introduced.
