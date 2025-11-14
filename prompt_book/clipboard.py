"""Utilities for copying text to the system clipboard."""

from __future__ import annotations

import shutil
import subprocess
from typing import Tuple


def copy_to_clipboard(text: str) -> Tuple[bool, str]:
    """Copy *text* to the system clipboard.

    The function attempts a series of strategies that work across operating systems
    without requiring external dependencies.  When no strategy succeeds it returns
    ``False`` together with an explanation so callers can gracefully degrade by
    showing the text to the user for manual copying.
    """

    strategies = [
        ("pyperclip", _pyperclip_copy),
        ("pbcopy", _pbcopy_copy),
        ("xclip", _xclip_copy),
        ("wl-copy", _wlcopy_copy),
        ("clip", _clip_copy),
    ]

    for name, strategy in strategies:
        try:
            strategy(text)
            return True, f"Copied using {name}"
        except Exception:
            continue

    return False, "Unable to access the clipboard. Text printed to stdout instead."


def _pyperclip_copy(text: str) -> None:
    try:
        import pyperclip  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError("pyperclip is unavailable") from exc

    pyperclip.copy(text)


def _pbcopy_copy(text: str) -> None:
    if shutil.which("pbcopy") is None:
        raise RuntimeError("pbcopy is unavailable")
    _run_copy_command(["pbcopy"], text)


def _xclip_copy(text: str) -> None:
    if shutil.which("xclip") is None:
        raise RuntimeError("xclip is unavailable")
    _run_copy_command(["xclip", "-selection", "clipboard"], text)


def _wlcopy_copy(text: str) -> None:
    if shutil.which("wl-copy") is None:
        raise RuntimeError("wl-copy is unavailable")
    _run_copy_command(["wl-copy"], text)


def _clip_copy(text: str) -> None:
    if shutil.which("clip") is None:
        raise RuntimeError("clip is unavailable")
    _run_copy_command(["clip"], text)


def _run_copy_command(command: list[str], text: str) -> None:
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = process.communicate(text)
    if process.returncode != 0:
        raise RuntimeError(f"Clipboard command failed: {stderr or stdout}")
