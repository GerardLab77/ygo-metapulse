"""Manual YGOPRODeck tournament deck import utilities.

YGOPRODeck's public site pages are not fetched by this module. It validates
manually downloaded `.ydk` files and an attribution manifest, then writes the
normalized deck files used by the ingestion pipeline.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import urlparse

from src.config import (
    TOURNAMENT_DECK_METADATA_DIR,
    TOURNAMENT_DECKS_DIR,
    YGOPRODECK_IMPORT_REPORTS_DIR,
    YGOPRODECK_IMPORT_TEMPLATE_PATH,
    YGOPRODECK_MANUAL_YDK_DIR,
    YGOPRODECK_TOURNAMENT_CATEGORY_URL,
)
from src.fetch_cards import fetch_cards
from src.parse_ydk import parse_ydk_file

logger = logging.getLogger(__name__)

CSV_COLUMNS = [
    "deck_file",
    "event_name",
    "event_date",
    "placement",
    "player",
    "player_count",
    "archetype",
    "format",
    "source_url",
    "access_date",
    "notes",
    "ygoprodeck_deck_id",
]

REQUIRED_COLUMNS = {"deck_file", "source_url"}
EVENT_METADATA_FIELDS = [
    "event_name",
    "event_date",
    "placement",
    "player",
    "player_count",
    "archetype",
    "format",
]


@dataclass
class ImportRecord:
    """Result for one row in the manual import manifest."""

    row_number: int
    status: str
    deck_slug: str | None
    deck_file: str | None
    source_url: str | None
    errors: list[str]
    warnings: list[str]
    main_count: int | None = None
    extra_count: int | None = None
    side_count: int | None = None


@dataclass
class ImportReport:
    """Machine-readable summary of a manual import run."""

    generated_at: str
    source_category: str
    dry_run: bool
    manifest_path: str
    input_ydk_dir: str
    output_decks_dir: str
    output_metadata_dir: str
    summary: dict[str, int]
    records: list[dict]


def write_manifest_template(path: Path = YGOPRODECK_IMPORT_TEMPLATE_PATH) -> Path:
    """Create a CSV template for manually attributed YGOPRODeck imports."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "deck_file": "example_downloaded_deck.ydk",
                "event_name": "Example WCQ Regional",
                "event_date": "2026-08-30",
                "placement": "Top 8",
                "player": "Player Name",
                "player_count": "128",
                "archetype": "Example Archetype",
                "format": "TCG Advanced",
                "source_url": "https://ygoprodeck.com/deck/example-123456",
                "access_date": date.today().isoformat(),
                "notes": "Manually downloaded from YGOPRODeck Tournament Meta Decks (TCG)",
                "ygoprodeck_deck_id": "123456",
            }
        )
    return path


def import_from_manifest(
    *,
    manifest_path: Path,
    ydk_dir: Path = YGOPRODECK_MANUAL_YDK_DIR,
    output_decks_dir: Path = TOURNAMENT_DECKS_DIR,
    output_metadata_dir: Path = TOURNAMENT_DECK_METADATA_DIR,
    report_dir: Path = YGOPRODECK_IMPORT_REPORTS_DIR,
    cards: list[dict] | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    overwrite: bool = False,
    write_report: bool = True,
) -> ImportReport:
    """Validate and import manually downloaded YGOPRODeck tournament decklists."""

    manifest_path = manifest_path.resolve()
    ydk_dir = ydk_dir.resolve()
    output_decks_dir = output_decks_dir.resolve()
    output_metadata_dir = output_metadata_dir.resolve()
    report_dir = report_dir.resolve()

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Import manifest not found: {manifest_path}. "
            f"Copy {YGOPRODECK_IMPORT_TEMPLATE_PATH} to import_manifest.csv and fill it in."
        )

    card_payload = cards if cards is not None else fetch_cards(force_refresh=False)
    valid_card_ids = {int(card["id"]) for card in card_payload if "id" in card}
    existing_source_urls = _load_existing_source_urls(output_metadata_dir)
    seen_source_keys: set[str] = set()
    records: list[ImportRecord] = []

    with manifest_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        _validate_manifest_columns(reader.fieldnames or [])
        for index, row in enumerate(reader, start=2):
            if limit is not None and len(records) >= limit:
                break
            if _row_is_blank(row):
                continue
            record = _process_manifest_row(
                row_number=index,
                row=row,
                ydk_dir=ydk_dir,
                output_decks_dir=output_decks_dir,
                output_metadata_dir=output_metadata_dir,
                valid_card_ids=valid_card_ids,
                existing_source_urls=existing_source_urls,
                seen_source_keys=seen_source_keys,
                dry_run=dry_run,
                overwrite=overwrite,
            )
            records.append(record)

    report = _build_report(
        records=records,
        dry_run=dry_run,
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
    )
    if write_report:
        _write_report(report, report_dir)
    return report


