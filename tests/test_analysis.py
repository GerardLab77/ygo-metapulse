from pathlib import Path

from src.analysis import deck_price_estimates, engine_detection, most_played_cards
from src.db import init_db, insert_or_update_deck, upsert_cards


def seed_test_database(db_path: Path) -> None:
    init_db(db_path=db_path)
    upsert_cards(
        [
            {
                "id": 100,
                "name": "Sky Striker Ace - Raye",
                "type": "Effect Monster",
                "frameType": "effect",
                "desc": "Starter.",
                "race": "Warrior",
                "attribute": "LIGHT",
                "archetype": "Sky Striker",
                "card_prices": [{"cardmarket_price": "2.50"}],
                "banlist_info": {"ban_tcg": "Limited"},
            },
            {
                "id": 200,
                "name": "Infinite Impermanence",
                "type": "Trap Card",
                "frameType": "trap",
                "desc": "Staple interaction.",
                "race": "Normal",
                "attribute": None,
                "archetype": None,
                "card_prices": [{"cardmarket_price": ""}],
                "banlist_info": {},
            },
            {
                "id": 300,
                "name": "Sky Striker Ace - Kagari",
                "type": "Link Monster",
                "frameType": "link",
                "desc": "Extra deck piece.",
                "race": "Machine",
                "attribute": "FIRE",
                "archetype": "Sky Striker",
                "card_prices": [{"cardmarket_price": "1.00"}],
                "banlist_info": {},
            },
            {
                "id": 400,
                "name": "Orcust Harp Horror",
                "type": "Effect Monster",
                "frameType": "effect",
                "desc": "Orcust engine piece.",
                "race": "Machine",
                "attribute": "DARK",
                "archetype": "Orcust",
                "card_prices": [{"cardmarket_price": "4.00"}],
                "banlist_info": {},
            },
        ],
        db_path=db_path,
    )
    insert_or_update_deck(
        "sky_striker_demo",
        {
            "event_name": "Test Event",
            "event_date": "2026-05-01",
            "placement": "1st",
            "player": "Tester A",
            "archetype": "Sky Striker",
            "format": "TCG Advanced",
            "source_url": "https://example.com/sky",
            "notes": "Demo",
        },
        {"main": {100: 3, 200: 2}, "extra": {300: 1}, "side": {}},
        db_path=db_path,
    )
    insert_or_update_deck(
        "orcust_demo",
        {
            "event_name": "Test Event",
            "event_date": "2026-05-03",
            "placement": "Top 8",
            "player": "Tester B",
            "archetype": "Orcust",
            "format": "TCG Advanced",
            "source_url": "https://example.com/orcust",
            "notes": "Demo",
        },
        {"main": {400: 3, 200: 1}, "extra": {}, "side": {}},
        db_path=db_path,
    )


def test_most_played_cards_returns_expected_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    seed_test_database(db_path)

    result = most_played_cards(db_path=db_path)

    assert {
        "card_name",
        "card_type",
        "card_archetype",
        "total_copies",
        "decks_seen",
        "deck_inclusion_rate",
    }.issubset(result.columns)


def test_deck_price_estimates_handle_missing_prices(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    seed_test_database(db_path)

    result = deck_price_estimates(db_path=db_path)
    sky_row = result[result["deck_slug"] == "sky_striker_demo"].iloc[0]

    assert sky_row["estimated_deck_price"] == 8.5
    assert sky_row["priced_copy_ratio"] > 0


def test_engine_detection_returns_sensible_values(tmp_path: Path) -> None:
    db_path = tmp_path / "analysis.db"
    seed_test_database(db_path)

    result = engine_detection(db_path=db_path)
    sky_row = result[result["deck_slug"] == "sky_striker_demo"].iloc[0]
    orcust_row = result[result["deck_slug"] == "orcust_demo"].iloc[0]

    assert "Sky Striker" in sky_row["detected_engines"]
    assert "Orcust" in orcust_row["detected_engines"]
