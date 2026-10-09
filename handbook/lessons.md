# Lessons learned

A short retrospective from Trazo's first published release, `v0.1.0`.

- **Keep one source for the framework.** Edit `src/`; treat `.trazo/` as the versioned install, so fixes can be traced to the release a project uses.
- **Plan releases around a goal.** A milestone makes the release scope visible before the tag is cut.
- **Keep a project's memory with the project.** Decisions and status belong in that repository and survive framework upgrades.
- **Check what users install.** Tests should compare the installed files with the pinned release, not just with the current working tree.
- **Give review its own voice.** A separate reviewer can catch gaps the builder is likely to miss, and a comment leaves the result where the next session can find it.

These are retrospective notes, not a process for automatically collecting lessons. Durable guidance belongs in the project's rules or decision records.
