# The bar

A result must clear every item here before the `skeptic` subagent passes it, and before
it reaches a decision-maker or a permanent record (`.trazo/project/adr/`, `.trazo/project/workstreams/`,
`.trazo/project/reports/`, `.template/LESSONS.md`).

**Fill this in at kickoff.** The items below marked *(specialise)* are the ones that change
with the domain; what counts as a valid result does not transfer between projects. The
default here is the general form, so a project that skips the specialisation still has a
working bar — but a quantitative project should replace every *(specialise)* line before
its first result is published.

The skeptic checks these items one by one and cites the item number in its verdict, so a
pass is traceable to a specific line rather than to a general impression. An item you
cannot evidence is an item you did not clear.

## A. The data is what it claims to be

- **A1 — Stale or mismatched inputs.** Every input is current as of a stated date, and the
  two systems compared were asked the same question in the same units. A comparison across
  two sources that define the same term differently is a comparison of two definitions.
- **A2 — The metric measures what it is presented as measuring.** Name the population and
  the window. A number that moved because the population changed is not a result.
- **A3 — Samples are independent.** Overlapping windows, repeated measurements of the same
  subject, or rows that share an upstream event counted as separate samples inflate
  confidence. State the unit of independence and how it was enforced.

## B. Nothing leaked from the future

- **B1 — No look-ahead.** Information dated after the decision point did not reach the
  decision. Check the data's *availability* timestamp, not just its event timestamp.
- **B2 — Not tuned after seeing the result.** Rules, thresholds, parameters, and feature
  choices were fixed before the evaluation set was opened, and any change made afterwards is
  logged and re-validated on fresh data.
- **B3 — Held-out data exists and was touched once.** A genuine holdout that was consulted
  more than once is no longer held out.

## C. The finding survives contact with alternatives

- **C1 — Not one of many tries.** If several variants were examined, all of them are
  reported, or the multiple-comparison problem is quantified. The best of *n* results is
  evidence of *n* attempts, not of one.
- **C2 — Not driven by a single observation.** Recompute the headline number with the most
  influential point or period removed. If the conclusion changes, that is the finding.
- **C3 — Not an artefact of the period.** The result holds outside the specific window
  examined, or the window is stated as a limitation of the claim rather than of the study.

## D. It is realisable, not just arithmetically true

- **D1 — Costs and rounding accounted for.** Fees, slippage, latency, and rounding are in
  the numbers, at the magnitudes that would actually occur.
- **D2 — A sanity ceiling.** State the best physically possible outcome for this quantity
  and confirm the result is below it. A result that beats the ceiling is a bug until proven
  otherwise. *(specialise)*
- **D3 — Worth doing at that size.** The effect is large enough to matter after the costs in
  D1, and the tail risk is shown, not just the average. *(specialise)*

## E. Someone independent looked

- **E1 — The `skeptic` subagent returned a verdict**, in a context that did not build the
  result, and the verdict is recorded on the issue or the pull request.
- **E2 — Caveats carried forward.** Every "holds with caveats" caveat is written where the
  result is cited, so a later reader meets the caveat before the number.
