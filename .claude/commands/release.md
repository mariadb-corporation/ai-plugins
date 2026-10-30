---
description: Cut an ai-plugins release, suggesting its next YY.MM.x version and raising the mariadb-shell floor to the latest shell release where there is a newer one, PR it, sync the fork, then PR the new pin to the Hermes plugin catalog. Usage: /release [version|-] [shell-version|-]
---

# Release Command

Arguments as typed: `$ARGUMENTS`

Split that string on whitespace. The first word is the plugin version, the
second is the new mariadb-shell floor. Both are optional, so a bare `/release`
works. A `-` in a position means "not given", so the floor can be given without
the version (`/release - 26.10.3`). What is not given is suggested in step 2:

- the plugin version: the next `YY.MM.x` version (see step 2);
- the floor: the latest published mariadb-shell release, when it is newer than
  the current floor. Otherwise it stays where it is.

From here on, "the plugin version" and "the floor" mean the two versions this
release ships, given or suggested; `<version>` and `<floor>` stand for them in
the commands below. If a third word is present, stop and ask what it means.

Both versions must be a bare `MAJOR.MINOR.PATCH` such as `26.10.0` — no `v` prefix. The
version *inside* this repo (manifests, CHANGELOG headings) is bare; only the git
tag carries the `v` (`v26.10.0`). Strip a leading `v` if one was given and say so.

**The two versions are independent.** The plugin version is the ai-plugins version: the plugin
manifests, the CHANGELOG headings and the tag. The floor is the `MARIADB_SHELL_VERSION`
floor, the oldest mariadb-shell the launchers accept. Through 26.9.5 the two were
always equal; that is no longer required. With no floor given it stays where it is
and the release ships on top of the current shell version — unless a newer shell
release exists, in which case step 2 suggests raising the floor to it.

Read `.claude/PROJECT_CONTEXT.md`, then `.claude/context/release-history.md` and
`.claude/context/repo-conventions.md` before starting: the previous release's
notes are the model for this one.

Remotes: `origin` = `mariadb-corporation/ai-plugins` (source of truth, where the
PR goes) and `fork` = `mariadb/ai-plugins`. Check `git remote -v` — the `fork`
remote has gone missing before. If either is missing, stop and report it.

## 1. Preconditions

- `git status --short` must be clean and the current branch must be `main`,
  level with `origin/main` after `git fetch --multiple --tags origin fork`. If not, stop
  and report rather than stashing or resetting anything.
- `v<version>` must not already exist as a tag locally or on either remote
  (`git ls-remote --tags <remote>`, once per remote — `ls-remote` takes one
  remote and would read `fork` as a pattern). If it does, stop. When the
  version is suggested, check this in step 2, once it is known.

## 2. Check the versions

Do all of this before changing anything, and report what you find in one
summary: the plugin version and the floor, each with its current value, the
value this release ships, and whether that was given or suggested.

**When anything was suggested, stop and ask the user to confirm the summary.**
They may accept it, or change either version, for example to keep the current
floor although a newer shell exists. Run the checks below again for what they
changed. When both were given, report the summary and go on.

**The plugin version.** List this repo's tags (`git tag -l 'v*' | sort -V`) and
take the highest. Report it as the previous version.

- **None given:** suggest `YY.MM.x` from today's date (`date +%y.%-m`): `YY` is
  the year's last two digits, `MM` the month without a leading zero (`26.9.0`,
  never `26.09.0`: semver forbids leading zeros), and `x` counts the releases
  of that month. It is `0` for the month's first release, and one more than the
  highest `x` among the tags that start with `vYY.MM.` otherwise. If the
  suggestion does not sort above the highest tag (one from a later month
  exists), stop and report it. Check that `v<suggestion>` is not a tag, locally
  or on either remote.
- **One given:** it must sort above the highest tag, or stop. If it does not
  follow `YY.MM.x` for this month, say so and ask whether to use it anyway.

**The current shell floor** is `shell_floor` in `docs/_config.yml`; it also
appears as the launchers' fallback (`VERSION="${MARIADB_SHELL_VERSION:-<v>}"`).
Read it and report it.

