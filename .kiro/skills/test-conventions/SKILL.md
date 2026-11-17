---
name: "test-conventions"
description: "Load when reviewing Python test code: files under tests/, files named test_*.py or *_test.py, or files that import pytest. Covers test naming, fixtures, and isolation."
---

# Test code conventions

## Rules

1. **Naming.** [LOW] Test files are `test_<module>.py`. Test functions are `test_<behavior>_<expected result>` and describe behavior, not implementation.
2. **Fixtures.** [MEDIUM] Shared setup goes in pytest fixtures, not copy-pasted across tests or run at import time.
3. **Isolation.** [MEDIUM] Tests do not depend on execution order, shared mutable state, real network calls, or real files. Use mocks or fakes for repositories and clients.
4. **One behavior per test.** [LOW] Each test checks one behavior, using the arrange, act, assert structure.
5. **Assertions.** [MEDIUM] Every test has at least one assertion on observable behavior.

## Template

Compliant:

```python
import pytest
from unittest.mock import Mock

from src.ride_history_service import RideHistoryService


@pytest.fixture
def ride_repository() -> Mock:
    return Mock()


def test_load_rides_returns_recent_rides_from_repository(ride_repository: Mock) -> None:
    ride_repository.recent_rides.return_value = ["ride-1"]
    service = RideHistoryService(ride_repository)

    assert service.load_rides() == ["ride-1"]
```

Non-compliant:

```python
import requests

results = []                       # rule 3: shared mutable state

def test1():                       # rule 1: name says nothing about behavior
    r = requests.get("https://api.example.com/rides")   # rule 3: real network call
    results.append(r.json())       # rule 5: no assertion
```

```

```
