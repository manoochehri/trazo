# .template: Trazo's own memory

This folder is about **Trazo itself**, not the project it is mounted on. It travels with
the overlay so Trazo can improve from real use.

**New here? Read [the guide](../handbook/guide.md).** Already running? [The playbook](../handbook/playbook.md) covers the daily loop and what to do in every common situation. Both are published at the [docs site](https://manoochehri.github.io/trazo/), built from `handbook/`.

- `VERSION`: the overlay version this project was mounted from
- `CHANGELOG.md`: what changed in the overlay, by version
- `LESSONS.md`: lessons learned from real projects, each tied to a change (or "not yet")
- `decisions/`: why the overlay is the way it is

**There is no upstream pointer, and no sync command.** Trazo is mounted onto a host repo,
not forked from a template, so a mounted project has nothing upstream to pull from and no
fork to send fixes back to. To take an improvement, copy the changed files from Trazo into
the host repo — or re-run `/kickoff` — and let the host's own decision records win on
anything they disagree about. Lessons flow the other way only when you are working **in
Trazo itself** and choose to promote one by hand (issue #73).

When working **on Trazo itself**, `CLAUDE.md`'s "project" means the overlay, and `.trazo/project/`
is this repository's own state and never ships; hosts get blank templates from `src/overlay/templates/`.