**The published mariadb-shell releases.** Every mariadb-shell release is a
**prerelease**, so `releases/latest` 404s — do not use it. List the releases
instead:

```bash
gh release list --repo mariadb-corporation/mariadb-shell --exclude-drafts --limit 30 --json tagName,isPrerelease,publishedAt
```

Sort the `tagName`s as versions (strip the `v`; `sort -V`), not by date.

- **The current floor itself is not in the list** (it was raised on `main`
  ahead of the shell release) → stop, whatever was given. A release must not
  ship a floor no launcher can install. Say whether the floor's release is
  still to come or whether the floor should go back to a published one, and
  let the user decide. A floor given here that *is* published resolves it.
- **No floor given:** check whether the current floor is still the latest
  published shell release (the highest `tagName`). If it is, the floor stays
  unchanged. If a newer one exists, suggest raising the floor to it, naming
  both versions and the latest one's publish date, and continue with it as if
  it had been given (the checks below then pass trivially). The confirmation
  of the summary settles it.
- **A floor given:**
  - `v<floor>` is not in the list → stop. The shell floor must never sit above a
    published release, or every launcher would demand a binary that does not
    exist.
  - It is below the current floor → stop and ask; lowering the floor is not a
    normal release step.
  - It equals the current floor → nothing to move; continue as if no floor was given.
  - A version higher than it exists → say so and ask whether to use the given floor anyway.
  - Otherwise continue, and report the publish date of `v<floor>`.

## 3. Branch and set the versions

```bash
git switch -c wip/<version>
scripts/set-mariadb-shell-version.sh <floor>   # only when the floor moves (step 2)
scripts/set-plugin-version.sh <version>
```

Run them in that order and stop at the first non-zero exit. Skip the shell-floor
script entirely when the floor is not moving. After each, note how many files
changed (`git status --short | wc -l`). For reference, 26.9.5 moved 33 files for
the shell floor and 17 for the plugin version; the Hermes plugins, added after
26.10.2, add 8 and 6 to those, and `hermes/guard-plugin` (26.10.4) 2 more to the
plugin version — 26.10.4 moved 39 and 25. Since 26.10.6 the plugin version also sets
`plugin_version` in `docs/_config.yml`, one file more (26). The shell floor grew by 16
with #66 (12 `mariadb-lsp` launchers, 2 `.lsp.json`, 2 docs-ref pages): 26.10.6 moved 55 and 26.
The shell-floor script also replaces the Hermes launchers' committed checksums,
`hermes/{dev,sql}-plugin/scripts/mariadb-shell-v<floor>.SHA256SUMS`, by downloading
that release's `SHA256SUMS` — so it needs network access and a published `v<floor>`,
and it stops before editing anything otherwise. The old file is deleted and the new
one is untracked: `git add` both directories' `scripts/` so the commit carries them.
A very different count is worth
looking into before going on. If a version was already at its target the script
changes nothing — say so, don't treat it as a failure. Commit each step on its
own so the PR is reviewable per step.

## 4. Re-vendor the skills

```bash
scripts/sync-skills.sh
```

No argument: it vendors the latest upstream `main`. Afterwards, **look at
`git status` rather than assuming the sync shipped something** — often only the
thirteen `skills-source.json` provenance files move (`hermes/guard-plugin` vendors
no skills, so it has none). Record, for the release notes:
the old → new upstream commits for `mariadb-docs` and `mariadb-shell` (from the
`skills-source.json` diffs), any skills added, removed or changed, and the skill
counts per variant (82 dev / 47 sql / 2 contributor as of 26.9.3). Commit.

## 5. Update the DevHub download links

The offline installation page (`docs/offline-install.md`) links straight to the
files this release ships, built from three places:

- `plugin_version` in `docs/_config.yml`: the ai-plugins source archives
  (`<repo>/archive/refs/tags/v<version>.tar.gz` and `.zip`). Set in step 3 by
  `set-plugin-version.sh`.
- `shell_floor` in `docs/_config.yml`: the mariadb-shell packages and
  `SHA256SUMS` of `v<floor>`. Set in step 3 by `set-mariadb-shell-version.sh`
  when the floor moved.
