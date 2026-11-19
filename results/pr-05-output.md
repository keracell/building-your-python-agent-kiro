# PR-05 review output

Repository: nebius-academy-templates/python-pr-review-practice, PR #5
Date: 2026-11-19
Sub-agents run: style-reviewer, security-reviewer, architecture-reviewer

### src/checkout_service.py

- [MINOR] line 1: The public class `CheckoutService` has no docstring. Add one (app-conventions, rule 3).
- [CRITICAL] line 3: A live secret is hardcoded as `CLIENT_SECRET = "sk-l…"` (first 4 characters shown). It is committed to source control and is now in the PR diff. Revoke and rotate it, whatever happens to this PR. Remove the literal and load it in the config layer from an environment variable or a secrets manager (ADR-002).
- [MAJOR] line 5: `__init__` has no type hints on `api_client` or the return value (app-conventions, rule 2).
- [MAJOR] line 10: The method name `SubmitOrder` is not `snake_case`. Rename it to `submit_order` (app-conventions, rule 1).
- [MAJOR] line 10: The method has no type hints, for example `order_id: int` and `-> None` (app-conventions, rule 2).
- [MINOR] line 10: The method has no docstring, and the comment on lines 8-9 shows its behavior isn't obvious. Replace the comment with a docstring (app-conventions, rule 3).
- [MAJOR] line 11: `SubmitOrder` calls `self.api_client.post(...)` directly, so the service bypasses the repository layer. Add an orders repository that wraps `ApiClient` and exposes `submit(order_id)`, and inject it in place of `api_client` on line 5 (ADR-003).
- [MAJOR] line 12: The service sends the secret itself, in the request body as `{"secret": ...}`. The repository or API client should own the credential and send it in an `Authorization` header, so the service never handles it and it doesn't end up in request-body logs (ADR-002).
- [MINOR] line 12: `order_id` goes into the request path without validation. If it can ever come from user input, a value containing `/` or `..` could change the path. Validate it as an integer or URL-encode it.
- [NIT] line 13: The file has no newline at the end. Add one.

### tests/test_checkout_service.py

- [MINOR] line 6: The name `test_checkout` doesn't describe the behavior. Use something like `test_submit_order_posts_to_order_endpoint` (test-conventions, rule 1).
- [MAJOR] line 7: The test builds a real `ApiClient()`, so running it makes a real network call and sends the hardcoded live secret to the real API. Inject a mock through a pytest fixture (test-conventions, rule 3).
- [MAJOR] line 8: The test has no assertion. Assert on observable behavior, for example `post.assert_called_once_with(...)` on the mock (test-conventions, rule 5).
- [NIT] line 8: The file has no newline at the end. Add one.

## Summary

- **Findings:** 1 `[CRITICAL]`, 7 `[MAJOR]`, 4 `[MINOR]`, 2 `[NIT]`.
- **Most serious issues:** `src/checkout_service.py`.
- **Assessment:** Needs fixes before merge. Rotate the secret now.

The security and architecture reviewers both reported the hardcoded secret as HIGH. It is merged here into one `[CRITICAL]` finding. The architecture reviewer reported the repository bypass as HIGH, mapped to `[MAJOR]`. On line 12, the architecture reviewer rated the secret in the request body HIGH and the security reviewer rated it LOW. They are merged at the higher rating, `[MAJOR]`. The security reviewer's LOW finding about the test sending the live secret is merged into the test's line 7 finding. The security reviewer rated the unvalidated `order_id` MEDIUM. It is listed as `[MINOR]` because the diff shows no user input reaching it, the same call as for `user_id` in PR-04. The two newline `[NIT]`s were added during consolidation from the diff.

Changes from the previous run of this review: the method docstring on line 10 is new. The secret in the request body on line 12 rose from `[MINOR]` to `[MAJOR]`, because the architecture reviewer now reports it as an ADR-002 violation.

This review is advice for the human reviewer. It is not an approval or rejection of the PR. Nothing has been posted to GitHub.
