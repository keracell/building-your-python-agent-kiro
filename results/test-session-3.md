# Test session 3

Real runs from the Kiro session of 2026-11-19. Agent responses are quoted from
the session. Long passages are shortened where marked `[…]`.

## Skill loading per file type

The `style-reviewer` sub-agent preloads both `app-conventions` and
`test-conventions` through its `resources` field. So both skills load on
every run, and the reviewer then picks which skill's rules apply to each file.
The runs below show which rules were applied. They do not show which skills
loaded.

### PR-02: a PR that only touches application files

The diff from the GitHub MCP server had one file, `src/profile_service.py`.
The `style-reviewer` cited only `app-conventions` rules:

> - [LOW] line 1: Public class `ProfileService` has no docstring. Rule
>   broken: app-conventions, rule 3.
> - [MEDIUM] line 7: Method `FetchProfile` is not `snake_case`. Rename it to
>   `fetch_profile`. Rule broken: app-conventions, rule 1.
> - [MEDIUM] line 7: Public method `FetchProfile` has no type hints […]. Rule
>   broken: app-conventions, rule 2.
> - [LOW] line 7: The method has no docstring […]. Rule broken:
>   app-conventions, rule 3.

None of its findings cited `test-conventions`.

### PR-01: the test file reviewed with test conventions

The diff had `src/ride_history_service.py` and
`tests/test_ride_history_service.py`. The `style-reviewer` found nothing in
the application file. In the test file it cited a `test-conventions` rule:

> ### src/ride_history_service.py
>
> No issues found.
>
> ### tests/test_ride_history_service.py
>
> - [LOW] line 14: The test asserts two behaviors […]. — One behavior per
>   test (test-conventions, rule 4).

## /review-pr run that pauses before posting

**User:**

```text
/review-pr 2
```

**Agent tool calls, in order:**

1. `github::pull_request_read` with `method: get_diff`, PR 2.
2. Three sub-agents, run in parallel: `style-reviewer`, `security-reviewer`
   and `architecture-reviewer`.
3. `fs_append` to `review_history.md`.

No GitHub write call was made.

**Agent (end of the turn):**

> ## Summary
>
> - **Findings:** 0 `[CRITICAL]`, 4 `[MAJOR]`, 2 `[MINOR]`, 1 `[NIT]`.
> - **Most serious issues:** `src/profile_service.py`.
> - **Assessment:** Needs fixes before merge.
>
> […]
>
> The exact comment I would post to the PR:
>
> > **Review of PR #2**
> >
> > - `src/profile_service.py` line 1 [MINOR]: add a class docstring.
> > - line 7 [MAJOR]: rename `FetchProfile` to `fetch_profile`.
> >   […]
> >   Summary: 4 major, 2 minor and 1 nit. Needs fixes before merge.
>
> Do you want me to post it? Reply `yes` or `post`. If you don't, I won't post
> anything.

**Outcome:** the workflow stopped at step 6 of `review-pr` and waited for
confirmation. Nothing was posted.

## Not yet captured

This session never loaded `app-conventions` or `test-conventions` alone,
because the `style-reviewer` preloads both. To show true selective loading,
choose one of these:

- **Ask for a direct review:** ask the main agent, without `/review-pr`, to
  review an app-only diff such as `samples/pr-02-style.diff`. Record which
  skill it loads with `disclose_context`.
- **Change the reviewer:** remove the `resources` preload from
  `style-reviewer.md`, so the reviewer loads each skill only when it needs
  it.