- `sandbox` in `docs/_data/downloads.yml`: the MariaDB Server sandbox packages
  (`release` and `versions`). No script sets it — check it here.

Check that both `_config.yml` keys hold this release's values:

```bash
grep -nE '^(plugin_version|shell_floor):' docs/_config.yml
```

**The sandbox packages.** Not every mariadb-shell release ships them (26.10.1
to 26.10.3 ship none; the shell's own index then points back at the newest one
that does). Find the newest release at or below the floor that carries
`*-sandbox.tar.gz` assets, and the server versions in it:

```bash
for t in $(gh release list --repo mariadb-corporation/mariadb-shell --exclude-drafts --limit 30 \
             --json tagName -q '.[].tagName' | sort -rV); do
  printf '%s\n%s\n' "${t#v}" "<floor>" | sort -CV || continue    # skip releases above the floor
  names=$(gh release view "$t" --repo mariadb-corporation/mariadb-shell --json assets \
            -q '.assets[].name | select(endswith("-sandbox.tar.gz"))')
  [ -n "$names" ] || continue
  echo "$t"; echo "$names" | sed -E 's/^mariadb-([0-9.]+)-.*/\1/' | sort -uV
  break
done
```

Compare the result with `sandbox.release` and `sandbox.versions` in
`docs/_data/downloads.yml`:

