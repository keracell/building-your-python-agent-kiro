# PR-03 review output

Repository: nebius-academy-templates/python-pr-review-practice, PR #3
Date: 2026-11-19
Sub-agents run: style-reviewer, security-reviewer, architecture-reviewer

### src/payment_service.py

- [CRITICAL] line 4: A live API key is hardcoded as the class attribute `API_KEY = "sk-l…"` (first 4 characters shown). It is committed to source control and is now in the PR diff. Revoke and rotate the key, whatever happens to this PR. Remove the literal and load the key in the config layer from an environment variable or a secrets manager (ADR-002). Inject it through a constructor instead of a class attribute (ADR-004). The cleanest fix gives the key to the repository or API client when it is built, so `PaymentService` never handles it and line 11 no longer passes `api_key=`.
- [NIT] line 11: The file has no newline at the end. Add one.

## Summary

- **Findings:** 1 `[CRITICAL]`, 0 `[MAJOR]`, 0 `[MINOR]`, 1 `[NIT]`.
- **Most serious issues:** `src/payment_service.py`.
- **Assessment:** Needs fixes before merge. Rotate the key now.

The security reviewer reported the hardcoded key as HIGH, which maps to `[CRITICAL]`. The architecture reviewer reported the same line as HIGH under ADR-002. The two are merged into one finding. The style reviewer found nothing. The newline `[NIT]` was added during consolidation from the diff. Apart from the key, the service follows the repository pattern (ADR-003) and constructor injection (ADR-004). This run matches the earlier run of this review.

This review is advice for the human reviewer. It is not an approval or rejection of the PR. Nothing has been posted to GitHub.
