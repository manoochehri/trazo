## What and why
Closes #<issue-number> as the **first line of the commit message** (`Closes #<n>: ...`), not just here — a squash merge keeps the commit subject, and a body-only or prose-only keyword leaves the issue open (#61, #68).

## Checks
- [ ] Tests added/updated and passing
- [ ] No secrets, keys, or real data in the diff
- [ ] Changed the system's shape? Updated `.trazo/ARCHITECTURE.md`
- [ ] Changed how to run/deploy/recover? Updated `.trazo/project/RUNBOOK.md`
- [ ] Made a decision? Added `.trazo/project/adr/NNNN-*.md`
- [ ] Changed a workstream's status or evidence? Updated `.trazo/project/workstreams/`
- [ ] Numbers reported with sample sizes and measured against external reality
- [ ] Learned something reusable? Recorded it in `.trazo/rules.md` or a new ADR
