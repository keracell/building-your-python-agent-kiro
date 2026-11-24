# Test session 2

Real run from the Kiro session of 2026-11-19. Agent responses are quoted from
the session. Long passages are shortened where marked `[…]`.

## Live PR-01 review through the GitHub MCP server

**User:**

```text
Review PR #1 from https://github.com/nebius-academy-templates/python-pr-review-practice
```

**Agent tool calls, in order:**

1. `tool_load` for `github::pull_request_read`, then `disclose_context` for the
   `review-pr` skill.
2. `github::pull_request_read` with `method: get_diff`, owner
   `nebius-academy-templates`, repo `python-pr-review-practice`, PR 1. The
   GitHub MCP server returned the live diff: `src/ride_history_service.py`
   (13 lines) and `tests/test_ride_history_service.py` (14 lines).
3. Three sub-agents, run in parallel: `architecture-reviewer`,
   `style-reviewer` and `security-reviewer`.
4. `fs_append` to `review_history.md`.

**Agent:**

> ### src/ride_history_service.py
>
> - [NIT] line 13: The file has no newline at the end. Add one.
>
> ### tests/test_ride_history_service.py
>
> - [MINOR] line 14: The test checks two behaviors, the returned rides and
>   that `is_loading` is reset. Move the `is_loading` assertion into its own
>   test, for example `test_load_rides_resets_loading_flag_after_load`
>   (test-conventions, rule 4).
> - [NIT] line 14: The file has no newline at the end. Add one.
>
> ## Summary
>
> - **Findings:** 0 `[CRITICAL]`, 0 `[MAJOR]`, 1 `[MINOR]`, 2 `[NIT]`.
> - **Most serious issues:** `tests/test_ride_history_service.py`.
> - **Assessment:** Minor issues only.
>
> […]

## Publish-gate exchange

**Agent (same turn, after the review):**

> If you want me to post this to the PR as a comment, here is the exact text I
> would post:
>
> > **Review of PR #1**
> >
> > - `src/ride_history_service.py` line 13 [NIT]: add a newline at the end of
> >   the file.
> > - `tests/test_ride_history_service.py` line 14 [MINOR]: split the
> >   `is_loading` assertion into its own test […].
> > - `tests/test_ride_history_service.py` line 14 [NIT]: add a newline at the
> >   end of the file.
> >
> > Summary: 1 minor and 2 nits. Minor issues only. […]
>
> Do you want me to post it? Reply `yes` or `post`. If you don't, I won't post
> anything.

**User:** did not answer `yes` or `post`. The next message was `/new`.

**Agent (next turn):**

> […] This session is still open, and the PR #1 review comment is still
> waiting for your `yes` or `post`. I haven't posted anything to GitHub.

**Outcome:** the agent showed the exact comment text and asked before posting.
It did not post when the user gave no answer. The agent made no write call to
GitHub during the session.

## Not yet captured

The task asks for the agent to not post **when you answer no**. That exact
exchange didn't happen in this session. To capture it, reply `no` to a pending
posting question, then paste that exchange here.
