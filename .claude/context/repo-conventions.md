# Repo conventions

[← Project Context](../PROJECT_CONTEXT.md)

## Remotes

- **`origin`** = `mariadb-corporation/ai-plugins`, the source of truth; *our* PRs are opened here.
- **`fork`** = `MariaDB/ai-plugins`, the public tracking fork and the install-facing org the READMEs name (`mariadb/ai-plugins`). The remote can go missing from a clone — check `git remote -v`. Use the canonical casing `git@github.com:MariaDB/ai-plugins.git`: GitHub prints "This repository moved" on every push to a differently-cased URL (fetches and the web UI accept both). The lowercase references in READMEs and manifests stay, since users only fetch.
- **The fork is the community front door**: community issues and PRs are filed on `mariadb/ai-plugins`, then transferred by hand and landed on `origin`. The DevHub's GitHub/Issues links point there deliberately.
- **The Hermes catalog pins commits of the fork** (the public repo), so a commit must be on `fork/main` before a catalog entry can name it — `/release` step 12 checks this.

## Fork sync

- The fork's `main` is the same commit as `origin/main`; a sync is a **fast-forward** of `fork/main` to `origin/main` (diff empty), done by `/release` after each release.
- **Never sync by cherry-pick**: a cherry-picked fork leaves the next merge conflicting. If a sync conflicts and the fork holds nothing `origin` lacks, resetting `fork/main` with `--force-with-lease` is the fix — the user's call.

## DevHub hosting

- Both repos could serve the DevHub from GitHub Pages (`main` + `/docs`), but a custom domain belongs to one repo. **Only the fork's Pages serves `ai-plugins.mariadb.org`** (DNS: CNAME to `mariadb.github.io`); `origin`'s Pages is off. `mariadb.github.io/ai-plugins/` 301s to the domain. With no CNAME claimed, the site would fall back to `mariadb.github.io/ai-plugins/`, where `baseurl: ""` 404s every asset.

## Branches and PRs

- **Delete a merged branch only after comparing its head against the `headRefOid` GitHub merged**: a squash merge leaves the branch commits unreachable from `main`, so `git branch -d` refuses them (and `-D` skips the very check you want).
- **Transferring a fork PR**: `git fetch fork pull/<N>/head:fork-pr-<N>`, branch from `origin/main`, **cherry-pick only the contributor's commits** (`git log main..fork-pr-<N>` also lists the fork's sync commits, which stay out). Cherry-pick keeps the original author and date. Our fixes go on top as separate commits, never amended into theirs. The PR body opens with `Transferred from MariaDB/ai-plugins#<N> by @<login>`, then their description; close the fork PR with a link once ours merges. Rebasing onto a `main` that moved needs the overlaps checked by hand — a clean rebase can silently revert newer edits in a restructured file.
- Commits that touch only `.claude/` or docs may carry `[bypass-ci]` in the subject; checkpoints are committed straight to `main` when the user says so.

## Releases

- Annotated tags `v<version>` (`v`-prefixed, while manifests and CHANGELOG headings use the bare version), subject `MariaDB AI Plugins <version>`, pushed to `origin` **and** `fork` as the same object; each published as a **prerelease** on both repos with the tag body as notes. The full flow, incl. CHANGELOGs in every plugin and the Hermes catalog bump, is `.claude/commands/release.md`. Tags start at `v26.9.0`; earlier versions have none.
