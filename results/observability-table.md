# Observability table

<!--
TODO: turn on the Post Tool Use log hook (.kiro/hooks/log-tool-calls.json), run
/review-pr 1 through /review-pr 5, then fill in this table from run-log.jsonl
(filter one run by its session_id) and answer the PR-03 diagnostic.
The slowest-tool column comes from tool-timings.jsonl, written by the tool-timer hooks
(.kiro/hooks/tool-timer-start.json and tool-timer-stop.json).
-->

| Input                          | Tools called (count) | `security-reviewer` delegated? | Any tool error? | Slowest tool (name, ms) |
| ------------------------------ | -------------------- | ------------------------------ | --------------- | ----------------------- |
| PR-01 (clean)                  | Not captured (no run-log entries) | Not captured | Not captured | Not captured |
| PR-02 (style violations)       | Not captured (no run-log entries) | Not captured | Not captured | Not captured |
| PR-03 (hardcoded API key)      | Not captured (no run-log entries) | Not captured | Not captured | Not captured |
| PR-04 (architecture violation) | 26 in the shared PR-04 + PR-05 session (7 only PR-04, 13 shared) | Y (`invoke_sub_agent` `security-reviewer`, log row 7) | N | `invoke_sub_agent`, about 45,522 ms (see note 3) |
| PR-05 (mixed issues)           | 26 in the shared PR-04 + PR-05 session (6 only PR-05, 13 shared) | Y (`invoke_sub_agent` `security-reviewer`, log row 12) | N | `invoke_sub_agent`, about 45,522 ms (see note 3) |

Source: `run-log.jsonl` (26 PostToolUse events, all from session `sess_9dd36a5c-3345-4fd3-86bc-f0ffb13c55a2`) and `tool-timings.jsonl`.

Notes:

1. **Coverage.** `run-log.jsonl` only started logging after the hook fix, so it holds one session. That session reviewed PR-04 and PR-05 together. PR-01 to PR-03 were run before logging worked, so they are marked "Not captured" and not estimated. Re-run `/review-pr 1`, `2` and `3` to fill those rows.
2. **Counts.** The 26 logged calls are 2 `mcp_github_pull_request_read`, 6 `invoke_sub_agent` (security, style and architecture reviewers for each PR), 6 `disclose_context`, 3 `read_file`, 2 `list_directory`, 4 `fs_write`, 1 `fs_append`, 1 `subagent_response` and 1 `execute_pwsh`. The PR-04 and PR-05 diffs were fetched through the GitHub MCP server. Calls are split by PR only where the tool input names the PR. The skill, ADR and directory reads were shared.
3. **Slowest tool.** The timer hook records no call id, so parallel `invoke_sub_agent` calls can swap durations. The 45,522 ms figure is the slowest call in the whole session window, at about 13:45:21 UTC. By timing order it matches log row 19, the PR-05 `architecture-reviewer` call. The slowest single call for PR-04 alone can't be isolated, so treat the per-PR column as approximate.
4. **Errors.** No `tool_response` in the log contains an error. The final `execute_pwsh` check printed `apply-check exit: 0` for both sample diffs.

## Diagnostic question

The diagnostic question asks why the hardcoded-credential finding for PR-03 was or was not produced.

**PR-03 is not in the log, so I can't answer it from evidence.** `run-log.jsonl` has no PR-03 session, because that review ran before the hook was fixed. I will not infer the answer.

What the log does show, from the nearest equivalent case, PR-05 (a hardcoded `CLIENT_SECRET`):

- `security-reviewer` was delegated (log row 12). The prompt told it that line 3 holds a live secret, redacted after the first 4 characters.
- It returned `[HIGH] line 3: A hardcoded client secret (sk-l...)`. The `architecture-reviewer` (row 19) also returned a HIGH finding on the same line, so two sub-agents produced the finding independently.
- The consolidated review mapped it to `[CRITICAL]`, which is the expected path through `review-pr` step 3.

This suggests the pipeline does produce the credential finding when a diff has one. It is not proof for PR-03. To close this, re-run `/review-pr 3` with logging on and check that row for the `security-reviewer` call and its response.
