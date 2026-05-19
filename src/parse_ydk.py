"""Utilities for parsing YGOPro `.ydk` decklists."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

SECTION_MARKERS = {
    "#main": "main",
    "#extra": "extra",
    "!side": "side",
}


def parse_ydk_file(path: Path) -> dict[str, dict[int, int]]:
    """Parse a `.ydk` file into section-level card quantities."""

    if not path.exists():
        raise FileNotFoundError(f"Deck file not found: {path}")

    sections: dict[str, Counter[int]] = {
        "main": Counter(),
        "extra": Counter(),
        "side": Counter(),
    }
    current_section: str | None = None
    saw_main = False

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line in SECTION_MARKERS:
                current_section = SECTION_MARKERS[line]
                if current_section == "main":
                    saw_main = True
                continue
            if line.startswith("#") or line.startswith("!"):
                continue
            if current_section is None:
                raise ValueError(
                    f"Invalid YDK format in {path.name}: card ID before a deck section on line {line_number}."
                )
            try:
                card_id = int(line)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid card ID '{line}' in {path.name} on line {line_number}. Expected an integer."
                ) from exc
            sections[current_section][card_id] += 1

    if not saw_main:
        raise ValueError(f"Invalid YDK format in {path.name}: missing #main section.")

    return {section: dict(counter) for section, counter in sections.items()}
