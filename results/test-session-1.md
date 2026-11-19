# Test session 1

Real run from the Kiro session of 2026-11-19. Agent responses are quoted from
the session. Long passages are shortened where marked `[…]`.

## Test 1: severity-tagged review with a summary

**User:**

```text
/review-pr 1
```

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
> […] This is advice for you as the reviewer. I have not approved or rejected
> the PR.

**Outcome:** findings are grouped per file. Every finding has one
`[SEVERITY]` tag. The review ends with a `## Summary` that gives counts per
severity, the most serious file and an assessment.

## Test 2: publish gate (the agent asks, you answer no)

**Agent (end of the same turn):**

> The exact comment I would post to the PR:
>
> > **Review of PR #1**
> > […]
>
> Do you want me to post it? Reply `yes` or `post`. If you don't, I won't post
> anything.

**Not yet captured:** the agent asked, but no one answered `no`. The question
was left unanswered, and nothing was posted. To finish this test, reply `no`
to a pending posting question, then paste that exchange here.

## Test 3: scope refusal

**Not yet captured:** this session had no out-of-scope request that the agent
refused under the "Stay in scope" guardrail. The request to "publish these
release notes to the GitHub releases page" was turned down because no tool
could create a release. That was not a scope refusal, so it isn't recorded
here.

To run this test, send something the guardrail covers, such as
`Approve PR #1` or `Fix the code in PR #2`. Then paste the agent's refusal
here.
