"""CLI entrypoint for the YGO MetaPulse ingestion pipeline."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.config import DECKS_DIR, DECK_METADATA_DIR
from src.db import delete_decks_not_in, init_db, insert_or_update_deck, upsert_cards
from src.fetch_cards import fetch_cards
from src.parse_ydk import parse_ydk_file
from src.sample_data import ensure_sample_deck_files, ensure_sample_metadata_files

logger = logging.getLogger(__name__)
SAMPLE_PREFIX = "sample_"


def ingest_cards(force_refresh: bool = False) -> list[dict]:
    """Fetch card metadata and store it in SQLite."""

    init_db()
    cards = fetch_cards(force_refresh=force_refresh)
    upsert_cards(cards)
    logger.info("Ingested %s cards.", len(cards))
    return cards


def ingest_decks() -> int:
    """Parse all available decklists and store them idempotently."""

    init_db()
    deck_files, deck_mode = _select_deck_files()
    ingested_count = 0
    active_slugs: list[str] = []

    for deck_path in deck_files:
        metadata_path = DECK_METADATA_DIR / f"{deck_path.stem}.json"
        if not metadata_path.exists():
            logger.warning("Skipping %s because metadata file is missing: %s", deck_path.name, metadata_path.name)
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        parsed_deck = parse_ydk_file(deck_path)
        insert_or_update_deck(deck_path.stem, metadata, parsed_deck)
        active_slugs.append(deck_path.stem)
        ingested_count += 1

    if deck_mode == "real" and not active_slugs:
        logger.warning(
            "Real deck files were detected, but none had matching metadata JSON files. "
            "Clearing stored deck data to avoid showing stale sample analytics."
        )
        delete_decks_not_in([])
    elif active_slugs:
        delete_decks_not_in(active_slugs)

    logger.info("Ingested %s %s decklist(s).", ingested_count, deck_mode)
    return ingested_count


def run_full_ingestion(force_refresh: bool = False) -> None:
    """Run the full metadata, sample data, and deck ingestion workflow."""

    ensure_sample_metadata_files(overwrite=True)
    real_deck_files = _discover_deck_files()[0]
    cards = ingest_cards(force_refresh=force_refresh)
    if real_deck_files:
        logger.info("Detected real deck files in %s. Skipping sample deck generation.", DECKS_DIR)
    else:
        ensure_sample_deck_files(cards, overwrite=True)
    ingest_decks()


def _discover_deck_files() -> tuple[list[Path], list[Path]]:
    """Return non-sample and sample deck files from the configured deck directory."""

    all_decks = sorted(DECKS_DIR.glob("*.ydk"))
    real_decks = [path for path in all_decks if not path.stem.startswith(SAMPLE_PREFIX)]
    sample_decks = [path for path in all_decks if path.stem.startswith(SAMPLE_PREFIX)]
    return real_decks, sample_decks


def _select_deck_files() -> tuple[list[Path], str]:
    """Prefer real decklists over generated sample decklists."""

    real_decks, sample_decks = _discover_deck_files()
    if real_decks:
        logger.info("Detected %s real decklist file(s). Sample decks will be ignored.", len(real_decks))
        return real_decks, "real"
    return sample_decks, "sample"


def main() -> None:
    """Run the ingestion workflow as a module."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    run_full_ingestion()


if __name__ == "__main__":
    main()
