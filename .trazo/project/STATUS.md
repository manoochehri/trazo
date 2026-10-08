# Status

> Replaced at the end of every session. Keep under one screen.

**Updated:** 2026-10-08 by engineer (Codex)
**Phase / milestone:** `v0.1.0` (#92); 8 of 10 epic children are closed.

## Running now
- **#124 → PR #167** — compare the installed copy against the recorded release tag when
  available. CI and separate review pass; the post-tag path awaits the first release tag.

## Blocked / needs a decision
- **#100 — release:** the `v0.1.0` milestone has 14 open issues. Owner-only #134 is
  unfinished, and `.template/VERSION` is `0.6.0` while the milestone and release gate
  require `v0.1.0`; the owner recommended resolving this mismatch before changing either.

## Next
1. Owner reviews and merges PR #167; after `v0.1.0` is tagged, confirm the pinned-tag
   comparison runs and close #124.
2. Resolve #100's version decision, complete #134, and clear the milestone's open issues
   before attempting the release.
