# Structure

```
AI-AGENT/
├── AGENTS.md          # Agent definition: role, rules, output format, guardrails
└── .kiro/
    └── steering/      # Steering files: product.md, tech.md, structure.md
```

## Conventions
- Changes to agent behavior go in `AGENTS.md`. Keep steering files consistent with it.
- Steering files live only in `.kiro/steering/` as Markdown.
- Keep documents short and rule-based.
