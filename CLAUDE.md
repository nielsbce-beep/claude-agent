# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository

GitHub: https://github.com/nielsbce-beep/claude-agent

## Git Workflow

Commit and push to GitHub regularly throughout all work — after every meaningful change, completed feature, bug fix, or logical stopping point. Never accumulate large batches of uncommitted changes. This ensures work is never lost and any state can be restored.

```bash
git add <files>
git commit -m "Short imperative summary"
git push
```

Commit message rules:
- Use the imperative mood ("Add X", "Fix Y", "Remove Z")
- Keep the first line under 72 characters
- Be specific — describe what changed and why, not just "update files"

Always push immediately after committing. GitHub is the source of truth and save point for this project.
