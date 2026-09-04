"""SQLite persistence layer for YGO MetaPulse."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.config import DB_PATH, ensure_directories

DECK_OPTIONAL_COLUMNS = {
    "player_count": "INTEGER",
    "source_site": "TEXT",
    "source_category": "TEXT",
    "access_date": "TEXT",
    "external_deck_id": "TEXT",
    "dataset_type": "TEXT",
}


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enabled."""

    ensure_directories()
    target = db_path or DB_PATH
    connection = sqlite3.connect(target)
    connection.execute("PRAGMA foreign_keys = ON;")
    return connection


def init_db(db_path: Path | None = None) -> None:
    """Create the application tables if they do not already exist."""

    schema_statements = (
        """
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            frame_type TEXT,
            description TEXT,
            race TEXT,
            attribute TEXT,
            archetype TEXT,
            ban_tcg TEXT,
            cardmarket_price REAL,
            raw_json TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_slug TEXT UNIQUE NOT NULL,
            event_name TEXT,
            event_date TEXT,
            placement TEXT,
            player TEXT,
            player_count INTEGER,
            archetype TEXT,
            format TEXT,
            source_url TEXT,
            source_site TEXT,
            source_category TEXT,
            access_date TEXT,
            external_deck_id TEXT,
            dataset_type TEXT,
            notes TEXT,
            created_at TEXT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS deck_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deck_id INTEGER NOT NULL,
            card_id INTEGER NOT NULL,
            section TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE,
            FOREIGN KEY(card_id) REFERENCES cards(id)
        );
        """,
    )

    with get_connection(db_path) as connection:
        for statement in schema_statements:
            connection.execute(statement)
        _ensure_deck_columns(connection)
        connection.commit()


def upsert_cards(cards: Iterable[dict], db_path: Path | None = None) -> None:
    """Insert or update card metadata in SQLite."""

    init_db(db_path)
    rows = []
    for card in cards:
        banlist_info = card.get("banlist_info") or {}
        card_prices = card.get("card_prices") or []
        cardmarket_price = None
        if card_prices and isinstance(card_prices, list):
            raw_price = card_prices[0].get("cardmarket_price")
            try:
                cardmarket_price = float(raw_price) if raw_price not in (None, "") else None
            except (TypeError, ValueError):
                cardmarket_price = None
        rows.append(
            (
                int(card["id"]),
                card.get("name"),
                card.get("type"),
                card.get("frameType"),
                card.get("desc"),
                card.get("race"),
                card.get("attribute"),
                card.get("archetype"),
                banlist_info.get("ban_tcg"),
                cardmarket_price,
                json.dumps(card, ensure_ascii=False),
            )
        )

    with get_connection(db_path) as connection:
        connection.executemany(
            """
            INSERT INTO cards (
                id, name, type, frame_type, description, race, attribute, archetype,
                ban_tcg, cardmarket_price, raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                type = excluded.type,
                frame_type = excluded.frame_type,
                description = excluded.description,
                race = excluded.race,
                attribute = excluded.attribute,
                archetype = excluded.archetype,
                ban_tcg = excluded.ban_tcg,
                cardmarket_price = excluded.cardmarket_price,
                raw_json = excluded.raw_json;
            """,
            rows,
        )
        connection.commit()


