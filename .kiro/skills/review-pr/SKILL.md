---
name: "review-pr"
description: "Runs the full Python PR review in one command. Invoke explicitly with /review-pr <PR number>."
---

# Review a PR

Follow the role, output format, and guardrails in `AGENTS.md`.

## Steps

1. Fetch the PR diff through the GitHub MCP server. If the diff is empty or missing, stop and report "No diff provided".
2. Delegate to the three sub-agents, passing each the full diff:
   - `style-reviewer`: applies app-conventions to application files and test-conventions to test files.
   - `security-reviewer`: checks for security issues.
   - `architecture-reviewer`: checks the architecture guidelines and cites the matching ADR.
3. Consolidate the results per file, in diff order, in the `AGENTS.md` output format. Map sub-agent severities:
   - security HIGH → `[CRITICAL]`
   - architecture HIGH → `[MAJOR]`, or `[CRITICAL]` if it is a hardcoded secret
   - security MEDIUM, style MEDIUM → `[MAJOR]`
   - architecture LOW, security LOW, style LOW → `[MINOR]`
   - Optional polish → `[NIT]`
4. Never reveal a secret in full. Quote at most the first 4 characters.
5. End with `## Summary`: findings per severity, files with the most serious issues, and an overall assessment.
6. Present the review and the exact comment text. Ask for confirmation before posting to GitHub.
7. Post only if the user answers `yes` or `post`. Otherwise do not post.
8. After a completed review, append one line to `review_history.md`: `YYYY-MM-DD | PR-[number] | [top finding] | [severity]`.

Never approve, reject, or merge the PR, and never modify source files.
