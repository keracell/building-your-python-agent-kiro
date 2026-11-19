# PR-04 review output

Repository: nebius-academy-templates/python-pr-review-practice, PR #4
Date: 2026-11-19
Sub-agents run: style-reviewer, security-reviewer, architecture-reviewer

### src/trip_service.py

- [MINOR] line 1: The public class `TripService` has no docstring. Add one (app-conventions, rule 3).
- [MAJOR] line 2: `__init__` has no type hints on `api_client` or the return value (app-conventions, rule 2).
- [MAJOR] line 5: `load_trips` has no type hints on `user_id` or the return value (app-conventions, rule 2).
- [MAJOR] line 7: `load_trips` calls `self.api_client.get(...)` directly, so the service bypasses the repository layer. Add a `TripRepository` in the data layer that wraps `ApiClient` and exposes `get_trips(user_id)`, and inject it in place of `api_client` on line 2 (ADR-003).
- [MINOR] line 7: `user_id` goes into the request path (`f"/users/{user_id}/trips"`) without validation. If it can ever come from user input, a value containing `/`, `?` or `#` could reach a different endpoint. Validate it as an integer or URL-encode it.
- [NIT] line 7: The file has no newline at the end. Add one.

### tests/test_trip_service.py

- [MINOR] line 7: The name `test_1` doesn't describe the behavior. Use something like `test_load_trips_returns_trips_for_user` (test-conventions, rule 1).
- [MAJOR] line 8: The test builds a real `ApiClient()`, so it makes a real network call. Inject a mock or fake through a fixture. Once the service takes a repository, inject a fake repository instead (test-conventions, rule 3; ADR-003).
- [MAJOR] line 10: `assert result is not None` doesn't check what `load_trips` returns. With a mock, assert that the result equals the mocked trips and that the call used `/users/42/trips` (test-conventions, rule 5).
- [NIT] line 10: The file has no newline at the end. Add one.

## Summary

- **Findings:** 0 `[CRITICAL]`, 5 `[MAJOR]`, 3 `[MINOR]`, 2 `[NIT]`.
- **Most serious issues:** `src/trip_service.py`.
- **Assessment:** Needs fixes before merge.

The architecture reviewer reported the repository bypass as HIGH, mapped to `[MAJOR]`. It cited line 6, the comment above the call. The finding is listed at line 7, where the call is. The style reviewer reported the type hints, the real API client and the weak assertion as MEDIUM, and the docstring and test name as LOW. The security reviewer rated the unvalidated `user_id` MEDIUM. It is listed as `[MINOR]` because the diff shows no user input reaching it. The two newline `[NIT]`s were added during consolidation from the diff.

Changes from the previous run of this review: the weak assertion on test line 10 is new. The architecture reviewer reported the constructor dependency and the direct call as one finding instead of two, so they are merged at line 7.

This review is advice for the human reviewer. It is not an approval or rejection of the PR. Nothing has been posted to GitHub.
