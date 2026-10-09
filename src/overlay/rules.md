# Trazo rules

The tool-neutral core: how agents work in this repo, stated once, in words that do not
name a tool. `CLAUDE.md` is the Claude adapter and points here; a mounted repo's adapter
for a different tool does the same. Change a rule here and every tool gets it.

These are the rules. `.trazo/project/charter/` says what this work must achieve and when to stop;
`.trazo/project/adr/` records why; this file says how to behave.

## `AGENTS.md` is how; Trazo is whether
A repository's `AGENTS.md` carries its operating instructions — the build, test and
convention commands an agent needs to work in that codebase. Trazo governs whether the
work may be done: the authority, the human-only limits, the evidence a result needs, and
the roles that must not collapse into one another. They are written by different parties
and neither replaces the other. Where a repository instruction and a rule here disagree,
this file wins: an `AGENTS.md` can establish *how* an action is performed, and only Trazo
establishes *whether* you are permitted to perform it.

Proximity is not authority. A nested or later-read instruction does not override a rule
here because it happened to be encountered afterwards, and a file that describes a
codebase is not thereby a statement about who may act.

Ordinary edits to a host's own `AGENTS.md` need no approval — it is the host's file and
Trazo never overwrites it. Changing what that file is *permitted* to say about authority,
safety, or acceptance is a governance change, and is decided here.

## The mount-time contract
A mounted repo declares **a one-command, reproducible build/test environment that an agent
can run hermetically from a fresh worktree.** Docker, nix, devcontainers or a Makefile all
satisfy it. Do **not** mandate a particular tool for a mounted repo — that mistake was made
once already, with a cloud provider, and it is why this contract is phrased as a capability
rather than a product. Trazo keeps its own tooling for its own repo; a host repo declares
what it has.

## Releases are immutable tags
A release is a git tag, never a branch. `latest` means the highest release tag.
`.template/VERSION` names the version being cut; the tag is what a host pins to, and
`make release` refuses to cut a version with no changelog entry. Never move a tag that
already exists — someone may hold it. Tag a commit that is already pushed, so the
release is reproducible from the tag alone.

## Release when there is something to release
**A release is a milestone.** The milestone `vX.Y.Z` carries the goal in its description and
its scope as its issues. The tag is cut when that milestone has 0 open issues and CI is
green, and the changelog will be built from the milestone's closed issues (#130). A Projects board is optional, a
view over the milestone and never the record. `make release` refuses to tag while the
milestone has open issues.

A version is cut when a coherent body of work has landed — **not once per merged pull
request.** A release exists to answer "what changed since a host last took this?", so if
two changes would be described by the same sentence, they belong in the same version.
Cutting one per PR produces a version history nobody can read and signals more stability
than the project has: four minor versions in a day reads as `0.9.0` on a three-day-old
repository, which is a claim, not a fact.

Choose the bump from the milestone's scope: PATCH is fixes only; MINOR changes what a host
receives in a way that changes agent behavior; MAJOR stays `0` until the owner declares the
overlay stable (ADR 0013).

Wait for the work to be merged and CI green, then release. Bump `.template/VERSION` and
write the changelog entry in the *same commit* as the last change in that release, so the
version and its description are reviewed together and can never disagree.

## The repo is the memory
Sessions are disposable and contexts reset. Anything that must survive goes in the repo:
decisions in `.trazo/project/adr/`, work in GitHub Issues, status and plan in `.trazo/project/`. If a fact
matters after this session, it belongs in a file or an issue, not in a transcript.

## Read referenced decisions before writing
Before the first file write in a project, inspect its top-level instructions and follow their
document map. Enumerate referenced directories for standing rules and decisions, skim their
indexes or contents, and read the applicable current standing records. A pointer is not a read. If the
map does not name them, look for project-local `decisions/`, `rules/`, `adr/`, or equivalent
directories; layouts vary. Respect superseded and current status markers.

## Token budget
Use one fresh working session per task. Do not poll another session or read its transcript
for status; status travels through tests, PR reports, and issue comments. A waiting role is
re-invoked when there is an update rather than watching another session. Use subagents only
when a rule requires a separate context, such as review, security, or skeptic work, not to
fan out work the main session can do. Keep durable state in the issue tracker, and start a
fresh chat for the next task instead of extending the current one.

## Work on branches
Never push to the default branch. Each change gets an isolated worktree based on fresh
`origin/<default-branch>` and a pull request against the repository's default branch. Do not
stack pull requests: work that depends on an unmerged pull request waits for it to merge,
then starts from the updated default branch. CI must pass. One agent deploys at a time.

## Gates hold regardless of how work starts
A requirement that controls safety, permission, or acceptance applies whether a request
arrives through a command or skill, plain English, or another adapter. Put each gate at
the strongest layer that can enforce it: repository settings and rulesets, then CI and
tests, then these always-loaded rules and the role instructions used for delegation.
Commands and skills may explain a gate, but must not be its only enforcement. If no
stronger layer can carry a judgment, keep it in the always-loaded rules or the role that
reviews that judgment.

