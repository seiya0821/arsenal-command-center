from __future__ import annotations

from datetime import datetime

import feedparser
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


st.set_page_config(page_title="Arsenal Tactical Dashboard", layout="wide")

ARSENAL_RED = "#EF4444"
ARSENAL_GOLD = "#FBBF24"
PANEL_BG = "#111827"
APP_BG = "#07111F"
PITCH_BG = "#0F3B2E"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#94A3B8"
BORDER = "rgba(148, 163, 184, 0.18)"

st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(239, 68, 68, 0.16), transparent 30%),
            radial-gradient(circle at top right, rgba(251, 191, 36, 0.12), transparent 25%),
            linear-gradient(180deg, #08111d 0%, #050b14 100%);
        color: {TEXT_MAIN};
    }}
    .block-container {{
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.98), rgba(15, 23, 42, 0.92));
        border: 1px solid {BORDER};
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.22);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED};
    }}
    div[data-testid="stMetricValue"] {{
        color: {TEXT_MAIN};
    }}
    .panel {{
        background: linear-gradient(180deg, rgba(17, 24, 39, 0.95), rgba(15, 23, 42, 0.92));
        border: 1px solid {BORDER};
        border-radius: 22px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 20px 45px rgba(0, 0, 0, 0.18);
    }}
    .hero {{
        padding: 24px 28px;
        border-radius: 24px;
        border: 1px solid rgba(251, 191, 36, 0.18);
        background:
            linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(15, 23, 42, 0.9) 42%),
            linear-gradient(180deg, rgba(17, 24, 39, 0.92), rgba(15, 23, 42, 0.98));
        margin-bottom: 18px;
    }}
    .hero-kicker {{
        color: {ARSENAL_GOLD};
        font-size: 0.82rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        font-weight: 700;
    }}
    .hero-title {{
        font-size: 2.15rem;
        font-weight: 800;
        margin-top: 0.35rem;
        margin-bottom: 0.45rem;
    }}
    .hero-subtitle {{
        color: {TEXT_MUTED};
        font-size: 0.98rem;
        max-width: 56rem;
    }}
    .small-note {{
        color: {TEXT_MUTED};
        font-size: 0.88rem;
    }}
    .news-link a {{
        color: {TEXT_MAIN};
        text-decoration: none;
    }}
    .news-link a:hover {{
        color: {ARSENAL_GOLD};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


def load_match_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "match_id": "WHU-A-PL",
                "date": "2026-02-21",
                "competition": "Premier League",
                "venue": "Away",
                "opponent": "West Ham United",
                "score": "3-1",
                "arsenal_goals": 3,
                "opponent_goals": 1,
                "xg_for": 2.34,
                "xg_against": 0.78,
                "shots": 17,
                "shots_on_target": 8,
                "possession": 61,
                "pass_accuracy": 89,
                "ppda": 7.8,
                "field_tilt": 66,
            },
            {
                "match_id": "PSV-H-UCL",
                "date": "2026-02-25",
                "competition": "Champions League",
                "venue": "Home",
                "opponent": "PSV Eindhoven",
                "score": "2-0",
                "arsenal_goals": 2,
                "opponent_goals": 0,
                "xg_for": 1.91,
                "xg_against": 0.62,
                "shots": 14,
                "shots_on_target": 6,
                "possession": 58,
                "pass_accuracy": 91,
                "ppda": 8.6,
                "field_tilt": 63,
            },
            {
                "match_id": "NEW-H-PL",
                "date": "2026-03-01",
                "competition": "Premier League",
                "venue": "Home",
                "opponent": "Newcastle United",
                "score": "1-1",
                "arsenal_goals": 1,
                "opponent_goals": 1,
                "xg_for": 1.48,
                "xg_against": 1.01,
                "shots": 13,
                "shots_on_target": 4,
                "possession": 57,
                "pass_accuracy": 88,
                "ppda": 10.4,
                "field_tilt": 59,
            },
            {
                "match_id": "ATL-A-UCL",
                "date": "2026-03-05",
                "competition": "Champions League",
                "venue": "Away",
                "opponent": "Atletico Madrid",
                "score": "2-1",
                "arsenal_goals": 2,
                "opponent_goals": 1,
                "xg_for": 1.67,
                "xg_against": 1.19,
                "shots": 11,
                "shots_on_target": 5,
                "possession": 53,
                "pass_accuracy": 86,
                "ppda": 9.1,
                "field_tilt": 55,
            },
            {
                "match_id": "CHE-H-PL",
                "date": "2026-03-09",
                "competition": "Premier League",
                "venue": "Home",
                "opponent": "Chelsea",
                "score": "2-1",
                "arsenal_goals": 2,
                "opponent_goals": 1,
                "xg_for": 2.07,
                "xg_against": 0.96,
                "shots": 16,
                "shots_on_target": 7,
                "possession": 60,
                "pass_accuracy": 90,
                "ppda": 8.2,
                "field_tilt": 64,
            },
        ]
    )


