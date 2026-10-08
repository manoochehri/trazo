# Install, upgrade and uninstall

Trazo is installed into your repository from a release tag, by one script. Nothing is
copied from a template repository and nothing is fetched from a moving branch.

!!! note "No release exists yet"
    The first tag, `v0.1.0`, is cut by [#100](https://github.com/manoochehri/trazo/issues/100).
    Until it exists, `install v0.1.0` has nothing to fetch and refuses. The commands below
    work as written once the tag is published.

## Install

From the root of your git repository:

```sh
curl -fsSL https://raw.githubusercontent.com/manoochehri/trazo/v0.1.0/scripts/install.sh -o install.sh
bash install.sh install v0.1.0
```

Pin the script to the same tag you install, as above. The tag is required: with none, the
script refuses. `latest` is accepted and resolves to the highest `vMAJOR.MINOR.PATCH` tag,
never to a branch.

| Option | Meaning |
|---|---|
| `--adapter claude\|agents\|codex\|both` | Which tool adapter to install. Default `both` (Claude and the generic `AGENTS.md` adapter). Use `codex` for Codex's project agents and skills. |
| `--source <path-or-url>` | Where to fetch from. Default `$TRAZO_SOURCE` (announced when used), then the public repository. A value starting with `-` is refused. |
| `--sha <commit>` | Optional full 40-hex commit the tag must resolve to; refuses on a mismatch. Use it to detect a moved tag. |

What it does:

- Copies the framework (`rules.md`, `ADVISOR.md`, `ARCHITECTURE.md`, `templates/`) into
  `.trazo/` and writes the tag and its resolved commit to `.trazo/VERSION`. The source, tag and
  commit are printed. Tags containing symlinks under `src/` are refused.
- Creates `.trazo/project/` from the blank templates **only if it does not exist**. It is
  yours, and no command here overwrites it.
- Inserts the adapter into `AGENTS.md` and/or `CLAUDE.md` between
  `<!-- trazo:begin -->` and `<!-- trazo:end -->`. If the file exists, everything outside
  those markers is left byte for byte as it was; if it does not, it is created. Running
  install again replaces the block and nothing else.
- For the Claude adapter, copies `agents/` and `commands/` into `.claude/`. If a file of
  that name is already yours, the Trazo one is installed as `trazo-<name>.md` and the
  script says so. `.claude/settings.json` is installed only if you have none.
- For Codex, inserts the `AGENTS.md` adapter block and installs project-scoped role agents
  under `.codex/agents/` and workflow skills under `.agents/skills/`. Both point to the
  canonical roles and rules in `.trazo/`. Existing host files are preserved; on a name
  clash, Trazo prefixes the installed name and reports it.
- Records a sha256 and path for each adapter file it placed in `.trazo/INSTALLED`, so upgrade
  and uninstall touch only those. A listed file you have edited since is never overwritten
  or deleted: the script warns and, on upgrade, prints the diff. Entries outside
  the supported Claude and Codex adapter paths make the script refuse.
- Prints the `settings.json` it installs. It only denies reads of secrets.
- Refuses if `.trazo/` exists without `INSTALLED` (an older layout), and on unbalanced
  markers in `AGENTS.md` or `CLAUDE.md`.
- Never edits `.github/CODEOWNERS`. It prints lines for you to add; a safety limit only
  counts if you review it.

## Upgrade

```sh
bash install.sh upgrade v0.2.0 --dry-run   # show the diff of .trazo/ and stop
bash install.sh upgrade v0.2.0             # show the diff, then apply
```

Upgrade is install at a newer tag, with a unified diff of `.trazo/` printed before anything
changes. Framework files are replaced (files dropped upstream are removed). `.trazo/project/`
is never read or written.

## Uninstall

```sh
bash install.sh uninstall            # keeps .trazo/project/
bash install.sh uninstall --purge    # removes it too; refuses if it has uncommitted, untracked or gitignored files
bash install.sh uninstall --purge --force   # ...unless you pass --force
```

Removes the framework files under `.trazo/`, the adapter files listed in
`.trazo/INSTALLED`, and the marked blocks in `AGENTS.md` and `CLAUDE.md`. A file that held
only the block is deleted; otherwise your content stays. Your own `.claude/` files, your
`.codex/` agents, `.agents/skills/`, `CODEOWNERS`, and `.trazo/project/` (without `--purge`)
are not touched.
