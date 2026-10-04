# Personal Pantheon fork

This checkout maintains personal ltui and jtui customizations on upstream
`runpantheon/ltui` revision `598c4039999e07b3dc03f4f199ccab8d63648dc5`.
The upstream README describes stock behavior. This file describes the fork.
Shortcut is unchanged. Preserve upstream LICENSE, NOTICE, and attribution.

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

## Checks

Use a Python environment with Textual, httpx, and watchfiles installed:

```sh
FLUME_RUNTIME=/absolute/path/to/flume.nvim PYTHON=/path/to/venv/bin/python ./scripts/check
```

The tests cover manual ordering, pagination failure, focus filters, milestone
ordering, theme loading, atomic marker watching, repository hints, and native
Textual theme/sidebar changes in both applications. Native tests stub credential
loading and application startup; they do not contact tracker APIs.
