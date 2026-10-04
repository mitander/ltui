"""Load and follow Flume themes for the Pantheon tracker TUI suite."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path

from textual.theme import Theme
from watchfiles import awatch

_ROLES: dict[str, dict[str, str]] = {}
_CHROME_ROLES = {
    "C_TEXT": "text",
    "C_SUB": "text_subtle",
    "C_DIM": "text_muted",
    "C_FAINT": "border",
    "C_VFAINT": "border_subtle",
    "C_BLUE": "accent",
    "C_LAV": "accent_tertiary",
    "C_PEACH": "warning",
    "C_GREEN": "success",
    "C_RED": "error",
    "C_MAUVE": "accent_secondary",
}


def _theme_dir() -> Path | None:
    value = os.environ.get("FLUME_TRACKER_THEME_DIR")
    return Path(value).expanduser() if value else None


def _schema_file() -> Path | None:
    value = os.environ.get("FLUME_SCHEMA_FILE")
    return Path(value).expanduser() if value else None


def _read_theme(path: Path, app: str) -> Theme:
    data = json.loads(path.read_text())
    name = data["name"]
    variables = data["variables"]
    prefix = f"{app}-"
    textual_variables = {
        prefix + "border": variables["border"],
        prefix + "border-focus": variables["border_focus"],
        prefix + "border-detail": variables["border_detail"],
        prefix + "modal-bg": variables["modal_bg"],
        prefix + "cursor": variables["cursor"],
        prefix + "overlay": variables["overlay"],
        "scrollbar": variables["scrollbar"],
        "scrollbar-hover": variables["scrollbar_hover"],
        "scrollbar-active": variables["scrollbar_active"],
        "scrollbar-background": variables["scrollbar_background"],
        "screen-selection-background": variables["selection_background"],
        "screen-selection-foreground": variables["selection_foreground"],
        "input-selection-background": variables["selection_background"],
    }
    roles = data["roles"]
    for constant, role in _CHROME_ROLES.items():
        variable = "tracker-" + constant.removeprefix("C_").lower().replace("_", "-")
        textual_variables[variable] = roles[role]
    textual_variables.update(
        {
            "text": roles["text"],
            "text-muted": roles["text_muted"],
            "text-disabled": roles["text_muted"],
            "text-primary": roles["accent"],
            "text-secondary": roles["accent_secondary"],
            "text-accent": roles["accent_tertiary"],
            "text-warning": roles["warning"],
            "text-error": roles["error"],
            "text-success": roles["success"],
            "foreground-muted": roles["text_muted"],
            "foreground-disabled": roles["text_muted"],
            "primary-muted": data["variables"]["cursor"],
            "secondary-muted": data["variables"]["cursor"],
            "accent-muted": data["variables"]["cursor"],
            "warning-muted": data["variables"]["cursor"],
            "error-muted": data["variables"]["cursor"],
            "success-muted": data["variables"]["cursor"],
            "block-cursor-foreground": roles["text"],
            "block-cursor-background": data["variables"]["cursor"],
            "block-cursor-blurred-foreground": roles["text_subtle"],
            "block-cursor-blurred-background": data["variables"]["cursor"],
            "block-hover-background": data["variables"]["cursor"],
            "border": data["variables"]["border_focus"],
            "border-blurred": data["variables"]["border"],
            "surface-active": data["variables"]["cursor"],
            "footer-foreground": roles["text_subtle"],
            "footer-background": data["panel"],
            "footer-key-foreground": roles["accent"],
            "footer-description-foreground": roles["text_subtle"],
            "input-cursor-background": roles["text"],
            "input-cursor-foreground": data["background"],
            "input-selection-foreground": data["variables"]["selection_foreground"],
            "button-foreground": roles["text"],
            "button-color-foreground": data["variables"]["selection_foreground"],
            "link-background-hover": data["variables"]["cursor"],
            "link-color": roles["accent"],
            "link-color-hover": roles["accent_tertiary"],
            "markdown-h1-color": roles["accent"],
            "markdown-h2-color": roles["accent"],
            "markdown-h3-color": roles["accent_secondary"],
            "markdown-h4-color": roles["text"],
            "markdown-h5-color": roles["text_subtle"],
            "markdown-h6-color": roles["text_muted"],
        }
    )
    _ROLES[name] = roles
    return Theme(
        name=name,
        primary=data["primary"],
        secondary=data["secondary"],
        accent=data["accent"],
        background=data["background"],
        surface=data["surface"],
        panel=data["panel"],
        foreground=data["foreground"],
        success=data["success"],
        warning=data["warning"],
        error=data["error"],
        dark=data["dark"],
        luminosity_spread=0.0,
        text_alpha=1.0,
        variables=textual_variables,
    )


def load_flume_themes(app: str) -> list[Theme]:
    root = _theme_dir()
    if root is None or not root.is_dir():
        return []
    themes = []
    for path in sorted(root.glob("flume-*.json")):
        try:
            themes.append(_read_theme(path, app))
        except (OSError, KeyError, TypeError, ValueError):
            continue
    return themes


def theme_roles(name: str) -> dict[str, str] | None:
    return _ROLES.get(name)


def theme_palette(name: str) -> dict[str, str] | None:
    roles = theme_roles(name)
    if roles is None:
        return None
    return {constant: roles[role] for constant, role in _CHROME_ROLES.items()}


def active_flume_theme() -> str | None:
    path = _schema_file()
    if path is None:
        return None
    try:
        schema = path.read_text().strip()
    except OSError:
        return None
    return f"flume-{schema}" if schema else None


async def watch_flume_theme_changes() -> AsyncIterator[str]:
    schema_file = _schema_file()
    if schema_file is None:
        return
    extras = schema_file.parent.parent
    if not extras.is_dir():
        return
    previous = active_flume_theme()
    async for _changes in awatch(extras, recursive=False):
        current = active_flume_theme()
        if current and current != previous:
            previous = current
            yield current
