"""Format directory listings into concise, human-friendly summaries."""

from __future__ import annotations

from typing import List, Optional, Tuple
import re


_WIN_DIR_ENTRY = re.compile(
    r"^(?P<mode>[d-][a-z-]{4,})\s+\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}\s+(?:(?P<size>\d+)\s+)?(?P<name>.+)$"
)


def _wants_full_listing(message: str) -> bool:
    lowered = message.lower()
    triggers = [
        "pełny",
        "pelny",
        "pełna lista",
        "pelna lista",
        "pełen listing",
        "pelny listing",
        "pokaż wszystko",
        "pokaz wszystko",
        "pokaż pełny",
        "pokaz pelny",
        "całość",
        "calosc",
        "show all",
        "full listing",
        "list all",
    ]
    return any(t in lowered for t in triggers)


def _summarize_items(items: List[str], limit: int = 8) -> str:
    if not items:
        return "brak"
    if len(items) <= limit:
        return ", ".join(items)
    return ", ".join(items[:limit]) + f", ... (+{len(items) - limit})"


def _parse_windows_dir(output: str) -> Tuple[Optional[str], List[str], List[str]]:
    path = None
    dirs: List[str] = []
    files: List[str] = []

    for line in output.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("Directory:"):
            path = line.split("Directory:", 1)[1].strip()
            continue
        match = _WIN_DIR_ENTRY.match(line)
        if not match:
            continue
        name = match.group("name").strip()
        mode = match.group("mode")
        if mode.startswith("d"):
            dirs.append(name)
        else:
            files.append(name)

    return path, dirs, files


def _parse_unix_ls(output: str) -> Tuple[Optional[str], List[str]]:
    items: List[str] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("total "):
            continue
        items.append(line)
    return None, items


def format_listing_output(
    output: str, user_message: str, platform: str = "win"
) -> str:
    """Format listing output for user display.

    If user explicitly asks for full listing, return raw output in code block.
    Otherwise, return a concise summary with counts and a short sample list.
    """
    if _wants_full_listing(user_message):
        return f"```\n{output}\n```"

    is_windows = platform.startswith("win")

    if is_windows:
        path, dirs, files = _parse_windows_dir(output)
        total = len(dirs) + len(files)
        header = f"W tym katalogu{f' ({path})' if path else ''} znalazłem:"
        summary = f"- katalogi: {len(dirs)}\n- pliki: {len(files)}"
        if total == 0:
            summary = "- brak wpisów"
        details = []
        if dirs:
            details.append(f"Katalogi: {_summarize_items(dirs)}")
        if files:
            details.append(f"Pliki: {_summarize_items(files)}")
        hint = "Jeśli chcesz pełny listing, napisz: pokaż pełny listing."
        return "\n".join([header, summary] + details + [hint])

    # Unix fallback
    _, items = _parse_unix_ls(output)
    header = "W tym katalogu znalazłem:"
    summary = f"- pozycje: {len(items)}"
    details = f"Przykład: {_summarize_items(items)}" if items else "brak wpisów"
    hint = "Jeśli chcesz pełny listing, napisz: pokaż pełny listing."
    return "\n".join([header, summary, details, hint])


__all__ = ["format_listing_output"]
