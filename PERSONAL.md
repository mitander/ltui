# Personal ltui fork

This checkout at `~/c/p/ltui` maintains personal ltui and jtui customizations
on upstream `runpantheon/ltui` revision
`cc3a03641a70b6a034c4ae9b19b1f4a69f5d728e`.
The upstream README describes stock behavior. This file describes the fork.
Shortcut retains upstream behavior with local rendering refactors.
Preserve upstream LICENSE, NOTICE, and attribution.

## Behavior

- Load all four Flume palettes and follow the shared active-schema marker.
- Map application chrome, workflow states, and identity colors to Flume roles. Context uses purple,
  controls and focused input cursors use the action accent, and secondary text uses readable muted
  ink. Retained-ink focus rows stay on the quiet active-element surface.
- Resolve CSS colors at theme-change time, not at module import.
- Start with the sidebar hidden; `b` toggles and persists its visibility.
- Prefer `TRACKER_SCOPE`, then `TRACKER_REPOSITORY`, for scope selection.
  Without a match, show the sidebar rather than silently selecting a saved team.
- In ltui, `p` (or `V`) chooses a project, `f` chooses included statuses, and
  `v` chooses grouping. These controls are independent. Default to status
  sections with In Progress, Todo, Backlog, and Done. Exclude canceled and triage
  unless All statuses is selected. Priority uses `P`, and moving a ticket to a
  project uses `M`. Custom keybindings still override these defaults.
- Sort by Linear manual order, not assignment or update time. Active view
  numbers Todo issues. Unknown cached ranks sort last and display `?` there.
  Pagination fetches the complete team queue.
- Add milestone grouping and detail metadata in ltui.

These changes are maintained directly in application source. The old dotfiles
replacement script was applied once during migration; it is not a build input.

## Project context in ltui

Launch ltui inside a checkout to select its matching project automatically.
Matching ignores case, spaces, and punctuation, but requires one unique project
name. Projects come from the loaded team's issues. With no match or an ambiguous
match, show all projects in the current team.

The repository hint is `TRACKER_REPOSITORY`, or the Git root directory name when
unset. Outside Git, use the current directory name. To override the project hint:

```sh
TRACKER_SCOPE=dev TRACKER_PROJECT="Project name or ID" ltui
```

Team selection still uses `TRACKER_SCOPE` and `TRACKER_REPOSITORY`. Project
matching does not change teams or Linear credentials. `TRACKER_PROJECT` takes
precedence over the repository hint for project matching only.

`p` offers All projects and individual projects alphabetically. A manual choice,
including All projects, takes precedence over inference and persists per
checkout, workspace, and team. Select another project with `p` to change it.
Status and grouping preferences persist independently. Old `focus` preferences
are replaced by the Workflow status default on the first launch after upgrading.
The top app header contains only ltui branding. Workspace, team and project context remain in the
board title rather than repeating account and team labels above it.

`f` offers Workflow (In Progress, Todo, Backlog, Done), Active (In Progress,
Todo), All statuses, and each of the four workflow types individually. `v`
shows an explicit menu for status, project, milestone, or initiative grouping.
Only sections containing matching issues appear. The board title shows the
workspace, team, and project, and its subtitle shows statuses, grouping, and order.

## Flume adapter

`flume-theme/flume_tracker_theme.py` maps Flume's version-1 semantic palette
exports to tracker and Textual roles. It reads local JSON without compiling,
activating, or copying a palette. Older generated Textual palettes remain readable.

Install the adapter and both applications together in an active virtual environment:

```sh
python -m pip install -e ./flume-theme -e ./ltui -e ./jtui
```

Set `FLUME_TRACKER_THEME_DIR` to Flume's `extras/palette` directory and
`FLUME_SCHEMA_FILE` to `extras/current/schema`. The loader watches atomic
active-set swaps. After editing palette colors, run Flume's normal compile/sync
command and restart the application. Switching among loaded schemas stays live.
No separate Textual export, Neovim subprocess, or Nix build is needed.

Editable installation runs application and adapter code from this checkout.
Restart after Python edits. Reinstall only after changing dependencies or package
metadata, not after each source edit. The dotfiles `scripts/setup-trackers` command
sets up this editable environment and its launchers provide the Flume paths.
See `~/dotfiles/tracker-tui/README.md` for setup details.

## Maintain the fork

`main` is the maintained fork and the default branch on `mitander/ltui`.
It tracks `origin/main`, including the personal changes. `upstream/main` is the
clean upstream reference, so no separate local mirror branch is needed.
The `origin` remote points to `mitander/ltui`. The `upstream` remote points to
`runpantheon/ltui`. Push fork changes only to `origin`, never to `upstream`.
The old `flume-personal` branch remains as a historical reference, not an active
maintenance branch. Use short-lived branches for new changes.

Update from a clean working tree:

```sh
git switch main
git fetch origin
git merge --ff-only origin/main
git fetch upstream
git merge --no-ff upstream/main
```

Resolve conflicts by preserving both upstream behavior and the personal behavior
documented above. Use `git merge --abort` to cancel an unfinished merge.
Inspect the merge diff and run the checks below before publishing with
`git push origin main`. Update the upstream revision at the top of this file
when integrating upstream changes. Do not rebase or force-push published fork
history. If the fast-forward from `origin/main` fails, inspect the divergence
rather than resetting either side.

Local editable installations use this checkout directly. Publishing is not required
to try source changes.

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