- **The same** → nothing to change; say so in the PR body.
- **Different** → update both keys and report old → new (for example "sandbox
  packages v26.10.0 → v26.11.0: 11.8.9, 12.3.3, 13.1.1 → 11.8.10, 12.3.4,
  13.1.2").
- **A platform missing**: every `platforms[].token` in `downloads.yml` must
  have a package for every version, and a `mariadb-shell-<floor>-<token>.tar.gz`
  in `v<floor>`. If an asset is missing, or the release carries a platform
  `downloads.yml` does not list, stop and report it — the table would link to a
  file that does not exist, or leave a platform out.

If the shell is installed locally at the floor, its index is the authority on
what it downloads; when it disagrees with the release listing, stop and report
it:

```bash
grep -oE 'releases/download/[^/]+' \
  ~/.local/share/mariadb-shell/<floor>/lib/mariadb-shell/plugins/mcp_plugin/lib/sandbox_server_versions.json | sort -u
```

Then build the site and check every GitHub link on the page. The archive links
for `v<version>` answer 404 until step 10 pushes the tag — expected here, but
every other link must answer 200:

```bash
npm run docs:build
grep -oE 'href="https://github.com/[^"]*"' docs/_site/offline-install/index.html \
  | sed 's/^href="//; s/"$//' | sort -u \
  | while read -r u; do c=$(curl -s -o /dev/null -I -L -w '%{http_code}' "$u"); [ "$c" = 200 ] || echo "$c $u"; done
```

Commit any change to `downloads.yml`.

## 6. CHANGELOG entries

Add a `## [<version>] - <today>` section to the top of all fourteen `*/*/CHANGELOG.md`
files, following the wording and structure of the previous release's section in
each file. Write only what actually changed in *that* plugin: the contributor
plugins have no MCP server, so no shell-floor line; the sql plugins have their
own skill count; `hermes/guard-plugin` has neither skills nor an MCP server, so
when nothing in it changed its section is the version bump alone. Mention the shell floor only when it moved in this release (then
name the new floor), and carry each plugin's `[Unreleased]` section, if it has
one, into the new section. Commit.

## 7. Verify

Run `./run_tests.py -m static` and report the result. If it fails, stop and show
the failure — do not open the PR on a red run.

## 8. Checkpoint

Run the `/checkpoint` command with `.` as the target, recording the release as
in progress (PR about to open) in `release-history.md`, `current-state.md` and
the index's "Latest work streams" and "Git state". Commit it on this branch so it
ships in the release PR.

## 9. Open the PR

```bash
git push -u origin wip/<version>
gh pr create --repo mariadb-corporation/ai-plugins --base main --head wip/<version> --title "Release <version>: …" --body-file <file>
```

Title in the style of #20 (`Release 26.9.3: shell floor, plugin version, and a
skills re-vendor`), naming what this release actually contains — leave out
"shell floor" when it didn't move. The body lists
each step with its file counts and the skill-sync findings, and ends with the
PR attribution line.

Then **stop and ask the user to review and merge the PR**, giving its URL. Do not
merge it yourself. Wait until the user says it is merged, then confirm with
`gh pr view <N> --repo mariadb-corporation/ai-plugins --json state,mergeCommit,headRefOid`
that `state` is `MERGED`, and note the squash commit.

## 10. Tag and publish the release

```bash
git switch main && git pull --ff-only origin main
```

Create an annotated tag `v<version>` on the squash commit. The annotation's body is the
release notes: a short prose summary in the style of the v26.9.3 release (read it
with `gh release view v26.9.3 --repo mariadb-corporation/ai-plugins`). It states
the mariadb-shell floor the release requires and whether it moved, and ends with
"See each plugin's CHANGELOG.md [<version>] section for details."

Push the **same tag object** to both remotes (`git push origin v<version>` and
`git push fork v<version>`) and verify with `git ls-remote --tags <remote> v<version>`, once per remote, that both
point at the same object.

Publish a **prerelease** on both repos. `gh` refuses `--notes-from-tag` together
with `--repo`, so extract the body to a file first:

```bash
git tag -l --format='%(contents:body)' v<version> > <scratch>/notes.md
gh release create v<version> --repo <repo> --title v<version> --notes-file <scratch>/notes.md --prerelease --verify-tag
```

for `<repo>` = `mariadb-corporation/ai-plugins` and `mariadb/ai-plugins`.

## 11. Sync the fork

The fork's `main` carries the same tree as `origin/main`, `docs/CNAME`
(`ai-plugins.mariadb.org`) included — the fork's Pages is what serves it. Sync with a **merge** of
`origin/main` into `fork/main`, never a reset or force push (a fast-forward when
the fork has no commits of its own). Since 26.9.5 the fork's `main` *is*
`origin/main` (same commit), so this is expected to be a plain fast-forward:

```bash
git fetch fork
git switch -c sync/fork-<version> fork/main
git merge origin/main -m "Sync with mariadb-corporation/ai-plugins main (#<PR>)"
```

(add the commit attribution line to the message if a merge commit is made.) A
conflict means someone committed to the fork directly — stop and show it.

Before pushing, verify:

- `git diff origin/main HEAD` is empty.

If it is not, stop and show it. Otherwise push with
`git push fork HEAD:main` (a fast-forward of the fork's `main`; it will be
refused if the fork moved meanwhile — then fetch and merge again, don't force).
Return to `main` and delete the local `wip/<version>` and `sync/fork-<version>` branches, and
delete `wip/<version>` on `origin` once its remote head matches the PR's `headRefOid`.

## 12. Bump the Hermes plugin catalog

Hermes users install `mariadb-dev`, `mariadb-sql` and `mariadb-guard` by name
from the Hermes plugin catalog: one file each, `plugin-catalog/mariadb-<name>.yaml`
in `NousResearch/hermes-agent` (added by NousResearch/hermes-agent#145982). Each
entry pins an exact commit of the **public** repo `mariadb/ai-plugins` (`subdir:
hermes/<dev|sql|guard>-plugin`), and the catalog never follows `main`: a release
reaches Hermes users only through a PR that moves `sha` and `version` in all three
entries. The catalog's rules are in
[`plugin-catalog/README.md`](https://github.com/NousResearch/hermes-agent/blob/main/plugin-catalog/README.md);
read them again when anything below is refused.

Work in the scratchpad, never in this repo. Let `<pin>` be the squash commit of
step 9 (`fork/main` after step 11, so the same commit).

**The pin must be public.** `git ls-remote https://github.com/mariadb/ai-plugins
refs/heads/main` must print `<pin>`. If it does not, step 11 did not land — stop.

**Find the open entry PR first.** `gh pr list --repo NousResearch/hermes-agent
--author @me --state open --search "mariadb in:title"`. If a previous bump (or
the original #145982) is still open, do not open a second PR: push the new pin to
that PR's branch, retitle it to this version, and say in a comment which
release it now pins. Otherwise open a new one as below.

**Validate at the pin**, exactly as the catalog CI does. Clone
`https://github.com/mariadb/ai-plugins` into the scratchpad, check out `<pin>`,
and run, with `HERMES_HOME` pointing into the scratchpad so `~/.hermes` is left
alone:

```bash
HERMES_HOME=<scratch>/hh hermes plugins validate --install-deps <scratch>/ai-plugins/hermes/<dev|sql|guard>-plugin </dev/null
```

Every one must end in `Validation passed`, with `security scan — safe`. Read every
warning: a `caution` finding goes to the reviewer, so name it in the PR body.
If no `hermes` is installed, install upstream `main` into a scratch venv (Python
3.11–3.14; `pip install -e <scratch>/hermes-agent`). On 3.14 its `Pillow` pin
clashed with `browser-harness` in October 2026; installing the `pyproject.toml`
dependencies without `browser-harness`, then Hermes with `--no-deps`, was enough
for `validate`. Never submit without a passing local run.

**Edit the three entries.** In a scratch clone of `NousResearch/hermes-agent`
(`--depth 1` is enough), on a branch `catalog-mariadb-<version>`, change in each of
`plugin-catalog/mariadb-dev.yaml`, `mariadb-sql.yaml` and `mariadb-guard.yaml`:

- `sha:` → `<pin>` (all 40 hex characters);
- `version:` → `"<version>"` (quoted);
- the skill counts in the `dev` and `sql` descriptions (`85 skills`, `47 skills`
  as of 26.10.6) → this release's counts from step 4;
- anything else this release made untrue: the disclosure text (how the launcher
  installs mariadb-shell, what it downloads), `capabilities.provides_hooks` of
  `mariadb-guard` against `provides_hooks` in `hermes/guard-plugin/plugin.yaml`,
  and `requires_hermes` when a package now needs a newer Hermes.

Then run the catalog's own schema check, which must end in `OK`:

```bash
python3 scripts/validate_plugin_catalog.py plugin-catalog/
```

**Commit and open the PR.** The catalog CI fails commits whose author email is not
mapped to a GitHub login, and a GitHub noreply address needs no mapping. Commit as
the `gh` user's noreply address (`gh api user --jq '"\(.id)+\(.login)@users.noreply.github.com"'`)
rather than adding a file under `contributors/emails/`. A catalog PR may touch
only `plugin-catalog/**` (and `contributors/emails/**`); CI refuses anything else.

```bash
gh repo fork NousResearch/hermes-agent --clone=false   # once per account; a no-op afterwards
git push -u https://github.com/<gh-login>/hermes-agent.git catalog-mariadb-<version>
gh pr create --repo NousResearch/hermes-agent --base main --head <gh-login>:catalog-mariadb-<version> \
  --title "catalog: bump mariadb-dev, mariadb-sql and mariadb-guard to <version>" --body-file <file>
```

The PR must come from a maintainer of `mariadb/ai-plugins` (catalog rule 5): check
`gh api repos/mariadb/ai-plugins --jq .permissions.maintain` is `true` for the `gh`
user. Reviewers read the commit range being adopted (rule 4), so the body names
the old → new pin with its compare link
(`https://github.com/mariadb/ai-plugins/compare/<old-sha>...<pin>`), summarises
what changed in the three Hermes packages (from the CHANGELOGs of step 6), states
the local `validate` result, and repeats any change to the disclosures. It ends
with the PR attribution line.

Do not wait for the merge — a maintainer reviews catalog PRs in batches, usually
within one to three days. Report the PR URL in step 13. If the reviewers ask for
changes to the plugins themselves, that is a new ai-plugins release, not an edit
to the entry.

## 13. Report

Tell the user the release is published, with:

- the merged PR and its squash commit
- the tag `v<version>` and its tag object
- both release URLs
- that the fork is synced and its tree matches `origin/main`
- the Hermes catalog PR (step 12), its pin and the local `validate` result
- anything that did not go as expected

Then record the finished release with `/checkpoint .` and open a small PR for it,
as was done after 26.9.3 (#21).
