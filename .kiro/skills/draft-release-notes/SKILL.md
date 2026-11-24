---
name: "draft-release-notes"
description: "Draft release notes for the app from its pull requests. Invoke with /draft-release-notes <version> when you want to produce release notes."
---

# Draft release notes

## Steps

1. Fetch the pull requests from the repository using the GitHub MCP server.
2. Apply the `pr-label-format` skill to categorize each PR.
3. Delegate description cleanup to the `ticket-fetcher` subagent. Pass the PR
   numbers, titles, and descriptions as the task prompt. Receive the cleaned
   list.
4. Delegate categorization to the `categorizer` subagent. Pass
   `ticket-fetcher`'s output as the task prompt. Receive the sorted Markdown.
5. Group PRs into Features, Fixes, and Improvements.
6. Draft each entry as a single user-facing sentence. Do not invent details,
   use only what's in the PR title or description.
7. Present the complete draft to the user with the version number
   `$ARGUMENTS`. Ask: "Review complete. Approve to publish, or reply with
   edits."
8. After every completed review, append one line to `review_history.md`.
   Use this format:

```text
- Date: <year-month-day>
- PR: <PR number and title>
- Top finding: <short description>
- Severity: <severity>
```

## Rules

Before drafting the Features section, read `docs/product-glossary.md`.

If a PR title or description matches a term in the `Search term` column, use
the corresponding value from the `Release notes name` column in the output
instead of the original wording.
