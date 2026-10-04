# 0009: Tag immutability binds from the first external consumer, not from the first tag

**Date:** 2026-10-01  **Status:** accepted

## Context

[0006](0006-release-process.md) decided that a release is an immutable annotated tag, that
`make release` is the only way to cut one, and that **"Tags are never moved. A new change is a
new version."** The reasoning was sound and still is: Trazo is consumed by mounting `.trazo/`
into another repo, so "latest" has to name one unambiguous thing, and a ref that shifts under a
consumer silently mixes two releases.

The rule was written for a repository that had consumers. This one did not, and the gap between
the rule and the situation produced a false version history.

Measured on 2026-10-01, before this record:

```
git tag -l                                   ->  v0.7.0  v0.9.0          (2 tags)
grep -c '^## ' .template/CHANGELOG.md       ->  10                        (10 entries)
git ls-remote --tags origin | wc -l         ->  4  (2 tags, each annotated)
```

**Eight of the ten changelog entries never existed as tags.** `0.1.0`, `0.1.1`, `0.2.0`,
`0.2.1`, `0.3.0`, `0.4.0`, `0.5.0`, `0.6.0` and `0.8.0` are changelog text and nothing else.
Worse, the two real tags were four days old and named a half-finished product: `v0.9.0` pointed
at `4606b31`, which calls itself a `0.9.0` of an overlay that had no installer, no published
template split ([#77](https://github.com/manoochehri/trazo/issues/77)), and a
`docs/STATUS.md` listing issues as next that were already closed ([#54](https://github.com/manoochehri/trazo/issues/54)).

**Nobody could have been holding them.** Verified rather than assumed:

- No script resolves a tag. `grep -rn 'describe\|git fetch\|refs/tags\|--tags\|archive' scripts/*.sh`
  returns only `release.sh:94`, which *refuses* re-tagging, and one unrelated AWS API call.
- The installer that would resolve a tag is [#53](https://github.com/manoochehri/trazo/issues/53) —
  open, `P2`, never built.
- `0.7.0`, `0.8.0` and `0.9.0` all carry the same date, 2026-09-30. Four minor versions in one day
  on a four-day-old repository is the failure `.trazo/rules.md` already names: *"four minor
  versions in a day reads as `0.9.0` on a three-day-old repository, which is a claim, not a fact."*

So the precondition behind 0006's rule — *"someone may hold it"* — was false. The rule was not
followed badly. It was **written for a situation that did not exist yet**, and a rule whose
precondition is false should not be enforced as though it were true.

The owner, on being shown this, called the tagging itself the bug: a half-finished product should
never have been pinned in the first place. That is correct, and it is the more general defect.

## Decision

- **Immutability is conditional on there being a consumer.** A tag is immutable once something
  outside this repository could resolve it — a published installer, a documented pin, or a host
  that has mounted the overlay at a version. **Until then, pre-release history is editable**:
  tags may be deleted or renamed, and the changelog may be corrected to match reality.
- **The first published release is the boundary, and it is recorded here.** When the installer
  from #53 ships, or the first host pins a version, that release is the first immutable tag.
  Everything before it is pre-release history and carries no guarantee.
- **The trigger is the consumer, not a version number.** Reaching `1.0.0` does not by itself
  start the guarantee. The guarantee starts when someone outside can resolve a ref. Recording the
  boundary at the moment it happens is what makes the next agent stop re-deriving it.
- **A tag may not be cut for a product known to be incomplete.** Cutting `v0.9.0` on an overlay
  with no installer and a stale `STATUS.md` is the defect this record corrects. If the work is not
  finished, the version is not cut.
- **Prereleases stay out of scope.** `scripts/release.sh` accepts `MAJOR.MINOR.PATCH` only and
  rejects anything else. 0006 left two questions open — whether prereleases exist, and what a
  consumer resolves when the newest tag is one. **Both are answered the same way: there are no
  prereleases before the first published release.** Revisit only when a consumer must choose
  between a prerelease and a stable tag, which is a problem that does not exist yet.

## Alternatives considered
- **Keep 0006 as written and add an exception for this repository.** Rejected: an exception scoped
  to one repo is how the exception becomes the norm, and it leaves 0006 asserting a guarantee the
  project is not making. The condition belongs in the rule, not beside it.
- **Delete the tags and say nothing.** Rejected: this is the action that was taken, and doing it
  without recording why guarantees the next agent re-litigates it. The tags are gone; the reason
  they were allowed to go is the durable part.
- **Rewrite 0006 in place.** Rejected: ADRs are append-only ([#49](https://github.com/manoochehri/trazo/issues/49)).
  Rewriting a record to match a later change makes it false.
- **Keep the tags and label them `pre-release`.** Rejected on the merits, not on principle: the
  product was incomplete, so the tags invited someone to pin a broken overlay. The fix is to
  remove the invitation, not to decorate it.

## Consequences

**Already done, at the owner's direction, on 2026-10-01:**

- `v0.7.0` and `v0.9.0` deleted locally and pushed (`git push origin --delete`). `git ls-remote
  --tags origin` now returns empty. Both commits (`7418002`, `4606b31`) remain reachable on
  `main`; a tag is a label, and deleting one destroys no history.

**Still to do, and this record does not do it:**

- `.template/VERSION` reads `0.9.0` — a version with no tag. It is the input `release.sh`
  validates, so it is currently a false claim in the file a consumer would trust.
- `.template/CHANGELOG.md` still carries ten entries, none of which is now a release.

**What this makes easier.** A tag now means what it says. The first real release will be the first
one anyone can honestly pin, and the boundary between "we were building this" and "this is
released" is a recorded fact rather than a number that drifted.

**What this makes harder.** Until the installer ships, there is no stable ref to point a user at,
and "latest Trazo" has no mechanical answer. That is the honest state of a project with no
consumers, and it is better than a tag that resolves to something broken.

**When to revisit.** The moment #53 ships, or the first host mounts the overlay at a version —
whichever comes first. That is the moment this record's first clause activates and immutability
becomes permanent for everything from that release forward.

- **Prereleases stay out of scope.** `scripts/release.sh` accepts `MAJOR.MINOR.PATCH` only and
  rejects anything else. 0006 left two questions open — whether prereleases exist, and what a
  consumer resolves when the newest tag is one. **Both are answered the same way: there are no
  prereleases before the first published release.** Revisit only when a consumer must choose
  between a prerelease and a stable tag, which is a problem that does not exist yet.