def _validate_manifest_columns(fieldnames: list[str]) -> None:
    missing = REQUIRED_COLUMNS - set(fieldnames)
    if missing:
        raise ValueError(f"Import manifest is missing required column(s): {', '.join(sorted(missing))}")


def _process_manifest_row(
    *,
    row_number: int,
    row: dict[str, str],
    ydk_dir: Path,
    output_decks_dir: Path,
    output_metadata_dir: Path,
    valid_card_ids: set[int],
    existing_source_urls: set[str],
    seen_source_keys: set[str],
    dry_run: bool,
    overwrite: bool,
) -> ImportRecord:
    errors: list[str] = []
    warnings: list[str] = []
    deck_file = _clean_text(row.get("deck_file"))
    source_url = _clean_text(row.get("source_url"))
    external_deck_id = _clean_text(row.get("ygoprodeck_deck_id")) or _extract_deck_id(source_url)
    source_key = external_deck_id or source_url

    if not deck_file:
        errors.append("Missing deck_file.")
    if deck_file and Path(deck_file).name != deck_file:
        errors.append("deck_file must be a filename inside the manual_ydk folder, not a path.")
    if not source_url:
        errors.append("Missing source_url.")
    elif not _is_ygoprodeck_url(source_url):
        errors.append("source_url must point to ygoprodeck.com.")
    if source_key and source_key in seen_source_keys:
        errors.append("Duplicate source URL or YGOPRODeck deck identifier in manifest.")
    source_already_imported = bool(source_url and source_url in existing_source_urls and not overwrite)
    if source_already_imported:
        warnings.append("Deck source has already been imported; skipped. Use --overwrite to refresh it.")

    deck_slug = _build_deck_slug(row, source_url, external_deck_id) if source_url else None
    parsed_deck: dict[str, dict[int, int]] | None = None
    main_count = extra_count = side_count = None
    if deck_file:
        ydk_path = ydk_dir / deck_file
        if not ydk_path.exists():
            errors.append(f"YDK file not found: {ydk_path}")
        else:
            try:
                parsed_deck = parse_ydk_file(ydk_path)
                validation_errors, counts = _validate_parsed_deck(parsed_deck, valid_card_ids)
                errors.extend(validation_errors)
                main_count = counts["main"]
                extra_count = counts["extra"]
                side_count = counts["side"]
            except (FileNotFoundError, ValueError) as exc:
                errors.append(str(exc))

    metadata = _build_metadata(row, source_url, external_deck_id, warnings)
    missing_fields = [field for field in EVENT_METADATA_FIELDS if metadata.get(field) in (None, "")]
    if missing_fields:
        warnings.append(f"Missing metadata field(s): {', '.join(missing_fields)}")

    if source_already_imported and not errors:
        status = "skipped_existing"
    elif errors:
        status = "rejected"
    elif warnings:
        status = "would_import_incomplete" if dry_run else "incomplete"
    else:
        status = "would_import" if dry_run else "imported"

    if source_key:
        seen_source_keys.add(source_key)

    if status in {"imported", "incomplete"} and parsed_deck and deck_file and deck_slug:
        output_decks_dir.mkdir(parents=True, exist_ok=True)
        output_metadata_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ydk_dir / deck_file, output_decks_dir / f"{deck_slug}.ydk")
        (output_metadata_dir / f"{deck_slug}.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )
        logger.info("Imported %s from %s.", deck_slug, source_url)

    return ImportRecord(
        row_number=row_number,
        status=status,
        deck_slug=deck_slug,
        deck_file=deck_file,
        source_url=source_url,
        errors=errors,
        warnings=warnings,
        main_count=main_count,
        extra_count=extra_count,
        side_count=side_count,
    )


def _validate_parsed_deck(
    parsed_deck: dict[str, dict[int, int]],
    valid_card_ids: set[int],
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    counts = {section: sum(cards.values()) for section, cards in parsed_deck.items()}
    if counts["main"] < 40 or counts["main"] > 60:
        errors.append(f"Main deck must contain 40-60 cards; found {counts['main']}.")
    if counts["extra"] > 15:
        errors.append(f"Extra deck must not exceed 15 cards; found {counts['extra']}.")
    if counts["side"] > 15:
        errors.append(f"Side deck must not exceed 15 cards; found {counts['side']}.")

    deck_card_ids = {
        card_id
        for section_cards in parsed_deck.values()
        for card_id in section_cards
    }
    unknown_ids = sorted(deck_card_ids - valid_card_ids)
    if unknown_ids:
        preview = ", ".join(str(card_id) for card_id in unknown_ids[:10])
        suffix = "..." if len(unknown_ids) > 10 else ""
        errors.append(f"Unknown card ID(s) not found in cached YGOPRODeck metadata: {preview}{suffix}")
    return errors, counts


def _build_metadata(
    row: dict[str, str],
    source_url: str | None,
    external_deck_id: str | None,
    warnings: list[str],
) -> dict:
    event_date = _parse_iso_date(_clean_text(row.get("event_date")), "event_date", warnings)
    access_date = _parse_iso_date(_clean_text(row.get("access_date")), "access_date", warnings)
    if access_date is None:
        access_date = date.today().isoformat()

    return {
        "event_name": _clean_text(row.get("event_name")),
        "event_date": event_date,
        "placement": _clean_text(row.get("placement")),
        "player": _clean_text(row.get("player")),
        "player_count": _parse_player_count(_clean_text(row.get("player_count")), warnings),
        "archetype": _clean_text(row.get("archetype")),
        "format": _clean_text(row.get("format")) or "TCG Advanced",
        "source_url": source_url,
        "notes": _clean_text(row.get("notes")),
        "dataset_type": "tournament",
        "source_site": "YGOPRODeck",
        "source_category": YGOPRODECK_TOURNAMENT_CATEGORY_URL,
        "access_date": access_date,
        "external_deck_id": external_deck_id,
        "attribution": "Decklist manually downloaded from YGOPRODeck Tournament Meta Decks (TCG).",
    }


def _parse_iso_date(value: str | None, field_name: str, warnings: list[str]) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        warnings.append(f"{field_name} should use YYYY-MM-DD format; stored as null.")
        return None


def _parse_player_count(value: str | None, warnings: list[str]) -> int | None:
    if not value:
        return None
    match = re.search(r"\d+", value.replace(",", ""))
    if not match:
        warnings.append("player_count could not be parsed as an integer; stored as null.")
        return None
    return int(match.group(0))


def _build_deck_slug(row: dict[str, str], source_url: str | None, external_deck_id: str | None) -> str:
    if external_deck_id:
        return f"ygoprodeck_{_slugify(external_deck_id)}"
    digest = hashlib.sha1((source_url or "").encode("utf-8")).hexdigest()[:10]
    parts = [
        "ygoprodeck",
        _clean_text(row.get("event_date")) or "unknown-date",
        _clean_text(row.get("archetype")) or "unknown-archetype",
        digest,
    ]
    return _slugify("_".join(parts))


def _extract_deck_id(source_url: str | None) -> str | None:
    if not source_url:
        return None
    path = urlparse(source_url).path.rstrip("/")
    match = re.search(r"-(\d+)$", path)
    return match.group(1) if match else None


def _is_ygoprodeck_url(source_url: str) -> bool:
    parsed = urlparse(source_url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() in {"ygoprodeck.com", "www.ygoprodeck.com"}


def _load_existing_source_urls(metadata_dir: Path) -> set[str]:
    source_urls: set[str] = set()
    if not metadata_dir.exists():
        return source_urls
    for path in metadata_dir.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        source_url = _clean_text(payload.get("source_url"))
        if source_url:
            source_urls.add(source_url)
    return source_urls


def _build_report(
    *,
    records: list[ImportRecord],
    dry_run: bool,
    manifest_path: Path,
    ydk_dir: Path,
    output_decks_dir: Path,
    output_metadata_dir: Path,
) -> ImportReport:
    summary = {
        "processed": len(records),
        "valid": sum(record.status in {"imported", "incomplete", "would_import", "would_import_incomplete"} for record in records),
        "imported": sum(record.status == "imported" for record in records),
        "incomplete": sum(record.status in {"incomplete", "would_import_incomplete"} for record in records),
        "rejected": sum(record.status == "rejected" for record in records),
        "skipped": sum(record.status == "skipped_existing" for record in records),
        "dry_run_valid": sum(record.status in {"would_import", "would_import_incomplete"} for record in records),
    }
    return ImportReport(
        generated_at=datetime.now(UTC).isoformat(),
        source_category=YGOPRODECK_TOURNAMENT_CATEGORY_URL,
        dry_run=dry_run,
        manifest_path=str(manifest_path),
        input_ydk_dir=str(ydk_dir),
        output_decks_dir=str(output_decks_dir),
        output_metadata_dir=str(output_metadata_dir),
        summary=summary,
        records=[asdict(record) for record in records],
    )


def _write_report(report: ImportReport, report_dir: Path) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"import_report_{timestamp}.json"
    report_path.write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")
    logger.info("Wrote import report: %s", report_path)
    return report_path


def _row_is_blank(row: dict[str, str]) -> bool:
    return not any(_clean_text(value) for value in row.values())


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned or cleaned.lower() in {"unknown", "n/a", "na", "null", "none"}:
        return None
    return cleaned


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return slug or "unknown"
