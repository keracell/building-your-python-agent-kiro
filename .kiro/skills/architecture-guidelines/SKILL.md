---
name: "architecture-guidelines"
description: "Load when reviewing Python code for architecture: layered architecture (entrypoint vs service), repository pattern, configuration from the environment, and constructor dependency injection. Used by the architecture-reviewer."
---

# Architecture guidelines

Cite each guideline by name and ADR number when reporting a violation. Full
text is in `docs/adr/`.

## Layered architecture (ADR-001)

- Entrypoints (route handlers, CLI commands, `main()`) only parse input and
  format output.
- Business logic lives in a service module.
- Violation: business logic or direct data access inside an entrypoint.

## Repository pattern (ADR-003)

- Services get data only through a repository.
- Only repositories may depend on `ApiClient`, a database, or an ORM.
- Violation: a service imports or references `ApiClient`, builds its own HTTP
  client, or calls a database/ORM directly.

## Configuration (ADR-002)

- Configuration and secrets come from environment variables or the single
  config module.
- Violation: a hardcoded config value, or `os.environ` read outside the config
  module.
- A hardcoded secret is also a security finding.

## Dependency injection (ADR-004)

- Dependencies are passed in through the constructor or function parameters.
- Violation: a module-level global singleton, a ServiceLocator lookup, or a
  dependency created inside the class.

## Severity

- HIGH: layer skipping (ADR-001, ADR-003) or a hardcoded secret (ADR-002).
- LOW: other violations of ADR-002 or ADR-004 with limited impact.
