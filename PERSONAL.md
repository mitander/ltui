# Personal ltui fork

This checkout at `~/c/p/ltui` maintains personal ltui and jtui customizations
on upstream `runpantheon/ltui` revision
`59da9ba656a14e37989e98d3e18a9d948a3ae158`.
The upstream README describes stock behavior. This file describes the fork.
Shortcut retains upstream behavior with local rendering refactors.
Preserve upstream LICENSE, NOTICE, and attribution.

## Behavior

- Load all four Flume palettes and follow the shared active-schema marker.
- Map application chrome, workflow states, and identity colors to Flume roles.
- Resolve CSS colors at theme-change time, not at module import.
- Start with the sidebar hidden; `b` toggles and persists its visibility.
- Prefer `TRACKER_SCOPE`, then `TRACKER_REPOSITORY`, for scope selection.
  Without a match, show the sidebar rather than silently selecting a saved team.
- In ltui, `f` toggles Now and next (started/unstarted) versus all issues.
  Sort by Linear manual order, not assignment or update time. Unknown cached
  ranks sort last and display `?`. Pagination fetches the complete team queue.
- Add milestone grouping and detail metadata in ltui.

These changes are maintained directly in application source. The old dotfiles
replacement script was applied once during migration; it is not a build input.

## Flume adapter

`flume-theme/generate.lua` owns Pantheon-specific color generation. It reads
`flume.palette` canonical schema metadata and semantic roles. It does not call
Flume's compiler or activate a palette, and contains no copied palette colors.

Install the adapter and both applications together:

```sh
python3 -m pip install ./flume-theme ./ltui ./jtui
```

Generate themes before launch:

```sh
FLUME_RUNTIME=/absolute/path/to/flume.nvim \
FLUME_TRACKER_OUTPUT=/absolute/path/to/generated-themes \
nvim --headless --clean -l flume-theme/generate.lua
```

Set `FLUME_TRACKER_THEME_DIR` to that output and `FLUME_SCHEMA_FILE` to Flume's
`extras/current/schema`. The loader watches atomic active-set swaps. Palette
source edits require regeneration and an application restart; schema switches
among loaded themes do not.

Dotfiles `home/common.nix` builds a hash-pinned local snapshot of this checkout,
builds the adapter, generates themes from the current canonical palette source,
and supplies both environment defaults. It does not deploy during validation.
A remote source pin requires publishing this fork separately.

## Maintain the fork

`main` tracks `upstream/main` without personal changes. `flume-personal` carries
the local commits. The `upstream` remote points to `runpantheon/ltui`; no personal
`origin` remote is configured yet. Add `origin` when publishing your own fork.
Do not push the personal branch to `upstream`.

Update from a clean working tree:

```sh
git switch flume-personal
git fetch upstream
git branch backup/flume-personal-before-update
git rebase upstream/main
```

Use a new backup branch name for subsequent updates. Resolve conflicts by
preserving both upstream behavior and the personal behavior documented above.
Use `git rebase --abort` to cancel an update. Compare the old and new commit
series with `git range-diff`, then run the checks below before publishing.
After validation, update the clean mirror with `git branch -f main upstream/main`.
Refresh the dotfiles source hash as described in `dotfiles/tracker-tui/README.md`.

Keep new commits focused on one behavior. Match surrounding code style and avoid
unrelated formatting changes: they increase conflicts without adding behavior.
Extract upstream contributions onto a separate branch based on `upstream/main`,
without the Flume adapter or personal defaults. Complete queue pagination is a
candidate because the upstream query otherwise truncates queues at 250 issues.

Before submitting a PR, read `CONTRIBUTING.md`. Submission grants Pantheon the
right to include the contribution in its commercial versions, in addition to GPL.

## Checks

Use a Python environment with Textual, httpx, and watchfiles installed:

```sh
FLUME_RUNTIME=/absolute/path/to/flume.nvim PYTHON=/path/to/venv/bin/python ./scripts/check
```

The tests cover manual ordering, pagination failure, focus filters, milestone
ordering, theme loading, atomic marker watching, repository hints, and native
Textual theme/sidebar changes in both applications, plus upstream's due-date
helpers, row layout, and modal layout. Native tests stub credential loading and
application startup; they do not contact tracker APIs.
