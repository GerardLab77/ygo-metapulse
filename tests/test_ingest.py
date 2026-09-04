import json
from pathlib import Path

from src import db
from src import ingest


def test_select_deck_files_prefers_real_decks(tmp_path: Path, monkeypatch) -> None:
    decks_dir = tmp_path / "decks"
    decks_dir.mkdir()
    (decks_dir / "sample_demo.ydk").write_text("#main\n100\n", encoding="utf-8")
    (decks_dir / "real_event_top8.ydk").write_text("#main\n200\n", encoding="utf-8")

    monkeypatch.setattr(ingest, "DECKS_DIR", decks_dir)

    selected_files, deck_mode = ingest._select_deck_files()

    assert deck_mode == "real"
    assert [path.name for path in selected_files] == ["real_event_top8.ydk"]


def test_ingest_decks_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    db_path = tmp_path / "ingest.db"
    decks_dir = tmp_path / "decks"
    metadata_dir = tmp_path / "deck_metadata"
    decks_dir.mkdir()
    metadata_dir.mkdir()

    db.init_db(db_path=db_path)
    db.upsert_cards(
        [
            {"id": 100, "name": "Card A", "card_prices": [], "banlist_info": {}},
            {"id": 200, "name": "Card B", "card_prices": [], "banlist_info": {}},
            {"id": 300, "name": "Card C", "card_prices": [], "banlist_info": {}},
            {"id": 400, "name": "Card D", "card_prices": [], "banlist_info": {}},
        ],
        db_path=db_path,
    )

    (decks_dir / "regional_top8.ydk").write_text(
        "\n".join(
            [
                "#main",
                "100",
                "100",
                "200",
                "#extra",
                "300",
                "!side",
                "400",
                "400",
            ]
        ),
        encoding="utf-8",
    )
    (metadata_dir / "regional_top8.json").write_text(
        json.dumps(
            {
                "event_name": "Regional Test",
                "event_date": "2026-05-01",
                "placement": "Top 8",
                "player": "Test Player",
                "archetype": "Test",
                "format": "TCG Advanced",
                "source_url": "https://example.com/regional-top8",
                "notes": "Test fixture",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ingest, "DECKS_DIR", decks_dir)
    monkeypatch.setattr(ingest, "DECK_METADATA_DIR", metadata_dir)
    monkeypatch.setattr(ingest, "init_db", lambda: db.init_db(db_path=db_path))
    monkeypatch.setattr(
        ingest,
        "insert_or_update_deck",
        lambda deck_slug, metadata, parsed_deck: db.insert_or_update_deck(
            deck_slug,
            metadata,
            parsed_deck,
            db_path=db_path,
        ),
    )
    monkeypatch.setattr(
        ingest,
        "delete_decks_not_in",
        lambda active_slugs: db.delete_decks_not_in(active_slugs, db_path=db_path),
    )

    first_count = ingest.ingest_decks()
    second_count = ingest.ingest_decks()

    decks_df = db.get_decks_df(db_path=db_path)
    deck_cards_df = db.get_deck_cards_df(db_path=db_path)

    assert first_count == 1
    assert second_count == 1
    assert len(decks_df) == 1
    assert len(deck_cards_df) == 4
    assert int(deck_cards_df["quantity"].sum()) == 6
