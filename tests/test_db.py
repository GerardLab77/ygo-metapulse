from pathlib import Path

from src.db import (
    delete_decks_not_in,
    get_connection,
    get_deck_cards_df,
    get_decks_df,
    init_db,
    insert_or_update_deck,
    upsert_cards,
)


def test_init_db_creates_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path=db_path)

    with get_connection(db_path=db_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table';"
            ).fetchall()
        }

    assert {"cards", "decks", "deck_cards"}.issubset(tables)


def test_deck_ingestion_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path=db_path)
    upsert_cards(
        [
            {"id": 100, "name": "Card A", "card_prices": [], "banlist_info": {}},
            {"id": 200, "name": "Card B", "card_prices": [], "banlist_info": {}},
            {"id": 300, "name": "Card C", "card_prices": [], "banlist_info": {}},
            {"id": 400, "name": "Card D", "card_prices": [], "banlist_info": {}},
        ],
        db_path=db_path,
    )
    metadata = {
        "event_name": "Test Event",
        "event_date": "2026-05-01",
        "placement": "1st",
        "player": "Tester",
        "archetype": "Demo",
        "format": "TCG Advanced",
        "source_url": "https://example.com",
        "notes": "Test",
    }
    parsed_deck = {
        "main": {100: 2, 200: 1},
        "extra": {300: 1},
        "side": {400: 2},
    }

    insert_or_update_deck("demo_deck", metadata, parsed_deck, db_path=db_path)
    insert_or_update_deck("demo_deck", metadata, parsed_deck, db_path=db_path)

    decks_df = get_decks_df(db_path=db_path)
    deck_cards_df = get_deck_cards_df(db_path=db_path)

    assert len(decks_df) == 1
    assert len(deck_cards_df) == 4
    assert int(deck_cards_df["quantity"].sum()) == 6


def test_delete_decks_not_in_removes_stale_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path=db_path)
    upsert_cards(
        [
            {"id": 100, "name": "Card A", "card_prices": [], "banlist_info": {}},
            {"id": 200, "name": "Card B", "card_prices": [], "banlist_info": {}},
        ],
        db_path=db_path,
    )
    metadata = {
        "event_name": "Test Event",
        "event_date": "2026-05-01",
        "placement": "1st",
        "player": "Tester",
        "archetype": "Demo",
        "format": "TCG Advanced",
        "source_url": "https://example.com",
        "notes": "Test",
    }

    insert_or_update_deck("keep_me", metadata, {"main": {100: 1}, "extra": {}, "side": {}}, db_path=db_path)
    insert_or_update_deck("drop_me", metadata, {"main": {200: 1}, "extra": {}, "side": {}}, db_path=db_path)

    delete_decks_not_in(["keep_me"], db_path=db_path)

    decks_df = get_decks_df(db_path=db_path)
    assert decks_df["deck_slug"].tolist() == ["keep_me"]