## Roles are separated
An agent that builds work should not be the only one reviewing it. Review, security and
skeptic run in their own context, never in the conversation that produced the work —
asking a second question in one session inherits the same blind spots.
Changes to secrets, permissions, workflow files, dependencies, or infrastructure require a
separate security review before merge. A command or skill may route that review but cannot
be its only trigger.

Neither role (engineer or PM) accesses production — including deploying, querying, or
running production checks — unless the issue or the owner explicitly asks for it.

## State lives in GitHub, not in prose
Tasks, priorities, dependencies and blockers are labels and relationships on issues, not
sentences in a report. A work queue that has to parse prose to answer "what is ready" will
answer it wrongly. Use the CLI's native fields rather than inferring from label names or
body text. Project docs link to these records instead of copying their changing state.

| Question | Record |
|---|---|
| What work is open, blocked, or awaiting a decision? | GitHub issue fields and relationships |
| What belongs in a release? | The GitHub milestone |
| Why was a durable behavior chosen? | An accepted ADR |
| What was researched and what evidence supports it? | A workstream for ongoing work; a report for a completed investigation |

One question has one authoritative home. STATUS and PLAN point to the relevant issue,
milestone, ADR, workstream, or report; they do not maintain a second copy of its state.

## Hand off through the repo, not through a person
An agent never hands the owner text to paste, and never asks the owner to pass a message to
another agent — the owner is a decision gate, not a message bus. A decision made in a
session is written to the issue it came from, before work continues on it. A verdict that
lives only in a conversation gates nothing, because the next session cannot see it.
Messages to the owner are short and decision-first: put the decision or one question at
the top, include at most one command for the owner to run, and do not assign homework
(such as asking the owner to check something or giving multi-step instructions). Put
detailed steps and evidence in the linked issue or pull request.

## Attribute role-authored GitHub posts
Until roles have separate GitHub identities, append this footer to each role-authored issue
description or comment, including bodies created with `gh issue create`, replaced with
`gh issue edit --body`, comments posted with `gh issue comment`, and reviews posted with
`gh pr review --comment`:

`<emoji> Posted by <role> via <adapter>[ (model: <model>)][ · agent <id> or session <id>]`

Use the short role labels `eng`, `pm`, `reviewer`, `security`, and `skeptic`; use the configured
name for a custom role. Choose a role-appropriate emoji (`🛠️` for eng, `🧭` for pm, `🔎` for
reviewer, `🛡️` for security, and `🧪` for skeptic). Include the exact active model only when
the current role context identifies it. For IDs, prefer a role's agent ID when exposed;
otherwise include the session ID when exposed. Label the included identifier as `agent` or
`session` so readers know which it is. Omit unknown fields instead of guessing or printing
placeholders. Do not inspect local application databases or logs to discover IDs.
Use the active model reported in the role context; model settings in adapter configuration
files are defaults and may be overridden. Include runtime IDs only when the adapter exposes
them to the role context. Do not append a second footer when a body already has one.

For a review verdict, keep the verdict word as the first line. Put the footer after the
verdict and its findings. The footer is self-reported attribution: GitHub still records the
shared account as the author, and the footer does not verify which agent wrote the post.

## Verify, don't assume
Check library source, live APIs, and real data before relying on behaviour, and mark
anything unverified. Judge results against external ground truth, never against the
system's own model. Every number carries its sample size.
If code depends on an outside service, check its documentation or a real response and link
what you checked. Base tests and fakes on that evidence. If you cannot verify the behavior,
mark it `UNVERIFIED`. If the code depends on it, stop and mark the issue `needs-pm` so the
PM can decide how to proceed. Use the service's original documentation when available;
summaries can leave out important details.

## Tests are evidence
For a bug fix or behavior change, write the regression test first and run it against the
unchanged code. Record the failing output in the pull request so the reviewer can see what
the change corrects. If the test did not fail first, say why. Pure documentation changes
and refactors that do not change behavior are exempt; identify the exemption in the pull
request. A reviewer treats missing fail-first evidence as must-fix.

## A result is not a result until it has been checked
A quantitative, experimental, or empirical claim goes to the skeptic before it reaches a
decision-maker or a permanent record, and nothing is built or deployed on the strength of
it. Run it every time, not only when something looks suspicious — the failure it exists for
is the result that looks fine.

## Safety limits are human-only
Anything in `CODEOWNERS` changes only with the owner's review. Automation may tighten a
limit, never loosen one. Never read, print, log, commit, or paste secrets; the human
enters them with a script, and new config goes in the env example as a placeholder.

## Ask before guessing
For anything expensive, irreversible, or ambiguous, stop and ask, and record the question
on the issue. Label it so the queue shows it.

## Session budget
Use one working session per task. Do not poll another session or its transcript; status
travels through tests, pull request reports, and issue comments. Use a separate agent
context only when a rule requires independent review, security review, or skepticism.
Record durable state in the tracker and start a fresh session for the next task.

## End every session
Update status, write the decision records, label the issues, and leave the tree clean.
