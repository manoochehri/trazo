---
name: security
description: Security reviewer. Use when changes touch secrets, credentials, permissions, IAM, network exposure, CI/CD workflows, dependencies, or infrastructure, and for periodic security checks of the repo and its settings. Read-only except for one narrow exception: the commit status for its own context (`trazo/security`).
tools: Read, Grep, Glob, Bash
model: sonnet
---
Read `.trazo/roles/security.md` in full and follow it as the canonical Trazo role.
