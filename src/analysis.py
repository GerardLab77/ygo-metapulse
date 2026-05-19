"""Analytics layer for YGO MetaPulse."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src import db

ENGINE_RULES = {
    "Bystial": ("bystial",),
    "Mulcharmy": ("mulcharmy",),
    "Dominus": ("dominus",),
    "Primite": ("primite",),
    "Fiendsmith": ("fiendsmith",),
    "Kashtira": ("kashtira",),
    "Sky Striker": ("sky striker",),
    "Orcust": ("orcust",),
    "Blue-Eyes": ("blue-eyes", "blue eyes"),
    "Maliss": ("maliss", "m∀lice", "malice"),
}


def load_joined_data(db_path: Path | None = None) -> pd.DataFrame:
    """Return the joined deck-card dataset."""

    return db.get_joined_deck_cards_df(db_path)


def load_decks_data(db_path: Path | None = None) -> pd.DataFrame:
    """Return the decks dataset."""

    return db.get_decks_df(db_path)


def apply_filters(
    joined_df: pd.DataFrame,
    archetypes: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    section: str | None = None,
) -> pd.DataFrame:
    """Apply archetype, date, and section filters to a joined dataframe."""

    if joined_df.empty:
        return joined_df.copy()

    filtered = joined_df.copy()
    if archetypes:
        filtered = filtered[filtered["deck_archetype"].isin(archetypes)]
    if start_date or end_date:
        filtered["event_date"] = pd.to_datetime(filtered["event_date"], errors="coerce")
        if start_date:
            filtered = filtered[filtered["event_date"] >= pd.Timestamp(start_date)]
        if end_date:
            filtered = filtered[filtered["event_date"] <= pd.Timestamp(end_date)]
    if section and section.lower() != "all":
        filtered = filtered[filtered["section"] == section.lower()]
    return filtered


def most_played_cards(
    section: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the most played cards and inclusion metrics."""

    data = joined_df.copy() if joined_df is not None else load_joined_data(db_path)
    if data.empty:
        return pd.DataFrame(
            columns=["card_name", "card_type", "card_archetype", "total_copies", "decks_seen", "deck_inclusion_rate"]
        )

    if section and section.lower() != "all":
        data = data[data["section"] == section.lower()]
    total_decks = data["deck_slug"].nunique()
    grouped = (
        data.groupby(["card_name", "card_type", "card_archetype"], dropna=False)
        .agg(total_copies=("quantity", "sum"), decks_seen=("deck_slug", "nunique"))
        .reset_index()
    )
    grouped["deck_inclusion_rate"] = (
        (grouped["decks_seen"] / total_decks * 100).round(1) if total_decks else 0.0
    )
    return grouped.sort_values(
        by=["total_copies", "decks_seen", "card_name"],
        ascending=[False, False, True],
    ).head(limit)


