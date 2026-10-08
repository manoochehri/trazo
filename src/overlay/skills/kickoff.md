Run project kickoff for this repository.

1. Interview the owner briefly: the idea and goal, measurable success criteria, budget (money/time), deadline, hard constraints, what will never be done, the stop rule, whether it needs a UI, and where it runs.
2. Inspect the blank project files the Trazo installer created under `.trazo/project/`. Draft the charter, `PLAN.md`, and `SKEPTIC_BAR.md` from the answers. Ask what counts as a valid result in this domain and specialise the skeptic bar for it. Show the drafts and wait for approval before writing them.
3. After approval, fill in the approved project state and record tooling decisions as ADRs. Do not overwrite existing project decisions or owner-protected files.
4. Set up GitHub labels, milestones, and initial issues only after agreeing on the plan. A Project board is optional.
5. Add repository safety settings only with owner review. Do not loosen branch protection, CODEOWNERS, or other safety limits. Never edit CODEOWNERS paths without its owner review.
6. Run the repository's documented setup, test, and secret-scan commands. Fix failures before calling setup complete.
7. Record the runtime, deployment procedure, budget alert, and teardown commands in the runbook when the owner approves a deployment target. Trazo provides no default deploy target.
8. Keep the project's operating docs accurate. Publish a documentation site only if the owner chooses one and approves any workflow, repository, or Pages settings changes.
