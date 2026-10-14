# 0022: Native reviewer subagents are the default; hosted review is optional

**Date:** 2026-10-13  **Status:** accepted

Decided by the owner on [#204](https://github.com/manoochehri/trazo/issues/204#issuecomment-6158135584).
This record supersedes the hosted-automation requirement in proposed [ADR 0017](0017-automatic-review-on-push.md).

## Context

The GitHub Actions reviewer uses a provider API key. The owner does not have an Anthropic or OpenAI
API key and does not want a provider choice or a missing credential to block ordinary work. The
coding-agent environment can already start a fresh reviewer subagent without adding a GitHub secret.

## Decision

- `/work` gets a fresh reviewer subagent verdict when a complete PR is ready, and again after pushes
  that address review findings. The reviewer checks the exact head SHA and posts the verdict on the PR.
- Provider-backed GitHub Actions review remains optional. It may be enabled by a host that has
  configured credentials, but it is not required to use `/work` or merge a reviewed PR.
- When the hosted workflow is disabled, skipped, or fails before posting a review, `/work` uses its
  native reviewer subagent. It does not require `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` for that path.
- Draft and intermediate work does not trigger review. A later push after review findings gets a new
  reviewer run on the new head.

## Consequences

Users can use the review role through their coding-agent environment without configuring a vendor
API key in GitHub. Hosted review remains available as an opt-in integration for pushes that happen
outside an active `/work` session. The required verdict check still applies to each PR head.
