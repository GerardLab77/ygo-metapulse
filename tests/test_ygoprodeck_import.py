import csv
import json
from pathlib import Path

from src.ygoprodeck_import import import_from_manifest


def _cards(count: int = 45) -> list[dict]:
    return [{"id": card_id, "name": f"Card {card_id}"} for card_id in range(1, count + 1)]


def _write_valid_ydk(path: Path) -> None:
    lines = [
        "#created by test",
        "#main",
        *(str(card_id) for card_id in range(1, 41)),
        "#extra",
        "41",
        "!side",
        "42",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_import_from_manifest_writes_valid_tournament_outputs(tmp_path: Path) -> None:
    ydk_dir = tmp_path / "manual_ydk"
    output_decks_dir = tmp_path / "tournament_decks"
    output_metadata_dir = tmp_path / "tournament_metadata"
    ydk_dir.mkdir()
    _write_valid_ydk(ydk_dir / "deck.ydk")
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(
        manifest_path,
        [
            {
                "deck_file": "deck.ydk",
                "event_name": "Test Regional",
                "event_date": "2026-08-30",
                "placement": "Top 8",
                "player": "Test Player",
                "player_count": "128",
                "archetype": "Sky Striker",
                "format": "TCG Advanced",
                "source_url": "https://ygoprodeck.com/deck/sky-striker-123456",
                "access_date": "2026-09-04",
                "notes": "Downloaded manually for test.",
                "ygoprodeck_deck_id": "",
            }
        ],
    )

    report = import_from_manifest(
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
        cards=_cards(),
        write_report=False,
    )

    metadata = json.loads((output_metadata_dir / "ygoprodeck_123456.json").read_text(encoding="utf-8"))
    assert report.summary["imported"] == 1
    assert (output_decks_dir / "ygoprodeck_123456.ydk").exists()
    assert metadata["dataset_type"] == "tournament"
    assert metadata["source_site"] == "YGOPRODeck"
    assert metadata["external_deck_id"] == "123456"


def test_import_from_manifest_rejects_unknown_card_ids(tmp_path: Path) -> None:
    ydk_dir = tmp_path / "manual_ydk"
    output_decks_dir = tmp_path / "tournament_decks"
    output_metadata_dir = tmp_path / "tournament_metadata"
    ydk_dir.mkdir()
    bad_lines = ["#main", *(str(card_id) for card_id in range(1, 40)), "999999", "#extra", "!side", ""]
    (ydk_dir / "bad.ydk").write_text("\n".join(bad_lines), encoding="utf-8")
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(
        manifest_path,
        [
            {
                "deck_file": "bad.ydk",
                "source_url": "https://ygoprodeck.com/deck/bad-deck-222222",
            }
        ],
    )

    report = import_from_manifest(
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
        cards=_cards(),
        write_report=False,
    )

    assert report.summary["rejected"] == 1
    assert "Unknown card ID" in report.records[0]["errors"][0]
    assert not output_decks_dir.exists()


def test_import_from_manifest_rejects_duplicate_sources(tmp_path: Path) -> None:
    ydk_dir = tmp_path / "manual_ydk"
    output_decks_dir = tmp_path / "tournament_decks"
    output_metadata_dir = tmp_path / "tournament_metadata"
    ydk_dir.mkdir()
    _write_valid_ydk(ydk_dir / "one.ydk")
    _write_valid_ydk(ydk_dir / "two.ydk")
    source_url = "https://ygoprodeck.com/deck/duplicate-333333"
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(
        manifest_path,
        [
            {
                "deck_file": "one.ydk",
                "source_url": source_url,
                "event_name": "Duplicate Regional",
                "event_date": "2026-09-01",
                "placement": "Top 8",
                "player": "First Player",
                "player_count": "64",
                "archetype": "Demo",
            },
            {
                "deck_file": "two.ydk",
                "source_url": source_url,
                "event_name": "Duplicate Regional",
                "event_date": "2026-09-01",
                "placement": "Top 4",
                "player": "Second Player",
                "player_count": "64",
                "archetype": "Demo",
            },
        ],
    )

    report = import_from_manifest(
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
        cards=_cards(),
        write_report=False,
    )

    assert report.summary["imported"] == 1
    assert report.summary["rejected"] == 1
    assert "Duplicate source URL" in report.records[1]["errors"][0]


def test_import_from_manifest_flags_missing_event_metadata(tmp_path: Path) -> None:
    ydk_dir = tmp_path / "manual_ydk"
    output_decks_dir = tmp_path / "tournament_decks"
    output_metadata_dir = tmp_path / "tournament_metadata"
    ydk_dir.mkdir()
    _write_valid_ydk(ydk_dir / "incomplete.ydk")
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(
        manifest_path,
        [
            {
                "deck_file": "incomplete.ydk",
                "source_url": "https://ygoprodeck.com/deck/incomplete-444444",
            }
        ],
    )

    report = import_from_manifest(
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
        cards=_cards(),
        write_report=False,
    )

    assert report.records[0]["status"] == "incomplete"
    assert report.summary["incomplete"] == 1
    assert "Missing metadata field" in report.records[0]["warnings"][0]


def test_import_from_manifest_skips_existing_source_url(tmp_path: Path) -> None:
    ydk_dir = tmp_path / "manual_ydk"
    output_decks_dir = tmp_path / "tournament_decks"
    output_metadata_dir = tmp_path / "tournament_metadata"
    ydk_dir.mkdir()
    output_metadata_dir.mkdir()
    _write_valid_ydk(ydk_dir / "existing.ydk")
    source_url = "https://ygoprodeck.com/deck/existing-555555"
    (output_metadata_dir / "ygoprodeck_555555.json").write_text(
        json.dumps({"source_url": source_url}),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.csv"
    _write_manifest(
        manifest_path,
        [
            {
                "deck_file": "existing.ydk",
                "source_url": source_url,
                "event_name": "Already Imported Regional",
                "event_date": "2026-09-01",
                "placement": "Top 8",
                "player": "Existing Player",
                "player_count": "64",
                "archetype": "Demo",
            }
        ],
    )

    report = import_from_manifest(
        manifest_path=manifest_path,
        ydk_dir=ydk_dir,
        output_decks_dir=output_decks_dir,
        output_metadata_dir=output_metadata_dir,
        cards=_cards(),
        write_report=False,
    )

    assert report.records[0]["status"] == "skipped_existing"
    assert report.summary["skipped"] == 1
    assert not output_decks_dir.exists()
