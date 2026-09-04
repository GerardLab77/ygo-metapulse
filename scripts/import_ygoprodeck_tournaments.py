"""Import manually downloaded YGOPRODeck Tournament Meta Decks (TCG)."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from src.config import (
    TOURNAMENT_DECK_METADATA_DIR,
    TOURNAMENT_DECKS_DIR,
    YGOPRODECK_IMPORT_REPORTS_DIR,
    YGOPRODECK_IMPORT_TEMPLATE_PATH,
    YGOPRODECK_MANUAL_YDK_DIR,
)
from src.ygoprodeck_import import import_from_manifest, write_manifest_template


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate manually downloaded YGOPRODeck Tournament Meta Decks (TCG) "
            "and write normalized deck/metadata files for YGO MetaPulse."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=YGOPRODECK_IMPORT_TEMPLATE_PATH.parent / "import_manifest.csv",
        help="CSV manifest describing manually downloaded YDK files.",
    )
    parser.add_argument(
        "--ydk-dir",
        type=Path,
        default=YGOPRODECK_MANUAL_YDK_DIR,
        help="Folder containing manually downloaded YDK files.",
    )
    parser.add_argument(
        "--output-decks-dir",
        type=Path,
        default=TOURNAMENT_DECKS_DIR,
        help="Destination for validated tournament YDK files.",
    )
    parser.add_argument(
        "--output-metadata-dir",
        type=Path,
        default=TOURNAMENT_DECK_METADATA_DIR,
        help="Destination for generated deck metadata JSON files.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=YGOPRODECK_IMPORT_REPORTS_DIR,
        help="Folder for machine-readable import reports.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Maximum manifest rows to process.")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs without writing deck outputs.")
    parser.add_argument("--overwrite", action="store_true", help="Refresh already imported source URLs.")
    parser.add_argument(
        "--write-template",
        action="store_true",
        help="Write the CSV template and exit.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = parse_args()

    if args.write_template:
        template_path = write_manifest_template()
        print(f"Wrote manifest template: {template_path}")
        return 0

    try:
        report = import_from_manifest(
            manifest_path=args.manifest,
            ydk_dir=args.ydk_dir,
            output_decks_dir=args.output_decks_dir,
            output_metadata_dir=args.output_metadata_dir,
            report_dir=args.report_dir,
            limit=args.limit,
            dry_run=args.dry_run,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Import failed: {exc}")
        return 1

    print(json.dumps(asdict(report), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