def load_player_match_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["CHE-H-PL", "Bukayo Saka", 0.62, 4, 6, 2, 27, 8],
            ["CHE-H-PL", "Martin Odegaard", 0.21, 2, 4, 0, 61, 6],
            ["CHE-H-PL", "Declan Rice", 0.08, 1, 2, 9, 72, 12],
            ["CHE-H-PL", "Kai Havertz", 0.47, 3, 2, 3, 24, 5],
            ["CHE-H-PL", "Gabriel Martinelli", 0.33, 3, 3, 4, 18, 7],
            ["ATL-A-UCL", "Bukayo Saka", 0.41, 3, 4, 2, 23, 7],
            ["ATL-A-UCL", "Martin Odegaard", 0.12, 1, 5, 1, 58, 5],
            ["ATL-A-UCL", "Declan Rice", 0.05, 1, 2, 11, 68, 10],
            ["ATL-A-UCL", "Kai Havertz", 0.54, 4, 1, 2, 19, 4],
            ["ATL-A-UCL", "Gabriel Martinelli", 0.18, 2, 2, 3, 17, 6],
            ["PSV-H-UCL", "Bukayo Saka", 0.44, 3, 5, 1, 26, 6],
            ["PSV-H-UCL", "Martin Odegaard", 0.16, 2, 6, 1, 63, 4],
            ["PSV-H-UCL", "Declan Rice", 0.09, 1, 3, 10, 75, 11],
            ["PSV-H-UCL", "Kai Havertz", 0.38, 3, 1, 3, 22, 5],
            ["PSV-H-UCL", "Gabriel Martinelli", 0.29, 2, 3, 4, 20, 5],
        ],
        columns=[
            "match_id",
            "player",
            "xg",
            "shots",
            "key_passes",
            "recoveries",
            "completed_passes",
            "progressive_passes",
        ],
    )


def load_shot_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["CHE-H-PL", "Bukayo Saka", 103, 28, 0.18, "Goal", 14],
            ["CHE-H-PL", "Kai Havertz", 109, 40, 0.31, "Saved", 23],
            ["CHE-H-PL", "Gabriel Martinelli", 95, 56, 0.12, "Off Target", 35],
            ["CHE-H-PL", "Martin Odegaard", 87, 41, 0.08, "Blocked", 48],
            ["CHE-H-PL", "Bukayo Saka", 101, 50, 0.22, "Saved", 67],
            ["CHE-H-PL", "Kai Havertz", 111, 36, 0.27, "Goal", 81],
            ["ATL-A-UCL", "Bukayo Saka", 100, 27, 0.14, "Saved", 12],
            ["ATL-A-UCL", "Kai Havertz", 106, 39, 0.29, "Goal", 29],
            ["ATL-A-UCL", "Gabriel Martinelli", 92, 58, 0.09, "Blocked", 44],
            ["ATL-A-UCL", "Martin Odegaard", 85, 36, 0.07, "Off Target", 61],
            ["ATL-A-UCL", "Bukayo Saka", 103, 46, 0.19, "Goal", 74],
            ["PSV-H-UCL", "Bukayo Saka", 104, 29, 0.21, "Goal", 19],
            ["PSV-H-UCL", "Kai Havertz", 108, 40, 0.24, "Saved", 40],
            ["PSV-H-UCL", "Gabriel Martinelli", 97, 55, 0.11, "Off Target", 52],
            ["PSV-H-UCL", "Martin Odegaard", 91, 37, 0.09, "Blocked", 69],
        ],
        columns=["match_id", "player", "x", "y", "xg", "result", "minute"],
    )


