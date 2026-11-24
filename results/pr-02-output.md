# PR-02 review output

Repository: nebius-academy-templates/python-pr-review-practice, PR #2
Date: 2026-11-19
Sub-agents run: style-reviewer, security-reviewer, architecture-reviewer

### src/profile_service.py

- [MINOR] line 1: The public class `ProfileService` has no docstring. Add one (app-conventions, rule 3).
- [MAJOR] line 7: The method name `FetchProfile` is not `snake_case`. Rename it to `fetch_profile` (app-conventions, rule 1).
- [MAJOR] line 7: The method has no type hints on `user_id`, `tags` or the return value. For example: `def fetch_profile(self, user_id: str, tags: list[str] | None = None) -> Profile:` (app-conventions, rule 2).
- [MAJOR] line 7: The default argument `tags=[]` is mutable, and the method appends to it on line 8. The list is shared across calls, so one caller's tags leak into another's result. Use `tags: list[str] | None = None` and create a new list inside the method.
- [MINOR] line 7: The method has no docstring, and its behavior isn't obvious because it adds "fetched" to the caller's list (app-conventions, rule 3).
- [MAJOR] line 9: `Profile` is neither imported nor defined in the diff. Calling the method would raise `NameError`. Import it, or confirm where it comes from.
- [NIT] line 9: The file has no newline at the end. Add one.

## Summary

- **Findings:** 0 `[CRITICAL]`, 4 `[MAJOR]`, 2 `[MINOR]`, 1 `[NIT]`.
- **Most serious issues:** `src/profile_service.py`.
- **Assessment:** Needs fixes before merge.

The security and architecture reviewers found nothing. The style reviewer reported the naming, type hint and docstring findings. It noted the mutable default as a real bug that no skill rule covers. The mutable default, the undefined `Profile` and the newline `[NIT]` were added during consolidation from the diff. This run matches the earlier run of this review.

This review is advice for the human reviewer. It is not an approval or rejection of the PR. Nothing has been posted to GitHub.