def insert_or_update_deck(
    deck_slug: str,
    metadata: dict,
    parsed_deck: dict[str, dict[int, int]],
    db_path: Path | None = None,
) -> None:
    """Insert or update a deck and replace its card mapping idempotently."""

    init_db(db_path)
    created_at = datetime.now(UTC).isoformat()
    dataset_type = metadata.get("dataset_type") or ("sample" if deck_slug.startswith("sample_") else "tournament")
    with get_connection(db_path) as connection:
        card_ids = {
            card_id
            for section_cards in parsed_deck.values()
            for card_id in section_cards.keys()
        }
        if card_ids:
            placeholders = ", ".join("?" for _ in card_ids)
            existing_ids = {
                row[0]
                for row in connection.execute(
                    f"SELECT id FROM cards WHERE id IN ({placeholders});",
                    tuple(card_ids),
                ).fetchall()
            }
            missing_ids = sorted(card_ids - existing_ids)
            if missing_ids:
                raise ValueError(
                    "Deck ingestion found card IDs that are missing from the cards table. "
                    f"Run card ingestion first or refresh the cache. Missing IDs: {missing_ids}"
                )
        connection.execute(
            """
            INSERT INTO decks (
                deck_slug, event_name, event_date, placement, player, player_count,
                archetype, format, source_url, source_site, source_category, access_date,
                external_deck_id, dataset_type, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(deck_slug) DO UPDATE SET
                event_name = excluded.event_name,
                event_date = excluded.event_date,
                placement = excluded.placement,
                player = excluded.player,
                player_count = excluded.player_count,
                archetype = excluded.archetype,
                format = excluded.format,
                source_url = excluded.source_url,
                source_site = excluded.source_site,
                source_category = excluded.source_category,
                access_date = excluded.access_date,
                external_deck_id = excluded.external_deck_id,
                dataset_type = excluded.dataset_type,
                notes = excluded.notes;
            """,
            (
                deck_slug,
                metadata.get("event_name"),
                metadata.get("event_date"),
                metadata.get("placement"),
                metadata.get("player"),
                _coerce_optional_int(metadata.get("player_count")),
                metadata.get("archetype"),
                metadata.get("format"),
                metadata.get("source_url"),
                metadata.get("source_site"),
                metadata.get("source_category"),
                metadata.get("access_date"),
                metadata.get("external_deck_id"),
                dataset_type,
                metadata.get("notes"),
                created_at,
            ),
        )
        deck_id = connection.execute(
            "SELECT id FROM decks WHERE deck_slug = ?;",
            (deck_slug,),
        ).fetchone()[0]
        connection.execute("DELETE FROM deck_cards WHERE deck_id = ?;", (deck_id,))
        rows = []
        for section, cards in parsed_deck.items():
            for card_id, quantity in cards.items():
                rows.append((deck_id, card_id, section, quantity))
        connection.executemany(
            """
            INSERT INTO deck_cards (deck_id, card_id, section, quantity)
            VALUES (?, ?, ?, ?);
            """,
            rows,
        )
        connection.commit()


def delete_decks_not_in(active_slugs: list[str], db_path: Path | None = None) -> None:
    """Synchronize stored deck rows to the provided deck slug list."""

    init_db(db_path)
    with get_connection(db_path) as connection:
        if active_slugs:
            placeholders = ", ".join("?" for _ in active_slugs)
            connection.execute(
                f"DELETE FROM decks WHERE deck_slug NOT IN ({placeholders});",
                tuple(active_slugs),
            )
        else:
            connection.execute("DELETE FROM decks;")
        connection.commit()


def get_cards_df(db_path: Path | None = None) -> pd.DataFrame:
    """Return the cards table as a pandas DataFrame."""

    init_db(db_path)
    with get_connection(db_path) as connection:
        return pd.read_sql_query("SELECT * FROM cards;", connection)


def get_decks_df(db_path: Path | None = None) -> pd.DataFrame:
    """Return the decks table as a pandas DataFrame."""

    init_db(db_path)
    with get_connection(db_path) as connection:
        return pd.read_sql_query("SELECT * FROM decks;", connection)


def get_deck_cards_df(db_path: Path | None = None) -> pd.DataFrame:
    """Return the deck_cards table as a pandas DataFrame."""

    init_db(db_path)
    with get_connection(db_path) as connection:
        return pd.read_sql_query("SELECT * FROM deck_cards;", connection)


def get_joined_deck_cards_df(db_path: Path | None = None) -> pd.DataFrame:
    """Return a joined deck-card dataset for analytics."""

    init_db(db_path)
    query = """
        SELECT
            dc.id AS deck_card_row_id,
            d.id AS deck_id,
            d.deck_slug,
            d.event_name,
            d.event_date,
            d.placement,
            d.player,
            d.player_count,
            d.archetype AS deck_archetype,
            d.format,
            d.source_url,
            d.source_site,
            d.source_category,
            d.access_date,
            d.external_deck_id,
            d.dataset_type,
            d.notes,
            d.created_at,
            dc.section,
            dc.quantity,
            c.id AS card_id,
            c.name AS card_name,
            c.type AS card_type,
            c.frame_type,
            c.description,
            c.race,
            c.attribute,
            c.archetype AS card_archetype,
            c.ban_tcg,
            c.cardmarket_price
        FROM deck_cards dc
        JOIN decks d ON d.id = dc.deck_id
        LEFT JOIN cards c ON c.id = dc.card_id;
    """
    with get_connection(db_path) as connection:
        return pd.read_sql_query(query, connection)


def _ensure_deck_columns(connection: sqlite3.Connection) -> None:
    """Add optional provenance columns to existing local databases."""

    existing_columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(decks);").fetchall()
    }
    for column_name, column_type in DECK_OPTIONAL_COLUMNS.items():
        if column_name not in existing_columns:
            connection.execute(f"ALTER TABLE decks ADD COLUMN {column_name} {column_type};")


def _coerce_optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