def load_pass_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["CHE-H-PL", "Martin Odegaard", 46, 54, 70, 60, "Complete", "Final third entry"],
            ["CHE-H-PL", "Declan Rice", 33, 38, 58, 43, "Complete", "Line break"],
            ["CHE-H-PL", "Jurrien Timber", 28, 66, 52, 58, "Complete", "Switch"],
            ["CHE-H-PL", "Bukayo Saka", 74, 58, 98, 44, "Complete", "Cutback"],
            ["CHE-H-PL", "Leandro Trossard", 71, 22, 95, 34, "Incomplete", "Cross"],
            ["CHE-H-PL", "William Saliba", 36, 24, 62, 32, "Complete", "Vertical"],
            ["ATL-A-UCL", "Martin Odegaard", 44, 53, 65, 56, "Complete", "Pocket pass"],
            ["ATL-A-UCL", "Declan Rice", 31, 35, 55, 41, "Complete", "Line break"],
            ["ATL-A-UCL", "Jurrien Timber", 22, 65, 47, 60, "Incomplete", "Switch"],
            ["ATL-A-UCL", "Bukayo Saka", 76, 56, 97, 46, "Complete", "Cutback"],
            ["ATL-A-UCL", "Kai Havertz", 68, 39, 92, 38, "Complete", "Layoff"],
            ["PSV-H-UCL", "Martin Odegaard", 42, 52, 68, 58, "Complete", "Final third entry"],
            ["PSV-H-UCL", "Declan Rice", 29, 37, 59, 42, "Complete", "Diagonal"],
            ["PSV-H-UCL", "Bukayo Saka", 77, 57, 101, 45, "Complete", "Cutback"],
            ["PSV-H-UCL", "Gabriel Martinelli", 72, 20, 96, 30, "Complete", "Cross"],
        ],
        columns=["match_id", "player", "x_start", "y_start", "x_end", "y_end", "outcome", "type"],
    )


def load_injuries() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["Gabriel Jesus", "Hamstring", "Out", "Late March 2026"],
            ["Oleksandr Zinchenko", "Calf", "Doubt", "Matchday decision"],
            ["Takehiro Tomiyasu", "Knee management", "Monitoring", "Early April 2026"],
            ["Thomas Partey", "Load management", "Limited training", "Available soon"],
            ["Jurrien Timber", "Available", "Fit", "Now"],
        ],
        columns=["Player", "Issue", "Status", "Expected Return"],
    )


def format_match_label(row: pd.Series) -> str:
    date_label = pd.to_datetime(row["date"]).strftime("%d %b %Y")
    return f"{date_label} | {row['competition']} | vs {row['opponent']}"


def fetch_arsenal_news() -> list[dict[str, str]]:
    rss_url = "https://news.google.com/rss/search?q=Arsenal+FC&hl=en-GB&gl=GB&ceid=GB:en"
    fallback_items = [
        {
            "title": "Arsenal tactical dashboard is using offline fallback headlines.",
            "link": "",
            "published": "Unavailable",
        },
        {
            "title": "Reconnect to load the latest Arsenal news feed from Google News RSS.",
            "link": "",
            "published": "Unavailable",
        },
    ]

    try:
        response = requests.get(rss_url, timeout=8)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        items = []
        for entry in feed.entries[:6]:
            published = entry.get("published", "")
            if published:
                try:
                    published = datetime(*entry.published_parsed[:6]).strftime("%d %b %Y")
                except Exception:
                    pass
            items.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": published or "Latest",
                }
            )
        return items or fallback_items
    except Exception:
        return fallback_items


