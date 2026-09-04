"""CLI entrypoint for the YGO MetaPulse ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.config import DECKS_DIR, DECK_METADATA_DIR, TOURNAMENT_DECK_METADATA_DIR, TOURNAMENT_DECKS_DIR
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


def ingest_decks(dataset_mode: str = "auto") -> int:
    """Parse all available decklists and store them idempotently."""

    init_db()
    deck_files, deck_mode = _select_deck_files(dataset_mode=dataset_mode)
    ingested_count = 0
    active_slugs: list[str] = []

    for deck_path in deck_files:
        metadata_path = _metadata_path_for(deck_path, deck_mode)
        if not metadata_path.exists():
            logger.warning("Skipping %s because metadata file is missing: %s", deck_path.name, metadata_path.name)
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        parsed_deck = parse_ydk_file(deck_path)
        insert_or_update_deck(deck_path.stem, metadata, parsed_deck)
        active_slugs.append(deck_path.stem)
        ingested_count += 1

    if deck_mode in {"tournament", "imported"} and not active_slugs:
        logger.warning(
            "Imported deck files were detected, but none had matching metadata JSON files. "
            "Clearing stored deck data to avoid showing stale sample analytics."
        )
        delete_decks_not_in([])
    elif active_slugs:
        delete_decks_not_in(active_slugs)

    logger.info("Ingested %s %s decklist(s).", ingested_count, deck_mode)
    return ingested_count


def run_full_ingestion(force_refresh: bool = False, dataset_mode: str = "auto") -> None:
    """Run the full metadata, sample data, and deck ingestion workflow."""

    ensure_sample_metadata_files(overwrite=False)
    tournament_deck_files = _discover_tournament_deck_files()
    legacy_real_deck_files, sample_deck_files = _discover_sample_area_deck_files()
    cards = ingest_cards(force_refresh=force_refresh)
    if dataset_mode == "sample":
        if not sample_deck_files:
            ensure_sample_deck_files(cards, overwrite=False)
    elif tournament_deck_files:
        logger.info("Detected verified tournament deck files in %s. Skipping sample deck generation.", TOURNAMENT_DECKS_DIR)
    elif legacy_real_deck_files:
        logger.info("Detected imported deck files in %s. Skipping sample deck generation.", DECKS_DIR)
    elif sample_deck_files:
        logger.info("Using existing sample deck files in %s.", DECKS_DIR)
    else:
        ensure_sample_deck_files(cards, overwrite=False)
    ingest_decks(dataset_mode=dataset_mode)


def parse_args() -> argparse.Namespace:
    """Parse command-line options for local ingestion runs."""

    parser = argparse.ArgumentParser(description="Fetch card metadata and rebuild the local YGO MetaPulse database.")
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Refresh card metadata from the YGOPRODeck API instead of using the local cache.",
    )
    parser.add_argument(
        "--dataset",
        choices=["auto", "tournament", "sample"],
        default="auto",
        help="Deck dataset to load. Auto prefers verified tournament imports, then local imports, then samples.",
    )
    return parser.parse_args()


def _discover_sample_area_deck_files() -> tuple[list[Path], list[Path]]:
    """Return non-sample and sample deck files from the configured deck directory."""

    all_decks = sorted(DECKS_DIR.glob("*.ydk"))
    real_decks = [path for path in all_decks if not path.stem.startswith(SAMPLE_PREFIX)]
    sample_decks = [path for path in all_decks if path.stem.startswith(SAMPLE_PREFIX)]
    return real_decks, sample_decks


def _discover_tournament_deck_files() -> list[Path]:
    """Return validated YGOPRODeck tournament deck files."""

    return sorted(TOURNAMENT_DECKS_DIR.glob("*.ydk"))


def _select_deck_files(dataset_mode: str = "auto") -> tuple[list[Path], str]:
    """Prefer verified tournament decklists over generated sample decklists."""

    if dataset_mode not in {"auto", "tournament", "sample"}:
        raise ValueError("dataset_mode must be one of: auto, tournament, sample")

    tournament_decks = _discover_tournament_deck_files()
    legacy_real_decks, sample_decks = _discover_sample_area_deck_files()
    if dataset_mode == "tournament":
        logger.info("Selected tournament deck mode with %s file(s).", len(tournament_decks))
        return tournament_decks, "tournament"
    if dataset_mode == "sample":
        logger.info("Selected sample deck mode with %s file(s).", len(sample_decks))
        return sample_decks, "sample"
    if tournament_decks:
        logger.info("Detected %s verified tournament decklist file(s). Sample decks will be ignored.", len(tournament_decks))
        return tournament_decks, "tournament"
    if legacy_real_decks:
        logger.info("Detected %s imported decklist file(s). Sample decks will be ignored.", len(legacy_real_decks))
        return legacy_real_decks, "imported"
    return sample_decks, "sample"


def _metadata_path_for(deck_path: Path, deck_mode: str) -> Path:
    if deck_mode == "tournament":
        return TOURNAMENT_DECK_METADATA_DIR / f"{deck_path.stem}.json"
    return DECK_METADATA_DIR / f"{deck_path.stem}.json"


def main() -> None:
    """Run the ingestion workflow as a module."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = parse_args()
    run_full_ingestion(force_refresh=args.force_refresh, dataset_mode=args.dataset)


if __name__ == "__main__":
    main()
