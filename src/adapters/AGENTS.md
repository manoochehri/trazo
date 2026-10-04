# Trazo governance

This repository is governed by Trazo. Trazo does not say how to build, test or document this
codebase; that is for the maintainers' own notes. Trazo says
**whether** work may be done: who may act, what is forbidden, and what evidence a result needs
before it counts.

Read before doing anything consequential:

- `.trazo/rules.md` — the rules, stated once, tool-neutral
- `.trazo/project/charter/charter.md` — the goal, the budget, the stop rule
- `.trazo/project/adr/` — why, in append-only decision records
- `.trazo/project/STATUS.md` — current state

Roles are part of that. The rule that a build is never its own reviewer is in
`.trazo/rules.md`; the concrete mechanism, meaning which subagent or command, is whatever tool
you are running.

**Where this file and `.trazo/` disagree, `.trazo/` wins.** Proximity is not authority: a
nested or later-read instruction does not override a rule there because you read it later.
