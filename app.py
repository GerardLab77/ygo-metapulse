"""Streamlit dashboard for YGO MetaPulse."""

from __future__ import annotations

from collections import Counter
from textwrap import dedent

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import (
    apply_filters,
    archetype_breakdown,
    banlist_summary,
    deck_price_estimates,
    engine_detection,
    most_played_cards,
    side_deck_trends,
    staple_usage,
    trend_velocity,
)
from src.db import get_cards_df, get_decks_df, get_joined_deck_cards_df, init_db
from src.ingest import run_full_ingestion
from src.report import generate_meta_report

st.set_page_config(page_title="YGO MetaPulse", layout="wide")

PALETTE = {
    "ink": "#102033",
    "slate": "#5b7086",
    "mist": "#edf2f7",
    "teal": "#0f766e",
    "gold": "#d97706",
    "rose": "#be123c",
}

px.defaults.template = "plotly_white"


def inject_styles() -> None:
    """Apply small dashboard styling improvements."""

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap');

        html, body, [class*="css"]  {{
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
        }}
        [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 30%),
                radial-gradient(circle at top right, rgba(217, 119, 6, 0.08), transparent 22%),
                linear-gradient(180deg, #f7fafc 0%, #eef4f8 100%);
        }}
        .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
        }}
        div[data-testid="stMetric"] {{
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid #dbe4ee;
            border-radius: 18px;
            padding: 0.95rem 1rem;
            box-shadow: 0 8px 24px rgba(16, 32, 51, 0.06);
        }}
        h1, h2, h3, [data-testid="stMetricLabel"] {{
            font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
            letter-spacing: -0.02em;
        }}
        .hero-panel {{
            background: linear-gradient(135deg, rgba(16, 32, 51, 0.96) 0%, rgba(15, 118, 110, 0.92) 100%);
            color: #f8fafc;
            border-radius: 28px;
            padding: 1.6rem 1.8rem 1.4rem;
            box-shadow: 0 24px 60px rgba(16, 32, 51, 0.18);
            margin-bottom: 1.25rem;
        }}
        .hero-kicker {{
            display: inline-block;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: #c7f9f0;
            margin-bottom: 0.55rem;
        }}
        .hero-title {{
            font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
            font-size: 2.15rem;
            line-height: 1.05;
            margin: 0 0 0.45rem;
        }}
        .hero-copy {{
            color: rgba(248, 250, 252, 0.88);
            max-width: 58rem;
            margin: 0;
            font-size: 1rem;
        }}
        .hero-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin-top: 1.15rem;
        }}
        .hero-stat {{
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 16px;
            padding: 0.85rem 0.95rem;
        }}
        .hero-stat-label {{
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: rgba(226, 232, 240, 0.8);
        }}
        .hero-stat-value {{
            font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
            font-size: 1.15rem;
            margin-top: 0.2rem;
        }}
        .section-note {{
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-left: 4px solid {PALETTE["gold"]};
            border-radius: 16px;
            padding: 0.95rem 1rem;
            margin: 0.5rem 0 1rem;
            color: {PALETTE["ink"]};
        }}
        .section-note strong {{
            font-family: "Space Grotesk", "IBM Plex Sans", sans-serif;
        }}
        @media (max-width: 900px) {{
            .hero-grid {{
                grid-template-columns: 1fr;
            }}
            .hero-title {{
                font-size: 1.8rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load cards, decks, and joined deck-card dataframes."""

    init_db()
    return get_cards_df(), get_decks_df(), get_joined_deck_cards_df()


def run_ingestion(force_refresh: bool) -> None:
    """Trigger the ingestion pipeline and refresh cached dashboard data."""

    run_full_ingestion(force_refresh=force_refresh)
    load_data.clear()


def build_engine_frequency(engines_df: pd.DataFrame) -> pd.DataFrame:
    """Expand engine detections into counts for charting."""

    counter: Counter[str] = Counter()
    for value in engines_df.get("detected_engines", pd.Series(dtype=str)).fillna(""):
        for engine in [item.strip() for item in str(value).split(",") if item.strip() and item.strip() != "None detected"]:
            counter[engine] += 1
    if not counter:
        return pd.DataFrame(columns=["engine", "deck_count"])
    return pd.DataFrame(
        [{"engine": engine, "deck_count": count} for engine, count in counter.most_common()]
    )


def get_dataset_mode(decks_df: pd.DataFrame) -> str:
    """Classify the current dataset as sample, tournament, mixed, or empty."""

    if decks_df.empty or "deck_slug" not in decks_df:
        return "empty"
    if "dataset_type" in decks_df:
        dataset_types = {
            str(value).strip().lower()
            for value in decks_df["dataset_type"].dropna().tolist()
            if str(value).strip()
        }
        if dataset_types == {"sample"}:
            return "sample"
        if dataset_types == {"tournament"}:
            return "tournament"
        if "sample" in dataset_types and len(dataset_types) > 1:
            return "mixed"

    deck_slugs = decks_df["deck_slug"].astype(str)
    has_tournament_decks = (~deck_slugs.str.startswith("sample_")).any()
    has_sample_decks = deck_slugs.str.startswith("sample_").any()
    if has_sample_decks and has_tournament_decks:
        return "mixed"
    if has_tournament_decks:
        return "tournament"
    return "sample"


def build_dataset_label(decks_df: pd.DataFrame, dataset_mode: str) -> str:
    """Return a concise human-readable dataset label."""

    if decks_df.empty:
        return "No deck dataset loaded."
    deck_count = int(decks_df["deck_slug"].nunique()) if "deck_slug" in decks_df else len(decks_df)
    event_count = int(decks_df["event_name"].dropna().nunique()) if "event_name" in decks_df else 0
    latest_event = "N/A"
    if "event_date" in decks_df and decks_df["event_date"].notna().any():
        parsed_dates = pd.to_datetime(decks_df["event_date"], errors="coerce")
        if parsed_dates.notna().any():
            latest_event = str(parsed_dates.max().date())

    if dataset_mode == "tournament":
        return f"Verified tournament snapshot: {deck_count} top-cut decklists from {event_count} events. Last updated: {latest_event}."
    if dataset_mode == "sample":
        return f"Illustrative sample fallback: {deck_count} generated decklists. No verified tournament rows loaded."
    if dataset_mode == "mixed":
        return f"Mixed dataset: {deck_count} decklists loaded. Re-run ingestion in tournament mode to avoid mixing samples with imported tournament rows."
    return "No deck dataset loaded."


def render_hero(decks_df: pd.DataFrame, joined_df: pd.DataFrame, dataset_mode: str) -> None:
    """Render the dashboard hero panel."""

    total_decks = int(decks_df["deck_slug"].nunique()) if not decks_df.empty and "deck_slug" in decks_df else 0
    total_cards = int(joined_df["card_id"].nunique()) if not joined_df.empty and "card_id" in joined_df else 0
    latest_event = "N/A"
    if not decks_df.empty and decks_df["event_date"].notna().any():
        latest_event = str(pd.to_datetime(decks_df["event_date"], errors="coerce").max().date())

    dataset_label = {
        "sample": "Illustrative sample fallback",
        "tournament": "Verified tournament snapshot",
        "mixed": "Mixed sample + tournament dataset",
        "empty": "No deck dataset loaded",
    }[dataset_mode]
    dataset_detail = build_dataset_label(decks_df, dataset_mode)

    hero_html = dedent(
        f"""
        <div class="hero-panel">
          <div class="hero-kicker">Decklist Intelligence • Data Engineering + Analytics</div>
          <div class="hero-title">YGO MetaPulse</div>
          <p class="hero-copy">
            Tournament decklist analytics for Yu-Gi-Oh! TCG, built as an end-to-end local pipeline:
            cached YGOPRODeck card metadata, normalized SQLite storage, pandas analysis, and a Streamlit reporting layer.
            {dataset_detail}
          </p>
          <div class="hero-grid">
            <div class="hero-stat">
              <div class="hero-stat-label">Dataset Mode</div>
              <div class="hero-stat-value">{dataset_label}</div>
            </div>
            <div class="hero-stat">
              <div class="hero-stat-label">Decks Loaded</div>
              <div class="hero-stat-value">{total_decks}</div>
            </div>
            <div class="hero-stat">
              <div class="hero-stat-label">Unique Cards / Latest Event</div>
              <div class="hero-stat-value">{total_cards} cards • {latest_event}</div>
            </div>
          </div>
        </div>
        """
    )
    st.markdown(hero_html, unsafe_allow_html=True)


def render_dataset_notice(dataset_mode: str) -> None:
    """Render a contextual note about the dataset currently being shown."""

    if dataset_mode == "sample":
        st.info(
            "Showing illustrative sample decklists generated from cached YGOPRODeck card metadata. "
            "They are useful for running the project offline, but they are not verified tournament results. "
            "Use the manual YGOPRODeck import workflow to load attributed tournament decklists."
        )
    elif dataset_mode == "mixed":
        st.warning(
            "Both sample and tournament deck rows are present. Re-run ingestion with `python -m src.ingest --dataset tournament` "
            "after importing verified decklists to keep tournament statistics separate."
        )
    elif dataset_mode == "tournament":
        st.success(
            "Showing locally imported YGOPRODeck Tournament Meta Decks. These are collected top-cut decklists, "
            "not match win rates or a complete measurement of every deck entered."
        )


def build_sidebar(
    decks_df: pd.DataFrame,
    joined_df: pd.DataFrame,
) -> tuple[
    list[str],
    list[str],
    list[str],
    tuple[pd.Timestamp | None, pd.Timestamp | None],
    str,
    int,
]:
    """Render sidebar controls and return the selected filters."""

    st.sidebar.header("Controls")
    force_refresh = st.sidebar.checkbox("Force refresh card metadata", value=False)
    if st.sidebar.button("Run ingestion / refresh data", type="primary", width="stretch"):
        with st.spinner("Refreshing card metadata, syncing deck files, and rebuilding analytics tables..."):
            run_ingestion(force_refresh)
        st.sidebar.success("Ingestion completed.")
        st.rerun()

    archetype_options = sorted(decks_df["archetype"].dropna().unique().tolist()) if not decks_df.empty else []
    selected_archetypes = st.sidebar.multiselect(
        "Archetype",
        options=archetype_options,
        default=archetype_options,
    )
    event_options = sorted(decks_df["event_name"].dropna().unique().tolist()) if not decks_df.empty else []
    selected_events = st.sidebar.multiselect(
        "Event",
        options=event_options,
        default=event_options,
    )
    placement_options = sorted(decks_df["placement"].dropna().unique().tolist()) if not decks_df.empty else []
    selected_placements = st.sidebar.multiselect(
        "Placement",
        options=placement_options,
        default=placement_options,
    )

    date_series = pd.to_datetime(decks_df["event_date"], errors="coerce") if not decks_df.empty else pd.Series(dtype="datetime64[ns]")
    min_date = date_series.min() if not date_series.empty else None
    max_date = date_series.max() if not date_series.empty else None
    if pd.notna(min_date) and pd.notna(max_date):
        selected_dates = st.sidebar.date_input(
            "Date range",
            value=(min_date.date(), max_date.date()),
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date = pd.Timestamp(selected_dates[0])
            end_date = pd.Timestamp(selected_dates[1])
        else:
            start_date = pd.Timestamp(selected_dates)
            end_date = pd.Timestamp(selected_dates)
    else:
        start_date = None
        end_date = None
        st.sidebar.caption("Date range becomes available after deck data is ingested.")

    section = st.sidebar.selectbox("Deck section", options=["all", "main", "extra", "side"], index=0)
    limit = st.sidebar.slider("Rows / chart items", min_value=5, max_value=30, value=15, step=5)

    st.sidebar.divider()
    st.sidebar.subheader("Dataset Stats")
    latest_event = "N/A"
    if not decks_df.empty and decks_df["event_date"].notna().any():
        latest_event = str(pd.to_datetime(decks_df["event_date"], errors="coerce").max().date())
    st.sidebar.metric("Decks", int(decks_df["deck_slug"].nunique()) if "deck_slug" in decks_df else 0)
    st.sidebar.metric("Unique cards", int(joined_df["card_id"].nunique()) if "card_id" in joined_df else 0)
    st.sidebar.metric("Archetypes", int(decks_df["archetype"].nunique()) if "archetype" in decks_df else 0)
    st.sidebar.metric("Latest event", latest_event)

    return selected_archetypes, selected_events, selected_placements, (start_date, end_date), section, limit


def render_data_provenance(decks_df: pd.DataFrame, dataset_mode: str) -> None:
    """Show the source scope for the currently loaded deck rows."""

    st.subheader("Data Provenance")
    if dataset_mode == "sample":
        st.caption(
            "Current rows are generated sample fixtures. Verified tournament imports are stored separately under "
            "`data/tournament_decks/ygoprodeck/` and replace samples during `--dataset auto` ingestion."
        )
    else:
        st.caption(
            "YGOPRODeck tournament rows are imported from manually downloaded `.ydk` files plus a CSV manifest. "
            "YGO MetaPulse is not affiliated with or endorsed by YGOPRODeck, Konami, or 4K Media."
        )
    provenance_columns = [
        "deck_slug",
        "dataset_type",
        "event_name",
        "event_date",
        "placement",
        "player",
        "player_count",
        "archetype",
        "source_site",
        "source_category",
        "source_url",
        "access_date",
    ]
    available_columns = [column for column in provenance_columns if column in decks_df.columns]
    if available_columns:
        st.dataframe(decks_df[available_columns].sort_values(["event_date", "deck_slug"], ascending=[False, True]), width="stretch", hide_index=True)


def render_empty_state() -> None:
    """Render guidance when the database has no usable data."""

    st.info(
        "No analytics data is available yet. Run `python -m src.ingest` or use the sidebar refresh button to "
        "fetch card metadata, generate sample decklists, and populate the database."
    )
    st.stop()


def main() -> None:
    """Render the dashboard."""

    inject_styles()

    cards_df, decks_df, joined_df = load_data()
    dataset_mode = get_dataset_mode(decks_df)
    render_hero(decks_df, joined_df, dataset_mode)
    render_dataset_notice(dataset_mode)
    (
        selected_archetypes,
        selected_events,
        selected_placements,
        (start_date, end_date),
        section_filter,
        row_limit,
    ) = build_sidebar(decks_df, joined_df)

    if joined_df.empty or decks_df.empty:
        render_empty_state()

    base_filtered = apply_filters(
        joined_df,
        archetypes=selected_archetypes or None,
        events=selected_events or None,
        placements=selected_placements or None,
        start_date=start_date.isoformat() if start_date is not None else None,
        end_date=end_date.isoformat() if end_date is not None else None,
    )
    if base_filtered.empty:
        st.warning("No deck rows match the current archetype/date filters.")
        st.stop()

    filtered_decks = decks_df[decks_df["deck_slug"].isin(base_filtered["deck_slug"].unique())].copy()
    section_filtered = apply_filters(base_filtered, section=section_filter)
    chart_source = section_filtered if not section_filtered.empty else base_filtered

    overview_tab, usage_tab, side_tab, engine_tab, banlist_tab, report_tab, raw_tab = st.tabs(
        [
            "Overview",
            "Card Usage",
            "Side Deck Trends",
            "Engines",
            "Banlist Watch",
            "Meta Report",
            "Raw Data Explorer",
        ]
    )

    with overview_tab:
        price_df = deck_price_estimates(joined_df=base_filtered)
        archetype_df = archetype_breakdown(decks_df=filtered_decks, joined_df=base_filtered)
        trend_df = trend_velocity(decks_df=filtered_decks)
        avg_price = float(price_df["estimated_deck_price"].mean()) if not price_df.empty else 0.0
        metric_columns = st.columns(4)
        metric_columns[0].metric("Total decks", int(filtered_decks["deck_slug"].nunique()))
        metric_columns[1].metric("Unique cards", int(base_filtered["card_id"].nunique()))
        metric_columns[2].metric("Archetypes represented", int(filtered_decks["archetype"].nunique()))
        metric_columns[3].metric("Average estimated deck price", f"{avg_price:.2f}")

        left, right = st.columns(2)
        with left:
            if not archetype_df.empty:
                archetype_chart = px.bar(
                    archetype_df,
                    x="archetype",
                    y="deck_count",
                    color="deck_share_percent",
                    text="deck_share_percent",
                    title="Archetype Distribution",
                    labels={"deck_count": "Deck count", "deck_share_percent": "Deck share (%)"},
                    color_continuous_scale="Blues",
                )
                archetype_chart.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                archetype_chart.update_layout(showlegend=False)
                st.plotly_chart(archetype_chart, width="stretch")
            else:
                st.caption("No archetype rows available for the selected filters.")
        with right:
            if not price_df.empty:
                price_chart = (
                    price_df.groupby("deck_archetype", dropna=False)
                    .agg(average_estimated_deck_price=("estimated_deck_price", "mean"))
                    .reset_index()
                    .sort_values("average_estimated_deck_price", ascending=False)
                )
                deck_price_chart = px.bar(
                    price_chart,
                    x="deck_archetype",
                    y="average_estimated_deck_price",
                    color="average_estimated_deck_price",
                    title="Deck Price by Archetype",
                    labels={
                        "deck_archetype": "Archetype",
                        "average_estimated_deck_price": "Average estimated price",
                    },
                    color_continuous_scale="Tealgrn",
                )
                deck_price_chart.update_layout(showlegend=False)
                st.plotly_chart(deck_price_chart, width="stretch")
            else:
                st.caption("Price data becomes richer when Cardmarket values are available in the API cache.")

        st.markdown(
            """
            <div class="section-note">
              <strong>What this view is showing:</strong> archetype share, estimated market value, and a lightweight trend layer intended
              to show how imported decklists can be transformed into structured metagame analysis.
            </div>
            """,
            unsafe_allow_html=True,
        )

        lower_left, lower_right = st.columns([1.15, 1])
        with lower_left:
            st.subheader("Trend Velocity")
            if not trend_df.empty:
                trend_chart = px.bar(
                    trend_df.head(8),
                    x="archetype",
                    y="trend_score",
                    color="recent_deck_count",
                    text="recent_deck_count",
                    title="Recency-Weighted Archetype Momentum",
                    labels={
                        "archetype": "Archetype",
                        "trend_score": "Trend score",
                        "recent_deck_count": "Recent decks",
                    },
                    color_continuous_scale="Teal",
                )
                trend_chart.update_traces(textposition="outside")
                trend_chart.update_layout(showlegend=False)
                st.plotly_chart(trend_chart, width="stretch")
                st.caption(trend_df["note"].iloc[0])
            else:
                st.caption("Trend velocity appears after dated deck metadata is available.")
        with lower_right:
            st.subheader("Archetype Summary")
            summary_columns = [
                "archetype",
                "deck_count",
                "deck_share_percent",
                "average_estimated_deck_price",
            ]
            st.dataframe(
                archetype_df[summary_columns].head(row_limit),
                width="stretch",
                hide_index=True,
            )
        render_data_provenance(filtered_decks, dataset_mode)

    with usage_tab:
        st.caption(f"Section filter applied: `{section_filter}`")
        usage_df = most_played_cards(
            section=None if section_filter == "all" else section_filter,
            limit=row_limit,
            joined_df=chart_source,
        )
        if usage_df.empty:
            st.info("No card usage rows match the current filters.")
        else:
            chart = px.bar(
                usage_df.sort_values("deck_inclusion_rate", ascending=True),
                x="deck_inclusion_rate",
                y="card_name",
                orientation="h",
                color="total_copies",
                title="Deck Inclusion Rate",
                labels={"deck_inclusion_rate": "Inclusion rate (%)", "card_name": "Card"},
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(chart, width="stretch")
            st.dataframe(usage_df, width="stretch", hide_index=True)

        staples_df = staple_usage(
            section="main" if section_filter == "all" else section_filter,
            limit=row_limit,
            joined_df=base_filtered if section_filter == "all" else chart_source,
        )
        st.subheader("Cross-Archetype Staples")
        st.dataframe(staples_df, width="stretch", hide_index=True)

    with side_tab:
        st.markdown(
            "Side deck trends matter because they reveal what players expect to face. "
            "When the same answers keep appearing, they usually point to format-defining threats."
        )
        side_df = side_deck_trends(limit=row_limit, joined_df=base_filtered)
        if side_df.empty:
            st.info("No side deck data is available for the current filters.")
        else:
            side_chart = px.bar(
                side_df.sort_values("total_copies", ascending=True),
                x="total_copies",
                y="card_name",
                orientation="h",
                color="decks_seen",
                title="Most Common Side Deck Cards",
                labels={"total_copies": "Copies", "card_name": "Card", "decks_seen": "Decks seen"},
                color_continuous_scale="Sunset",
            )
            st.plotly_chart(side_chart, width="stretch")
            st.dataframe(side_df, width="stretch", hide_index=True)

    with engine_tab:
        engines_df = engine_detection(joined_df=base_filtered)
        engine_frequency_df = build_engine_frequency(engines_df)
        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("Detected Engines by Deck")
            st.dataframe(engines_df, width="stretch", hide_index=True)
        with right:
            if not engine_frequency_df.empty:
                engine_chart = px.bar(
                    engine_frequency_df,
                    x="engine",
                    y="deck_count",
                    color="deck_count",
                    title="Engine Frequency",
                    color_continuous_scale="Mint",
                )
                engine_chart.update_layout(showlegend=False)
                st.plotly_chart(engine_chart, width="stretch")
            else:
                st.caption("No engine keywords were detected in the filtered sample.")

    with banlist_tab:
        st.markdown(
            "This view surfaces cards with recorded TCG banlist status so you can quickly spot lists that rely on "
            "high-scrutiny pieces when formats shift."
        )
        banlist_df = banlist_summary(joined_df=base_filtered)
        if banlist_df.empty:
            st.success("No forbidden, limited, or semi-limited cards were surfaced in the current sample.")
        else:
            st.dataframe(banlist_df, width="stretch", hide_index=True)

    with report_tab:
        if "meta_report" not in st.session_state:
            st.session_state["meta_report"] = generate_meta_report(decks_df=filtered_decks, joined_df=base_filtered)
        if st.button("Regenerate report"):
            st.session_state["meta_report"] = generate_meta_report(decks_df=filtered_decks, joined_df=base_filtered)
        st.caption("Narrative report generated deterministically from the analytics layer. No LLM call is required.")
        st.markdown(st.session_state["meta_report"])

    with raw_tab:
        st.subheader("Decks")
        st.dataframe(filtered_decks, width="stretch", hide_index=True)
        st.subheader("Joined Deck / Card Rows")
        st.dataframe(base_filtered, width="stretch", hide_index=True)
        st.caption(f"Loaded {len(cards_df):,} cached card metadata rows.")


if __name__ == "__main__":
    main()
