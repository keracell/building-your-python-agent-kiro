# Observability table

<!--
TODO: turn on the Post Tool Use log hook (.kiro/hooks/log-tool-calls.json), run
/review-pr 1 through /review-pr 5, then fill in this table from run-log.jsonl
(filter one run by its session_id) and answer the PR-03 diagnostic.
The slowest-tool column comes from tool-timings.jsonl, written by the tool-timer hooks
(.kiro/hooks/tool-timer-start.json and tool-timer-stop.json).
-->

| Input                          | Tools called (count)                                             | `security-reviewer` delegated?                         | Any tool error? | Slowest tool (name, ms)                          |
| ------------------------------ | ---------------------------------------------------------------- | ------------------------------------------------------ | --------------- | ------------------------------------------------ |
| PR-01 (clean)                  | 12 (log rows 40-51)                                              | Y (`invoke_sub_agent` `security-reviewer`, log row 44) | N               | `invoke_sub_agent`, 28,480 ms                    |
| PR-02 (style violations)       | 13 (log rows 53-65)                                              | Y (`invoke_sub_agent` `security-reviewer`, log row 58) | N               | `invoke_sub_agent`, 30,281 ms                    |
| PR-03 (hardcoded API key)      | 11 (log rows 67-77)                                              | Y (`invoke_sub_agent` `security-reviewer`, log row 69) | N               | `invoke_sub_agent`, 21,600 ms                    |
| PR-04 (architecture violation) | 26 in the shared PR-04 + PR-05 session (7 only PR-04, 13 shared) | Y (`invoke_sub_agent` `security-reviewer`, log row 7)  | N               | `invoke_sub_agent`, about 45,522 ms (see note 4) |
| PR-05 (mixed issues)           | 26 in the shared PR-04 + PR-05 session (6 only PR-05, 13 shared) | Y (`invoke_sub_agent` `security-reviewer`, log row 12) | N               | `invoke_sub_agent`, about 45,522 ms (see note 4) |

Source: `run-log.jsonl` and `tool-timings.jsonl`. Every row comes from session `sess_9dd36a5c-3345-4fd3-86bc-f0ffb13c55a2`.

Notes:

1. **Separating runs in one session.** All five reviews ran in the same session, so `session_id` alone can't tell them apart. PR-01, PR-02 and PR-03 were re-run one at a time with logging on. Each run sits between marker commands (`echo "OBS-MARKER PR-0N START"` / `END`), which are log rows 39, 52, 66 and 78. Counts exclude the markers. The timing windows use the same markers and contain the same number and mix of calls as the log windows (12, 13 and 11).
2. **What the counts include.** The PostToolUse hook also logs the sub-agents' own calls. Each run has 6 calls by the main agent:
   - 1 `mcp_github_pull_request_read`, which fetched the live diff through the GitHub MCP server
   - 3 `invoke_sub_agent`, one each for the security, style and architecture reviewers
   - 1 `fs_write` to `results/pr-0N-output.md`
   - 1 `fs_append` to `review_history.md`

   The remaining calls came from inside the sub-agents:
   - **PR-01 (6):** 3 `disclose_context` skill loads, 1 ADR `read_file` and 2 `subagent_response`.
   - **PR-02 (7):** 2 `disclose_context`, 1 `list_directory` of `docs/adr/`, 2 ADR `read_file` and 2 `subagent_response`.
   - **PR-03 (5):** 2 `disclose_context`, 1 ADR `read_file` (ADR-002) and 2 `subagent_response`.

3. **Errors.** No `tool_response` in the PR-01 to PR-03 windows reports an error. A text search for error words found only the heading "Error handling", inside the `app-conventions` skill text that `disclose_context` returned. That is skill content, not a failure.
4. **Slowest tool.** In every run the slowest call was an `invoke_sub_agent`. The timer hook records no call id, and the three sub-agents run in parallel, so the timer can't say which reviewer took longest. The figure is the slowest single call in each PR's window. For PR-04 and PR-05, which ran together, the 45,522 ms is the slowest call in the shared window, so treat it as approximate per PR.
5. **PR-04 and PR-05 counts.** The 26 logged calls were:
   - 2 `mcp_github_pull_request_read`
   - 6 `invoke_sub_agent` (the three reviewers for each PR)
   - 6 `disclose_context`
   - 3 `read_file`
   - 2 `list_directory`
   - 4 `fs_write`
   - 1 `fs_append`
   - 1 `subagent_response`
   - 1 `execute_pwsh`

   Calls are split by PR only where the tool input names the PR. The skill, ADR and directory reads were shared.

## Diagnostic question

The question asks whether the hardcoded-credential finding for PR-03 was produced, and if not, which failure mode caused it.

**Yes, the finding was produced, by `security-reviewer`. No failure mode applies.**

Evidence:

- **Sub-agent called:** yes. Log row 69 is `invoke_sub_agent` with `name: security-reviewer` in the PR-03 window. This matches the "Y" in the PR-03 row.
- **Right input:** yes. Log row 67 is the live diff from `mcp_github_pull_request_read` for PR 3. The sub-agent got that diff with the key on line 4 redacted to its first 4 characters. The line, the attribute and the `sk-l` prefix were all kept.
- **Tool fired:** yes. Row 69 has a non-empty `tool_response` of 653 characters and no error.
- **Prompt sufficient:** yes. The response begins `[HIGH] line 4 — Hardcoded API key in the class attribute API_KEY (starts with sk-l)` and tells the author to rotate the key and load it from the config layer.

`architecture-reviewer` also reported line 4 as HIGH under ADR-002, in log row 74. The `style-reviewer` did not flag it, which is correct, because it is not a style rule. The consolidated review maps security HIGH to `[CRITICAL]`. It appears as the `[CRITICAL] line 4` finding in `results/pr-03-output.md` and in `results/test-session-4.md`. None of the four failure modes happened: the sub-agent was called, its input was right, the tool fired, and the prompt produced the finding.
