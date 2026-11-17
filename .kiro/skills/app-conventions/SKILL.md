---
name: "app-conventions"
description: "Load when reviewing non-test Python application code, meaning files outside tests/ and not named test_*.py or *_test.py. Covers naming, type hints, docstrings, and error handling."
---

# Application code conventions

## Rules

1. **Naming (PEP 8).** [MEDIUM] Classes use `CapWords`. Functions, methods, variables, and attributes use `snake_case`. Constants use `UPPER_SNAKE_CASE`. Module files use `snake_case`.
2. **Type hints.** [MEDIUM] Public functions and methods have type hints on parameters and return values.
3. **Docstrings.** [LOW] Public classes have a docstring. Functions have one when behavior is not obvious.
4. **Error handling.** [MEDIUM] Do not use bare `except:` or swallow exceptions silently. Catch specific exceptions and handle or re-raise them.
5. **Cleanliness.** [LOW] No dead code, commented-out code, leftover debug prints, or unused imports and variables.
6. **Mutable state.** [MEDIUM] No mutable class-level attributes (such as lists) shared between instances. Set them in `__init__`.

## Template

Compliant:

```python
class NotificationManager:
    """Schedules and cancels push notifications."""

    def __init__(self) -> None:
        self._pending: list[dict] = []

    def schedule_notification(self, title: str, body: str) -> None:
        self._pending.append({"title": title, "body": body})
```

Non-compliant:

```python
class notifications_manager:      # rule 1: class name
    pending = []                  # rule 6: shared mutable attribute

    def ScheduleNotification(self, Title, Body):   # rules 1, 2: naming, no type hints
        try:
            self.pending.append({"title": Title, "body": Body})
        except:                   # rule 4: bare except
            pass
```