def base_figure_layout(fig: go.Figure, height: int = 420) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=12, r=12, t=48, b=12),
        height=height,
        legend_title_text="",
    )
    return fig


def add_pitch_shapes(fig: go.Figure) -> None:
    line = dict(color="rgba(255,255,255,0.72)", width=2)
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, line=line)
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80, line=line)
    fig.add_shape(type="circle", x0=50, y0=30, x1=70, y1=50, line=line)
    fig.add_shape(type="circle", x0=59.3, y0=39.3, x1=60.7, y1=40.7, line=line, fillcolor="white")
    fig.add_shape(type="rect", x0=0, y0=18, x1=18, y1=62, line=line)
    fig.add_shape(type="rect", x0=102, y0=18, x1=120, y1=62, line=line)
    fig.add_shape(type="rect", x0=0, y0=30, x1=6, y1=50, line=line)
    fig.add_shape(type="rect", x0=114, y0=30, x1=120, y1=50, line=line)
    fig.add_shape(type="circle", x0=11.3, y0=39.3, x1=12.7, y1=40.7, line=line, fillcolor="white")
    fig.add_shape(type="circle", x0=107.3, y0=39.3, x1=108.7, y1=40.7, line=line, fillcolor="white")


def create_shot_map(shots: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        margin=dict(l=8, r=8, t=48, b=8),
        height=500,
        font=dict(color=TEXT_MAIN),
    )
    add_pitch_shapes(fig)

    color_map = {
        "Goal": ARSENAL_RED,
        "Saved": ARSENAL_GOLD,
        "Blocked": "#38BDF8",
        "Off Target": "#CBD5E1",
    }

    fig.add_trace(
        go.Scatter(
            x=shots["x"],
            y=shots["y"],
            mode="markers+text",
            text=shots["player"],
            textposition="top center",
            marker=dict(
                size=shots["xg"] * 85 + 12,
                color=[color_map.get(result, "#CBD5E1") for result in shots["result"]],
                line=dict(color="white", width=1.2),
                opacity=0.92,
            ),
            customdata=shots[["minute", "xg", "result"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Minute: %{customdata[0]}'<br>"
                "xG: %{customdata[1]:.2f}<br>"
                "Result: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def create_pass_map(passes: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        margin=dict(l=8, r=8, t=48, b=8),
        height=500,
        font=dict(color=TEXT_MAIN),
    )
    add_pitch_shapes(fig)

    for row in passes.itertuples(index=False):
        color = "rgba(248, 250, 252, 0.85)" if row.outcome == "Complete" else "rgba(239, 68, 68, 0.78)"
        width = 3 if row.outcome == "Complete" else 2
        fig.add_annotation(
            x=row.x_end,
            y=row.y_end,
            ax=row.x_start,
            ay=row.y_start,
            xref="x",
            yref="y",
            axref="x",
            ayref="y",
            showarrow=True,
            arrowhead=3,
            arrowsize=1,
            arrowwidth=width,
            arrowcolor=color,
            opacity=0.95,
        )

    fig.add_trace(
        go.Scatter(
            x=passes["x_start"],
            y=passes["y_start"],
            mode="markers",
            marker=dict(
                size=9,
                color=[ARSENAL_GOLD if result == "Complete" else ARSENAL_RED for result in passes["outcome"]],
                line=dict(color="white", width=0.8),
            ),
            text=passes["player"],
            customdata=passes[["type", "outcome"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Pass type: %{customdata[0]}<br>"
                "Outcome: %{customdata[1]}<extra></extra>"
            ),
            showlegend=False,
        )
    )

    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


matches_df = load_match_data()
matches_df["date"] = pd.to_datetime(matches_df["date"])
player_df = load_player_match_data()
shot_df = load_shot_data()
pass_df = load_pass_data()
injuries_df = load_injuries()

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Arsenal Analytics</div>
        <div class="hero-title">Arsenal Tactical Dashboard</div>
        <div class="hero-subtitle">
            Track recent Premier League and Champions League performances, inspect player output,
            and review pitch-level shot and pass patterns in one Streamlit workspace.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Match Controls")
    competition_filter = st.multiselect(
        "Competition",
        options=["Premier League", "Champions League"],
        default=["Premier League", "Champions League"],
    )
    filtered_matches = matches_df[matches_df["competition"].isin(competition_filter)].sort_values("date", ascending=False)
    selected_match_id = st.selectbox(
        "Match",
        options=filtered_matches["match_id"],
        format_func=lambda match_id: format_match_label(
            filtered_matches.loc[filtered_matches["match_id"] == match_id].iloc[0]
        ),
    )
    view_mode = st.radio(
        "View",
        options=["Team Performance", "Player Performance"],
        horizontal=True,
    )
    st.caption("The dashboard uses a small embedded match sample so it stays fast and portable.")

selected_match = matches_df.loc[matches_df["match_id"] == selected_match_id].iloc[0]
selected_players = player_df[player_df["match_id"] == selected_match_id].copy()
selected_shots = shot_df[shot_df["match_id"] == selected_match_id].copy()
selected_passes = pass_df[pass_df["match_id"] == selected_match_id].copy()
selected_players = selected_players.sort_values(["xg", "key_passes"], ascending=False)

top_row = st.columns(6)
top_row[0].metric("Match Date", selected_match["date"].strftime("%d %b %Y"))
top_row[1].metric("Competition", selected_match["competition"])
top_row[2].metric("Opponent", selected_match["opponent"])
top_row[3].metric("Score", selected_match["score"])
top_row[4].metric("Arsenal xG", f"{selected_match['xg_for']:.2f}")
top_row[5].metric("xG Against", f"{selected_match['xg_against']:.2f}")

summary_col, trends_col = st.columns([1.05, 1.35])

with summary_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Match Summary")
    inner_metrics = st.columns(4)
    inner_metrics[0].metric("Shots", int(selected_match["shots"]))
    inner_metrics[1].metric("On Target", int(selected_match["shots_on_target"]))
    inner_metrics[2].metric("Possession", f"{int(selected_match['possession'])}%")
    inner_metrics[3].metric("Pass Accuracy", f"{int(selected_match['pass_accuracy'])}%")
    detail_metrics = st.columns(2)
    detail_metrics[0].metric("PPDA", f"{selected_match['ppda']:.1f}")
    detail_metrics[1].metric("Field Tilt", f"{int(selected_match['field_tilt'])}%")

    summary_text = (
        f"Arsenal generated {selected_match['xg_for']:.2f} xG against {selected_match['opponent']} "
        f"in the {selected_match['competition']}. The shot profile shows a strong bias toward the "
        "right channel and central cutback zones, while possession remained controlled through Rice "
        "and Odegaard's progression."
    )
    st.write(summary_text)
    st.markdown("</div>", unsafe_allow_html=True)

with trends_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Competition Trend")
    trend_source = filtered_matches.sort_values("date")
    trend_fig = go.Figure()
    trend_fig.add_trace(
        go.Scatter(
            x=trend_source["date"],
            y=trend_source["xg_for"],
            mode="lines+markers",
            name="Arsenal xG",
            line=dict(color=ARSENAL_GOLD, width=3),
            marker=dict(size=9),
        )
    )
    trend_fig.add_trace(
        go.Scatter(
            x=trend_source["date"],
            y=trend_source["xg_against"],
            mode="lines+markers",
            name="xG Against",
            line=dict(color=ARSENAL_RED, width=3),
            marker=dict(size=9),
        )
    )
    trend_fig = base_figure_layout(trend_fig, height=290)
    trend_fig.update_xaxes(showgrid=False)
    trend_fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)", zeroline=False)
    st.plotly_chart(trend_fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

left_col, right_col = st.columns([1.08, 0.92])

with left_col:
    if view_mode == "Team Performance":
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Team Performance")
        team_cards = pd.DataFrame(
            {
                "Metric": ["Shots", "Shots On Target", "Possession", "Pass Accuracy", "Field Tilt", "PPDA"],
                "Value": [
                    selected_match["shots"],
                    selected_match["shots_on_target"],
                    f"{selected_match['possession']}%",
                    f"{selected_match['pass_accuracy']}%",
                    f"{selected_match['field_tilt']}%",
                    selected_match["ppda"],
                ],
            }
        )
        st.dataframe(team_cards, use_container_width=True, hide_index=True)

        comp_split = (
            matches_df[matches_df["competition"].isin(competition_filter)]
            .groupby("competition", as_index=False)[["xg_for", "xg_against", "shots"]]
            .mean()
        )
        comp_fig = px.bar(
            comp_split,
            x="competition",
            y=["xg_for", "xg_against"],
            barmode="group",
            color_discrete_sequence=[ARSENAL_GOLD, ARSENAL_RED],
        )
        comp_fig = base_figure_layout(comp_fig, height=320)
        comp_fig.update_xaxes(title=None)
        comp_fig.update_yaxes(title="Average xG", gridcolor="rgba(148,163,184,0.16)")
        st.plotly_chart(comp_fig, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("Player Performance")
        player_focus = st.selectbox("Focus Player", options=selected_players["player"].tolist())
        focus_row = selected_players.loc[selected_players["player"] == player_focus].iloc[0]
        player_metrics = st.columns(5)
        player_metrics[0].metric("xG", f"{focus_row['xg']:.2f}")
        player_metrics[1].metric("Shots", int(focus_row["shots"]))
        player_metrics[2].metric("Key Passes", int(focus_row["key_passes"]))
        player_metrics[3].metric("Recoveries", int(focus_row["recoveries"]))
        player_metrics[4].metric("Prog. Passes", int(focus_row["progressive_passes"]))

        player_chart = px.bar(
            selected_players,
            x="player",
            y=["xg", "key_passes", "recoveries"],
            barmode="group",
            color_discrete_sequence=[ARSENAL_GOLD, "#F8FAFC", "#38BDF8"],
        )
        player_chart = base_figure_layout(player_chart, height=340)
        player_chart.update_xaxes(title=None)
        player_chart.update_yaxes(title=None, gridcolor="rgba(148,163,184,0.16)")
        st.plotly_chart(player_chart, use_container_width=True)
        st.dataframe(
            selected_players.rename(
                columns={
                    "player": "Player",
                    "xg": "xG",
                    "shots": "Shots",
                    "key_passes": "Key Passes",
                    "recoveries": "Recoveries",
                    "completed_passes": "Completed Passes",
                    "progressive_passes": "Progressive Passes",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Shot Map")
    st.caption("Marker size scales with xG. Goals, saves, blocks, and misses are color-coded on a full pitch.")
    st.plotly_chart(create_shot_map(selected_shots), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

map_col, side_col = st.columns([1.08, 0.92])

with map_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Pass Map")
    st.caption("Arrows show Arsenal progression patterns from buildup into the final third.")
    st.plotly_chart(create_pass_map(selected_passes), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Injury Report")
    st.dataframe(injuries_df, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Arsenal News Feed")
    for item in fetch_arsenal_news():
        if item["link"]:
            st.markdown(
                f'<div class="news-link">• <a href="{item["link"]}">{item["title"]}</a></div>',
                unsafe_allow_html=True,
            )
        else:
            st.write(f"• {item['title']}")
        st.caption(item["published"])
    st.markdown(
        '<div class="small-note">Live headlines are requested from Google News RSS. If the request fails, the dashboard shows an offline fallback.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
