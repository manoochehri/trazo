# 0001: Keep project state in the repo

**Date:** YYYY-MM-DD  **Status:** accepted

> **Date of record:** 2026-09-27, inferred from commit `7eaf827` — the initial commit, which
> is when this file was created, not necessarily when the decision was taken. The original
> decision date was never recorded, and the header above still carries the template's
> `YYYY-MM-DD` placeholder rather than a date nobody can now verify.
>
> This note is appended rather than substituted: decisions are append-only (see ADR 0003),
> so the honest record is the placeholder *plus* what is actually known, not a plausible date
> written into the header by someone guessing.

## Context
AI sessions lose context when they end or reset. Decisions and status kept only in chat get lost.

## Decision
All durable state lives in `docs/` (charter, plan, architecture, status, decisions, workstreams, reports). Tasks live in GitHub Issues. Every session ends with `/wrapup`.

## Alternatives considered
- One long project log: grows unreadable; mixes status with history.
- External PM tool: agents can't reliably read or update it.

## Consequences
Any agent can be started fresh. Docs must be kept current; the PR template enforces it.
