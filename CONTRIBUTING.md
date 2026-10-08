# Contributing to Trazo

Trazo is mounted onto a host repo, not forked from a template, so there is no automated
path for a host project to send a change back. If a mounted project learns something
reusable, note it in that project's own decision records — and when you are working **in
Trazo**, promote what is worth promoting, by hand, on a branch like any other change.

Every change should:
- solve a problem that actually happened (add a row to `.template/LESSONS.md`)
- keep the core cloud-neutral and lean (deploy targets are the host's choice, not shipped here)
- keep working for a host repo that already has its own runtime, docs and conventions
- bump `.template/VERSION` and add a `.template/CHANGELOG.md` entry, in the same commit
- use `make changelog` to draft the entry from the closed issues in that version's milestone; review and commit it with the release change
- cut a release with `make release` (validates, tags `vX.Y.Z`, pushes) once merged

**When to cut one:** when a coherent body of work has landed, not once per merged PR. If
two changes would be described by the same sentence, they belong in the same version. This
repository shipped four minor versions in one afternoon because the rule above was read as
"bump on every change"; the version history was unreadable and `0.9.0` implied a maturity
the project does not have. See *Release when there is something to release* in
`.trazo/rules.md`.
- contain no secrets, real data, or project-specific names (CI runs gitleaks)
