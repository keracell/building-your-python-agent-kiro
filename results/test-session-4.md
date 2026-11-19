# Test session 4

Real run from the Kiro session of 2026-11-19. Agent responses are quoted from
the session. Long passages are shortened where marked `[…]`. The secret is
shown only as its first 4 characters, as the guardrail requires.

## /review-pr 3: all three sub-agents and the high-severity security finding

**User:**

```text
/review-pr 3
```

**Agent tool calls, in order:**

1. `github::pull_request_read` with `method: get_diff`, repository
   `nebius-academy-templates/python-pr-review-practice`, PR 3. It returned one
   new file, `src/payment_service.py` (11 lines).
2. Three sub-agents, run in parallel. Each got the diff with the key on line 4
   redacted to `sk-l[REDACTED]`:
   - `security-reviewer`
   - `architecture-reviewer`
   - `style-reviewer`
3. `fs_append` to `review_history.md`.
4. `fs_write` to `results/pr-03-output.md`.
5. `execute_pwsh` to confirm the file exists and the full key is in neither
   file. Result: `full key in output file: False`.

**Sub-agent results:**

- `security-reviewer`:

  > [HIGH] line 4 — Hardcoded API key in `API_KEY = "sk-l…"` (first 4
  > characters shown; the rest is withheld). […] Revoke and rotate it now,
  > because it is exposed in the diff. Then load it from the environment or a
  > secrets manager. […]
  >
  > Summary: 1 HIGH, 0 MEDIUM, 0 LOW.

- `architecture-reviewer`:

  > [HIGH] line 4 — Hardcoded API key `sk-l…` is stored as the class attribute
  > `API_KEY`. […] Guideline: Configuration (ADR-002). […] I found no
  > violations of ADR-001, ADR-003 or ADR-004.

- `style-reviewer`:

  > No issues found. […] Line 4 is a hardcoded secret. That is a security and
  > configuration finding (ADR-002) for the security and architecture
  > reviewers, so it is not listed here.

**Agent (consolidated review):**

> ### src/payment_service.py
>
> - [CRITICAL] line 4: A live API key is hardcoded as the class attribute
>   `API_KEY = "sk-l…"`. I show only the first 4 characters. The key is in
>   source control and in the PR diff.
>   - Revoke the key and issue a new one.
>   - Delete the literal. Load the key in the config layer from an
>     environment variable or a secrets manager (ADR-002).
>   - Pass it in through a constructor instead of a class attribute (ADR-004).
>   - […]
> - [NIT] line 11: The file has no newline at the end. Add one.
>
> ## Summary
>
> - **Findings:** 1 `[CRITICAL]`, 0 `[MAJOR]`, 0 `[MINOR]`, 1 `[NIT]`.
> - **Most serious issues:** `src/payment_service.py`.
> - **Assessment:** Needs fixes before merge. Rotate the key now.
>
> All three reviewers ran:
>
> - The security and architecture reviewers both rated the key HIGH. I
>   combined their two reports into the one `[CRITICAL]` finding.
> - The style reviewer found nothing.
>   […]
>
> Do you want me to post it? Reply `yes` or `post`, or I won't post anything.

**Outcome:** all three sub-agents ran. The security reviewer's HIGH finding
became the `[CRITICAL]` finding in the consolidated review. No reviewer saw the
key in full, and no output file contains it. The user never answered the
posting question, so nothing was posted to GitHub.