def deck_price_estimates(
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Estimate deck prices using cached Cardmarket values."""

    data = joined_df.copy() if joined_df is not None else load_joined_data(db_path)
    if data.empty:
        return pd.DataFrame(
            columns=[
                "deck_slug",
                "deck_archetype",
                "event_name",
                "event_date",
                "estimated_deck_price",
                "priced_copy_ratio",
            ]
        )

    working = data.copy()
    working["cardmarket_price"] = pd.to_numeric(working["cardmarket_price"], errors="coerce")
    working["priced_quantity"] = working["quantity"].where(working["cardmarket_price"].notna(), 0)
    working["price_component"] = working["quantity"] * working["cardmarket_price"].fillna(0)
    summary = (
        working.groupby(["deck_slug", "deck_archetype", "event_name", "event_date"], dropna=False)
        .agg(
            estimated_deck_price=("price_component", "sum"),
            total_copies=("quantity", "sum"),
            priced_copies=("priced_quantity", "sum"),
        )
        .reset_index()
    )
    summary["priced_copy_ratio"] = (
        (summary["priced_copies"] / summary["total_copies"] * 100).round(1)
    ).fillna(0.0)
    return summary.drop(columns=["total_copies", "priced_copies"]).sort_values(
        by="estimated_deck_price", ascending=False
    )


def archetype_breakdown(
    db_path: Path | None = None,
    decks_df: pd.DataFrame | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return deck share and average price by archetype."""

    decks = decks_df.copy() if decks_df is not None else load_decks_data(db_path)
    if decks.empty:
        return pd.DataFrame(columns=["archetype", "deck_count", "sample_percentage", "average_estimated_deck_price"])

    prices = deck_price_estimates(db_path=db_path, joined_df=joined_df)
    total_decks = len(decks)
    grouped = decks.groupby("archetype", dropna=False).agg(deck_count=("deck_slug", "count")).reset_index()
    grouped["sample_percentage"] = (grouped["deck_count"] / total_decks * 100).round(1)
    avg_prices = (
        prices.groupby("deck_archetype", dropna=False)
        .agg(average_estimated_deck_price=("estimated_deck_price", "mean"))
        .reset_index()
    )
    merged = grouped.merge(
        avg_prices,
        left_on="archetype",
        right_on="deck_archetype",
        how="left",
    ).drop(columns=["deck_archetype"])
    merged["average_estimated_deck_price"] = merged["average_estimated_deck_price"].round(2)
    return merged.sort_values(by=["deck_count", "archetype"], ascending=[False, True])


def staple_usage(
    section: str = "main",
    limit: int = 20,
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return cards used across multiple archetypes as generic staples."""

    data = joined_df.copy() if joined_df is not None else load_joined_data(db_path)
    if data.empty:
        return pd.DataFrame(columns=["card_name", "archetypes_using", "decks_seen", "total_copies"])
    data = data[data["section"] == section.lower()]
    grouped = (
        data.groupby(["card_name", "card_type", "card_archetype"], dropna=False)
        .agg(
            archetypes_using=("deck_archetype", "nunique"),
            decks_seen=("deck_slug", "nunique"),
            total_copies=("quantity", "sum"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["archetypes_using"] > 1]
    return grouped.sort_values(
        by=["archetypes_using", "decks_seen", "total_copies", "card_name"],
        ascending=[False, False, False, True],
    ).head(limit)


def side_deck_trends(
    limit: int = 20,
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return the most common side deck cards."""

    return most_played_cards(section="side", limit=limit, db_path=db_path, joined_df=joined_df)


def banlist_summary(
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return cards with TCG banlist statuses found in loaded decklists."""

    data = joined_df.copy() if joined_df is not None else load_joined_data(db_path)
    if data.empty:
        return pd.DataFrame(columns=["card_name", "ban_tcg", "decks_seen", "total_copies"])
    filtered = data[data["ban_tcg"].notna() & data["ban_tcg"].ne("")]
    summary = (
        filtered.groupby(["card_name", "ban_tcg"], dropna=False)
        .agg(total_copies=("quantity", "sum"), decks_seen=("deck_slug", "nunique"))
        .reset_index()
    )
    priority = {"Forbidden": 0, "Limited": 1, "Semi-Limited": 2}
    summary["_priority"] = summary["ban_tcg"].map(priority).fillna(3)
    return summary.sort_values(
        by=["_priority", "decks_seen", "total_copies", "card_name"],
        ascending=[True, False, False, True],
    ).drop(columns="_priority")


def engine_detection(
    db_path: Path | None = None,
    joined_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Detect engines by simple keyword matching over deck metadata and card names."""

    data = joined_df.copy() if joined_df is not None else load_joined_data(db_path)
    if data.empty:
        return pd.DataFrame(columns=["deck_slug", "deck_archetype", "detected_engines"])

    rows: list[dict[str, str]] = []
    for deck_slug, deck_df in data.groupby("deck_slug"):
        card_blob = " ".join(deck_df["card_name"].fillna("").astype(str)).lower()
        archetype_blob = " ".join(deck_df["deck_archetype"].fillna("").astype(str)).lower()
        detected = [
            engine
            for engine, keywords in ENGINE_RULES.items()
            if any(keyword in archetype_blob or keyword in card_blob for keyword in keywords)
        ]
        rows.append(
            {
                "deck_slug": deck_slug,
                "deck_archetype": deck_df["deck_archetype"].iloc[0],
                "detected_engines": ", ".join(detected) if detected else "None detected",
            }
        )
    return pd.DataFrame(rows).sort_values(by=["deck_archetype", "deck_slug"])


def trend_velocity(
    db_path: Path | None = None,
    decks_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Calculate a simple recency-weighted archetype trend score."""

    decks = decks_df.copy() if decks_df is not None else load_decks_data(db_path)
    if decks.empty:
        return pd.DataFrame(
            columns=["archetype", "recent_deck_count", "previous_deck_count", "inclusion_rate_delta", "trend_score", "note"]
        )

    working = decks.copy()
    working["event_date"] = pd.to_datetime(working["event_date"], errors="coerce")
    working = working.dropna(subset=["event_date"])
    if working.empty:
        return pd.DataFrame(
            columns=["archetype", "recent_deck_count", "previous_deck_count", "inclusion_rate_delta", "trend_score", "note"]
        )

    latest_date = working["event_date"].max()
    recent_cutoff = latest_date - pd.Timedelta(days=30)
    previous_cutoff = recent_cutoff - pd.Timedelta(days=30)

    recent = working[working["event_date"] >= recent_cutoff]
    previous = working[(working["event_date"] < recent_cutoff) & (working["event_date"] >= previous_cutoff)]

    recent_counts = recent.groupby("archetype").size().rename("recent_deck_count")
    previous_counts = previous.groupby("archetype").size().rename("previous_deck_count")
    summary = pd.concat([recent_counts, previous_counts], axis=1).fillna(0).reset_index()
    total_recent = max(len(recent), 1)
    total_previous = max(len(previous), 1)
    summary["inclusion_rate_delta"] = (
        summary["recent_deck_count"] / total_recent - summary["previous_deck_count"] / total_previous
    ).round(3)
    summary["trend_score"] = (summary["recent_deck_count"] + summary["inclusion_rate_delta"]).round(3)
    note = "Trend confidence is limited; more dated decklists improve signal." if len(working) < 12 else "Trend signal improves as the sample grows."
    summary["note"] = note
    return summary.sort_values(by=["trend_score", "recent_deck_count"], ascending=[False, False])
