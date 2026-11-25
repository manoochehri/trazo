## What and why
Closes #<issue-number> as the **first line of the commit message** (`Closes #<n>: ...`), not just here — a squash merge keeps the commit subject, and a body-only or prose-only keyword leaves the issue open (#61, #68).

## Checks
- [ ] Tests added/updated and passing
- [ ] External behavior assumptions cite primary docs or a real response; fakes and fixtures cite what they model
- [ ] No secrets, keys, or real data in the diff
- [ ] Changed the system's shape? Updated `.trazo/ARCHITECTURE.md`
- [ ] Changed how to run/deploy/recover? Updated `.trazo/project/RUNBOOK.md`
- [ ] Made a decision? Added `.trazo/project/adr/NNNN-*.md`
- [ ] Changed a workstream's status or evidence? Updated `.trazo/project/workstreams/`
- [ ] Numbers reported with sample sizes and measured against external reality
- [ ] Learned something reusable? Recorded it in `.trazo/rules.md` or a new ADR

## Evidence
CI (`scripts/check_pr_evidence.py`) reads the lines below literally. Each stands alone on its own line: no bullet, no checkbox, no bold. Replace every `<...>` placeholder; a leftover one fails the check.

Review rounds: <number>
Defects found and fixed: <summary or none>

## Fail-first output
```
<paste the failing test output from the unchanged code; it must contain a FAILED, ERROR, AssertionError or Traceback line>
```

No fail-first output (docs-only change or a refactor that changes no behavior)? Delete the whole `## Fail-first output` section above and its fenced block, and use this one line instead, with a reason of at least 20 characters. Delete this paragraph too:

Fail-first exemption: <reason, at least 20 characters>
