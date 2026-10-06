# Trazo Roles

Canonical Trazo role definitions. These roles represent the standard division of responsibilities for agentic work governed by Trazo.

## Standard Roles

| Role | Purpose | Model | Edits Code? |
|------|---------|-------|-------------|
| **[Engineer](engineer.md)** | Builds, tests, and delivers code changes | Sonnet recommended | Yes |
| **[PM / Advisor](pm.md)** | Plans, prioritizes, and judges results | Opus recommended | No |
| **[Reviewer](reviewer.md)** | Reviews pull requests before merge | Opus recommended | No |
| **[Security](security.md)** | Checks security, permissions, dependencies | Opus recommended | No |
| **[Skeptic](skeptic.md)** | Breaks quantitative claims before action | Opus recommended | No |

## Role Separation Principle

Roles are separated to prevent conflicts of interest and ensure proper governance:
- **A build is never its own reviewer**
- **Security checks are independent**
- **Quantitative claims are skeptically examined**
- **Planning is separate from implementation**

## Using These Roles

Tool-specific implementations should reference these canonical definitions rather than redefining roles. Each tool implements these roles according to its capabilities while adhering to the core responsibilities defined here.

## Custom Roles

Projects may define custom roles in `.trazo/project/roles/`. Custom roles should be documented with the same structure: purpose, model, permissions, constraints, and key responsibilities.
