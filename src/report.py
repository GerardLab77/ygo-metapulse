"""Human-readable reporting utilities."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from src.analysis import (
    archetype_breakdown,
    banlist_summary,
    deck_price_estimates,
    engine_detection,
    most_played_cards,
    side_deck_trends,
    trend_velocity,
)
from src.db import get_decks_df, get_joined_deck_cards_df


def generate_meta_report(
    db_path: Path | None = None,
    decks_df: pd.DataFrame | None = None,
    joined_df: pd.DataFrame | None = None,
) -> str:
    """Generate a concise meta report without an LLM dependency."""

    decks = decks_df.copy() if decks_df is not None else get_decks_df(db_path)
    joined = joined_df.copy() if joined_df is not None else get_joined_deck_cards_df(db_path)
    if decks.empty or joined.empty:
        return (
            "## Meta Report\n\n"
            "No deck data is available yet. Run the ingestion pipeline to fetch card metadata, "
            "generate sample decklists, and populate the analytics database."
        )

    archetypes = archetype_breakdown(db_path=db_path, decks_df=decks, joined_df=joined).head(3)
    main_cards = most_played_cards(section="main", limit=5, db_path=db_path, joined_df=joined)
    extra_cards = most_played_cards(section="extra", limit=5, db_path=db_path, joined_df=joined)
    side_cards = side_deck_trends(limit=5, db_path=db_path, joined_df=joined)
    engines = engine_detection(db_path=db_path, joined_df=joined)
    prices = deck_price_estimates(db_path=db_path, joined_df=joined)
    banlist = banlist_summary(db_path=db_path, joined_df=joined).head(5)
    trends = trend_velocity(db_path=db_path, decks_df=decks).head(3)

    top_archetypes = ", ".join(
        f"{row.archetype} ({int(row.deck_count)} deck{'s' if row.deck_count != 1 else ''}, {row.sample_percentage:.1f}% share)"
        for row in archetypes.itertuples()
    )
    top_main_cards = ", ".join(
        f"{row.card_name} ({int(row.total_copies)} copies across {int(row.decks_seen)} decks)"
        for row in main_cards.itertuples()
    )
    top_extra_cards = ", ".join(
        f"{row.card_name} ({int(row.total_copies)} copies)"
        for row in extra_cards.itertuples()
    )
    top_side_cards = ", ".join(
        f"{row.card_name} ({int(row.total_copies)} copies)"
        for row in side_cards.itertuples()
    )
    engine_counter: Counter[str] = Counter()
    for row in engines.itertuples():
        for engine in [item.strip() for item in str(row.detected_engines).split(",") if item.strip() and item.strip() != "None detected"]:
            engine_counter[engine] += 1
    notable_engines = "No recurring engine package surfaced in the current sample."
    if engine_counter:
        notable_engines = ", ".join(
            f"{engine} ({count} deck{'s' if count != 1 else ''})"
            for engine, count in engine_counter.most_common(5)
        )
    price_line = "No price data available."
    if not prices.empty:
        avg_price = prices["estimated_deck_price"].mean()
        highest = prices.iloc[0]
        lowest = prices.iloc[-1]
        price_line = (
            f"Estimated deck prices average {avg_price:.2f} based on available Cardmarket metadata. "
            f"{highest.deck_archetype} currently reads highest at {highest.estimated_deck_price:.2f}, "
            f"while {lowest.deck_archetype} is lowest at {lowest.estimated_deck_price:.2f}."
        )
    banlist_line = "No forbidden, limited, or semi-limited cards were flagged in the current sample."
    if not banlist.empty:
        banlist_line = ", ".join(
            f"{row.card_name} ({row.ban_tcg})" for row in banlist.itertuples()
        )
    trend_line = "Trend data is minimal."
    if not trends.empty:
        trend_line = ", ".join(
            f"{row.archetype} (score {row.trend_score:.3f})" for row in trends.itertuples()
        )

    return f"""## Meta Report

### Executive Summary

- Archetype representation is currently led by {top_archetypes}.
- Main deck usage is concentrated around {top_main_cards}.
- The most common extra deck conversion pieces are {top_extra_cards}.

### Competitive Signals

- Side-deck coverage is led by {top_side_cards}.
- Engine detection highlights the following patterns: {notable_engines}.
- {price_line}

### Risk Watch

- Banlist-sensitive cards in the current sample: {banlist_line}.
- Early trend velocity currently favors {trend_line}.

### Caveat

_This report is based on the decklists currently loaded into SQLite. Bundled sample lists are illustrative, not verified tournament results; confidence improves as more dated tournament lists are imported._"""
