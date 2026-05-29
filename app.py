from __future__ import annotations

from datetime import datetime, timezone
from itertools import combinations
import json
import re
import xml.etree.ElementTree as ET

import feedparser
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(page_title="Arsenal Command Center", layout="wide")

TEAM_ID = 9825
TEAM_NAME = "Arsenal"
ARSENAL_RED = "#D90429"
ARSENAL_GOLD = "#F5C451"
PANEL_BG = "#101826"
PITCH_BG = "#0C4A3A"
APP_BG = "#06111D"
TEXT_MAIN = "#F8FAFC"
TEXT_MUTED = "#9FB0C4"
BORDER = "rgba(159, 176, 196, 0.16)"
FOTMOB_HEADERS = {"user-agent": "Mozilla/5.0"}


st.markdown(
    f"""
    <style>
    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(217, 4, 41, 0.18), transparent 28%),
            radial-gradient(circle at top right, rgba(245, 196, 81, 0.14), transparent 22%),
            linear-gradient(180deg, {APP_BG} 0%, #040b13 100%);
        color: {TEXT_MAIN};
    }}
    .block-container {{
        max-width: 1450px;
        padding-top: 1.2rem;
        padding-bottom: 2rem;
    }}
    div[data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(16, 24, 38, 0.96), rgba(9, 15, 26, 0.95));
        border: 1px solid {BORDER};
        border-radius: 18px;
        padding: 14px 16px;
        box-shadow: 0 16px 40px rgba(0, 0, 0, 0.18);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {TEXT_MUTED};
    }}
    div[data-testid="stMetricValue"] {{
        color: {TEXT_MAIN};
    }}
    .hero {{
        padding: 24px 28px;
        border-radius: 24px;
        border: 1px solid rgba(245, 196, 81, 0.18);
        background:
            linear-gradient(135deg, rgba(217, 4, 41, 0.22), rgba(10, 17, 29, 0.92) 44%),
            linear-gradient(180deg, rgba(16, 24, 38, 0.94), rgba(10, 17, 29, 0.96));
        margin-bottom: 18px;
        box-shadow: 0 22px 50px rgba(0, 0, 0, 0.2);
    }}
    .hero-kicker {{
        color: {ARSENAL_GOLD};
        font-size: 0.82rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }}
    .hero-title {{
        margin-top: 0.3rem;
        margin-bottom: 0.45rem;
        font-size: 2.3rem;
        font-weight: 850;
    }}
    .hero-subtitle {{
        color: {TEXT_MUTED};
        font-size: 0.98rem;
        max-width: 60rem;
    }}
    .panel {{
        background: linear-gradient(180deg, rgba(16, 24, 38, 0.96), rgba(9, 15, 26, 0.95));
        border: 1px solid {BORDER};
        border-radius: 22px;
        padding: 18px 20px;
        margin-bottom: 16px;
        box-shadow: 0 18px 45px rgba(0, 0, 0, 0.18);
    }}
    .small-note {{
        color: {TEXT_MUTED};
        font-size: 0.88rem;
    }}
    .insight-card {{
        min-height: 116px;
        border: 1px solid rgba(245, 196, 81, 0.16);
        border-radius: 18px;
        padding: 14px 16px;
        background: rgba(6, 17, 29, 0.58);
        overflow-wrap: anywhere;
        white-space: normal;
    }}
    .insight-card-label {{
        color: {ARSENAL_GOLD};
        font-size: 0.76rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 8px;
    }}
    .insight-card-value {{
        color: {TEXT_MAIN};
        font-size: 0.96rem;
        line-height: 1.42;
    }}
    .benefit-note {{
        margin-top: -0.25rem;
        margin-bottom: 0.85rem;
        padding: 10px 12px;
        border-left: 3px solid rgba(245, 196, 81, 0.62);
        border-radius: 12px;
        background: rgba(245, 196, 81, 0.07);
        color: {TEXT_MUTED};
        font-size: 0.9rem;
        line-height: 1.46;
    }}
    .news-item a {{
        color: {TEXT_MAIN};
        text-decoration: none;
    }}
    .news-item a:hover {{
        color: {ARSENAL_GOLD};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


SECTION_BENEFITS = {
    "Current Mode": "この画面がチーム全体の構造を見る状態か、選手個人の深掘りを見る状態かを確認できます。迷った時の現在地です。",
    "Player Matchboard": "選手単位でその試合にどれだけ関与したかを見ます。誰を深掘りすべきか、交代や起用判断の入口になります。",
    "Match Center": "試合の基本文脈です。相手、会場、結果、次戦を押さえることで、以降の分析を正しい前提で読めます。",
    "Recent Results": "短期的な調子を見ます。単発の勝敗ではなく、得点・失点の流れからチーム状態の変化を把握できます。",
    "Key Match Signals": "試合を動かした主要指標の要約です。細かい図に入る前に、どこが勝因・敗因候補かを掴めます。",
    "What This Match Says": "この試合を一言でどう評価するかを整理します。監督目線の結論、原因、不足点をすぐ確認できます。",
    "Key Player Verdict": "数字上だけでなく、構造上も重要だった選手を特定します。誰が試合を前に進めたかを見る入口です。",
    "Match Control Room": "試合を直感的に読むための司令室です。脅威ゾーン、攻撃の波、保持構造、プレッシングを横断して結果の理由を見ます。",
    "Threat Zones": "どのエリアが得点期待値や前進の源泉になったかをピッチ上で見ます。攻撃の強みと詰まりやすい場所がわかります。",
    "Attacking Waves": "短い時間に生まれた連続攻撃を見ます。単発のシュートではなく、試合を傾けた圧力の時間帯がわかります。",
    "Build-up Shape": "保持時の配置とレーン占有を見ます。どこに人数を置き、誰が前進の出口になったかがわかります。",
    "Pressing Lens": "ボール非保持でどれだけ相手を制限できたかを見ます。ハイプレス、中央封鎖、奪回後の安全性がわかります。",
    "Coach Takeaways": "次に残すべき良さと修正点を分けます。分析を感想で終わらせず、次のトレーニングや起用判断に変換できます。",
    "Next Match Prep": "選択した試合の次戦に向けて、何を継続し何を変えるべきかを整理します。",
    "Structural Diagnosis": "なぜその結果になったかを構造要因に分解します。攻撃、守備、陣地、選手関係性のどこが効いたかが見えます。",
    "Why Structurally": "構造診断の読み解きです。スコアだけでなく、その指標がなぜ重要なのかを文章で確認できます。",
    "Attack Review": "チャンス創出の質を見ます。シュート数だけでなく、中央攻略や前進から崩せていたかがわかります。",
    "Opponent Possession Review": "相手が保持した時にどこで危険だったかを見ます。守備の弱点や次戦で塞ぐべき場所がわかります。",
    "Half-by-Half Adjustments": "前半と後半で何が変わったかを見ます。ハーフタイム修正や交代後の効果を掴めます。",
    "Role Evaluation": "選手を役割で評価します。ゴール・アシスト以外に、前進役、接続役、奪回役などの貢献が見えます。",
    "Phase Control": "時間帯ごとの優位を見ます。どの30分で試合を支配し、どこで失速したかがわかります。",
    "Zone Profile": "どのエリアからシュートや侵入が生まれたかを見ます。中央、ハーフスペース、ボックス内の攻略度を確認できます。",
    "Arsenal Edge": "Arsenal側の明確な優位を抽出します。勝因として語れる材料を素早く拾えます。",
    "Opponent Threat": "相手側の危険要素を抽出します。勝っていても見逃したくない敗因候補や修正点がわかります。",
    "Team Analytics": "チーム単位の成績と試合一覧です。どの試合を比較・深掘りするかを選ぶための地図になります。",
    "Player Analytics": "選手単位の成績と傾向です。好調な選手、不調な選手、役割が変化している選手を見つけられます。",
    "Top Arsenal Performers": "シーズン全体で目立つ選手を確認します。直近試合だけに引っ張られず、継続的な貢献を見られます。",
    "Chance Quality Profile": "シュートの質を見ます。単なる本数ではなく、どれだけ得点に近い形を作れたかがわかります。",
    "Territory & Access": "どれだけ相手陣に入れていたかを見ます。押し込めたのか、最後の侵入で止まったのかを判別できます。",
    "xG Race": "試合中の期待値の流れを見ます。どの時間帯で優位が生まれ、どこで相手に流れを渡したかがわかります。",
    "Defensive Review": "相手に許したチャンスの質を見ます。守備が安定していたのか、結果に救われたのかを判断できます。",
    "Score State Analysis": "同点時、リード時、ビハインド時で試合内容がどう変わったかを見ます。試合運びの成熟度がわかります。",
    "Event Timeline": "得点、カード、交代などの出来事を時系列で確認します。試合の転換点を素早く特定できます。",
    "Match Shot Map": "実際のシュート位置とxGをピッチ上で見ます。どこから危険なシュートを打てたか、または打たれたかがわかります。",
    "Pass Network": "選手間のつながりと前進経路を見ます。ビルドアップの中心、詰まったレーン、依存している関係性がわかります。",
    "Player Relationships": "パスネットワークのハブと強い関係性を見ます。誰と誰の接続が攻撃の再現性を支えたかがわかります。",
    "Injury Tracker": "起用可能性を確認します。戦術評価と次戦準備を現実的なメンバー状況に結びつけられます。",
    "Arsenal News": "チーム外部の最新文脈を拾います。負傷、移籍、監督コメントなど分析の前提が変わる情報に気づけます。",
    "Analyst Snapshot": "試合全体の要約です。細部を見る前後に、結論を短く掴み直せます。",
    "Cannon-Style Analysis Template": "分析の型です。毎試合同じ観点で見ることで、感覚ではなく比較可能なレビューにできます。",
    "Full Match Report": "試合分析を文章としてまとめます。後で読み返す、共有する、投稿用素材にするための出口です。",
    "Season Player Performance Lab": "シーズン全体で選手が良いパフォーマンスを出しているかを多角的に見ます。G/Aだけで見落とす貢献も拾えます。",
    "Player Deep Dive": "特定選手のその試合の関与を深掘りします。ヒートマップ、シュート、パス、回収から役割の実態が見えます。",
    "Arsenal Analyst Chat": "疑問をその場で深掘りするための対話欄です。勝因、敗因、構造、次戦への示唆を質問形式で掘れます。",
}


def render_section_benefit(title: str, fallback: str | None = None) -> None:
    text = SECTION_BENEFITS.get(title, fallback)
    if not text:
        return
    st.markdown(f'<div class="benefit-note">{text}</div>', unsafe_allow_html=True)


def inject_auto_refresh(interval_seconds: int) -> None:
    if interval_seconds <= 0:
        return
    components.html(
        f"""
        <script>
        setTimeout(function() {{
            window.parent.location.reload();
        }}, {interval_seconds * 1000});
        </script>
        """,
        height=0,
    )


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def safe_get(url: str) -> requests.Response:
    response = requests.get(url, timeout=20, headers=FOTMOB_HEADERS)
    response.raise_for_status()
    return response


def parse_next_data(html: str) -> dict | None:
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def fetch_team_payload() -> dict:
    try:
        response = safe_get(f"https://www.fotmob.com/api/teams?id={TEAM_ID}")
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
    except Exception:
        pass

    try:
        html = safe_get(f"https://www.fotmob.com/teams/{TEAM_ID}/overview/arsenal").text
        next_data = parse_next_data(html)
        team_payload = next_data.get("props", {}).get("pageProps", {}).get("fallback", {}).get(f"team-{TEAM_ID}")
        if team_payload:
            return team_payload
    except Exception:
        pass

    return {
        "overview": {
            "lastMatch": None,
            "nextMatch": None,
            "overviewFixtures": [],
            "topPlayers": {},
            "newsSummary": {"items": []},
            "lastLineupStats": {
                "starters": [],
                "subs": [],
                "unavailable": [],
                "formation": "",
                "rating": None,
                "coach": {"name": "Unavailable"},
            },
        },
        "fixtures": {"allFixtures": {"fixtures": []}},
        "squad": {"squad": []},
    }


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_google_news() -> list[dict[str, str]]:
    rss_url = "https://news.google.com/rss/search?q=Arsenal+FC&hl=en-GB&gl=GB&ceid=GB:en"
    try:
        response = safe_get(rss_url)
        feed = feedparser.parse(response.content)
        items: list[dict[str, str]] = []
        for entry in feed.entries[:8]:
            published = entry.get("published", "Latest")
            items.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "source": entry.get("source", {}).get("title", "Google News"),
                    "published": published,
                }
            )
        return items
    except Exception:
        return []


def normalize_competition(name: str | None) -> str:
    if not name:
        return "Other"
    return "Champions League" if "Champions League" in name else name


def get_competition_options(matches_df: pd.DataFrame) -> list[str]:
    if matches_df.empty:
        return []
    competitions = matches_df["competition"].dropna().tolist()
    return list(dict.fromkeys(competitions))


@st.cache_data(ttl=900, show_spinner=False)
def fetch_match_page_props(page_url: str) -> dict:
    if not page_url:
        return {}
    try:
        html = safe_get(f"https://www.fotmob.com{page_url}").text
        next_data = parse_next_data(html)
        if not next_data:
            return {}
        return next_data.get("props", {}).get("pageProps", {})
    except Exception:
        return {}


@st.cache_data(ttl=900, show_spinner=False)
def fetch_match_heatmap_payload(page_url: str) -> dict:
    page_props = fetch_match_page_props(page_url)
    heatmap_path = page_props.get("content", {}).get("heatmapUrl")
    if not heatmap_path:
        return {}
    try:
        response = safe_get(f"https://www.fotmob.com{heatmap_path}")
        if "application/json" in response.headers.get("content-type", ""):
            return response.json()
    except Exception:
        return {}
    return {}


def get_team_side(page_props: dict, team_id: int) -> int:
    lineup = page_props.get("content", {}).get("lineup", {})
    if lineup.get("homeTeam", {}).get("id") == team_id:
        return 0
    return 1


def build_matches_df(payload: dict) -> pd.DataFrame:
    columns = [
        "match_id",
        "date",
        "competition",
        "stage",
        "opponent",
        "venue",
        "score",
        "arsenal_goals",
        "opponent_goals",
        "status",
        "result",
        "finished",
        "started",
        "page_url",
    ]
    fixtures = payload.get("fixtures", {}).get("allFixtures", {}).get("fixtures", [])
    rows = []
    for item in fixtures:
        tournament_name = normalize_competition(item.get("tournament", {}).get("name"))
        match_dt = parse_dt(item.get("status", {}).get("utcTime"))
        home = item.get("home", {})
        away = item.get("away", {})
        arsenal_is_home = home.get("id") == TEAM_ID
        arsenal_score = home.get("score") if arsenal_is_home else away.get("score")
        opponent_score = away.get("score") if arsenal_is_home else home.get("score")
        score = (
            f"{arsenal_score} - {opponent_score}"
            if arsenal_score is not None and opponent_score is not None
            else "Scheduled"
        )
        result_code = item.get("result")
        result_label = "Draw"
        if result_code == 1:
            result_label = "Win"
        elif result_code == -1:
            result_label = "Loss"
        elif result_code is None:
            result_label = "Upcoming"
        rows.append(
            {
                "match_id": item.get("id"),
                "date": match_dt,
                "competition": tournament_name,
                "stage": item.get("tournament", {}).get("stage", ""),
                "opponent": item.get("opponent", {}).get("name", "Unknown"),
                "venue": "Home" if arsenal_is_home else "Away",
                "score": score,
                "arsenal_goals": arsenal_score,
                "opponent_goals": opponent_score,
                "status": item.get("status", {}).get("reason", {}).get("short", "NS"),
                "result": result_label,
                "finished": item.get("status", {}).get("finished", False),
                "started": item.get("status", {}).get("started", False),
                "page_url": item.get("pageUrl", ""),
            }
        )
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return df
    return df.sort_values("date", ascending=False).reset_index(drop=True)


def get_selected_next_match(matches_df: pd.DataFrame, selected_match: pd.Series) -> dict | None:
    if matches_df.empty or pd.isna(selected_match.get("date")):
        return None
    future = matches_df[matches_df["date"] > selected_match["date"]].sort_values("date", ascending=True)
    if future.empty:
        return None
    next_row = future.iloc[0]
    return {
        "opponent": {"name": next_row["opponent"]},
        "tournament": {"name": next_row["competition"]},
        "status": {"utcTime": next_row["date"].isoformat() if pd.notna(next_row["date"]) else None},
        "venue": next_row["venue"],
        "match_id": next_row["match_id"],
    }


def player_rows_from_lineup(lineup: dict) -> list[dict]:
    rows: list[dict] = []
    for section, status in [("starters", "Available"), ("subs", "Available")]:
        for player in lineup.get(section, []):
            performance = player.get("performance", {})
            rows.append(
                {
                    "player": player.get("name"),
                    "status": status,
                    "role": section[:-1].title(),
                    "shirt": player.get("shirtNumber", ""),
                    "position_id": player.get("usualPlayingPositionId"),
                    "country": player.get("countryCode", ""),
                    "rating_last_match": performance.get("rating"),
                    "season_goals": performance.get("seasonGoals", 0),
                    "season_assists": performance.get("seasonAssists", 0),
                    "season_rating": performance.get("seasonRating"),
                    "market_value": player.get("marketValue"),
                    "x": player.get("horizontalLayout", {}).get("x"),
                    "y": player.get("horizontalLayout", {}).get("y"),
                    "events": performance.get("events", []),
                }
            )
    for player in lineup.get("unavailable", []):
        unavailability = player.get("unavailability", {})
        rows.append(
            {
                "player": player.get("name"),
                "status": unavailability.get("type", "Unavailable").title(),
                "role": "Unavailable",
                "shirt": "",
                "position_id": player.get("positionId"),
                "country": player.get("countryCode", ""),
                "rating_last_match": None,
                "season_goals": None,
                "season_assists": None,
                "season_rating": None,
                "market_value": player.get("marketValue"),
                "x": None,
                "y": None,
                "events": [],
                "expected_return": unavailability.get("expectedReturn", "TBD"),
            }
        )
    return rows


def build_player_df(payload: dict) -> pd.DataFrame:
    lineup = payload.get("overview", {}).get("lastLineupStats", {})
    df = pd.DataFrame(player_rows_from_lineup(lineup))
    if df.empty:
        return df
    return df.sort_values(
        ["status", "season_rating", "season_goals"],
        ascending=[True, False, False],
        na_position="last",
    ).reset_index(drop=True)


def extract_stat_value(player_stats: dict, label: str) -> float | int | None:
    for stat_group in player_stats.get("stats", []):
        stats = stat_group.get("stats", {})
        for title, entry in stats.items():
            if title != label:
                continue
            stat = entry.get("stat", {})
            return stat.get("value")
    return None


def numeric_or_default(value: object, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_match_player_df(page_props: dict, team_id: int) -> pd.DataFrame:
    content = page_props.get("content", {})
    lineup = content.get("lineup", {})
    player_stats = content.get("playerStats", {})
    team_block = lineup.get("homeTeam", {}) if lineup.get("homeTeam", {}).get("id") == team_id else lineup.get("awayTeam", {})
    rows: list[dict] = []
    for section, role in [("starters", "Starter"), ("subs", "Sub")]:
        for player in team_block.get(section, []):
            stats = player_stats.get(str(player.get("id")), {})
            performance = player.get("performance", {})
            rows.append(
                {
                    "player": player.get("name"),
                    "role": role,
                    "status": "Available",
                    "shirt": player.get("shirtNumber", ""),
                    "position_id": player.get("usualPlayingPositionId"),
                    "rating_last_match": performance.get("rating"),
                    "season_rating": performance.get("seasonRating"),
                    "season_goals": performance.get("seasonGoals"),
                    "season_assists": performance.get("seasonAssists"),
                    "market_value": player.get("marketValue"),
                    "x": player.get("horizontalLayout", {}).get("x"),
                    "y": player.get("horizontalLayout", {}).get("y"),
                    "accurate_passes": extract_stat_value(stats, "Accurate passes"),
                    "passes_into_final_third": extract_stat_value(stats, "Passes into final third"),
                    "touches": extract_stat_value(stats, "Touches"),
                    "recoveries": extract_stat_value(stats, "Recoveries"),
                    "distance_covered": extract_stat_value(stats, "Distance covered"),
                }
            )
    for player in team_block.get("unavailable", []):
        unavailability = player.get("unavailability", {})
        rows.append(
            {
                "player": player.get("name"),
                "role": "Unavailable",
                "status": unavailability.get("type", "Unavailable").title(),
                "shirt": "",
                "position_id": player.get("positionId"),
                "rating_last_match": None,
                "season_rating": None,
                "season_goals": None,
                "season_assists": None,
                "market_value": player.get("marketValue"),
                "x": None,
                "y": None,
                "accurate_passes": None,
                "passes_into_final_third": None,
                "touches": None,
                "recoveries": None,
                "distance_covered": None,
                "expected_return": unavailability.get("expectedReturn", "TBD"),
            }
        )
    return pd.DataFrame(rows)


def build_match_shot_df(page_props: dict, team_id: int | None = None) -> pd.DataFrame:
    shots = page_props.get("content", {}).get("shotmap", {}).get("shots", [])
    rows = []
    for shot in shots:
        if team_id is not None and shot.get("teamId") != team_id:
            continue
        rows.append(
            {
                "team_id": shot.get("teamId"),
                "player": shot.get("fullName") or shot.get("playerName"),
                "event_type": shot.get("eventType"),
                "minute": shot.get("min"),
                "xg": shot.get("expectedGoals"),
                "xgot": shot.get("expectedGoalsOnTarget"),
                "shot_type": shot.get("shotType"),
                "situation": shot.get("situation"),
                "inside_box": shot.get("isFromInsideBox"),
                "on_target": shot.get("isOnTarget"),
                "blocked": shot.get("isBlocked"),
                "x": numeric_or_default(shot.get("x")) * (120 / 105),
                "y": numeric_or_default(shot.get("y")) * (80 / 68),
            }
        )
    return pd.DataFrame(rows)


def build_event_df(page_props: dict, team_id: int) -> pd.DataFrame:
    events_block = page_props.get("content", {}).get("matchFacts", {}).get("events", {})
    events = events_block.get("events", []) if isinstance(events_block, dict) else []
    rows = []
    for event in events:
        player = event.get("fullName") or event.get("nameStr") or event.get("player", {}).get("name")
        assist = event.get("assistStr")
        shotmap_event = event.get("shotmapEvent", {})
        rows.append(
            {
                "minute": event.get("time"),
                "event_type": event.get("type"),
                "team": "Arsenal" if event.get("isHome") == (get_team_side(page_props, team_id) == 0) else "Opponent",
                "player": player,
                "assist": assist,
                "card": event.get("card"),
                "score": "-".join(str(x) for x in event.get("newScore", [])) if event.get("newScore") else "",
                "xg": numeric_or_default(shotmap_event.get("expectedGoals")),
                "situation": shotmap_event.get("situation"),
                "is_sub": event.get("type") == "Substitution",
                "text": (
                    event.get("goalDescription")
                    or event.get("minutesAddedStr")
                    or event.get("halfStrShort")
                    or event.get("cardDescription")
                    or event.get("nameStr")
                ),
            }
        )
    event_df = pd.DataFrame(rows)
    if event_df.empty:
        return pd.DataFrame(columns=["minute", "event_type", "team", "player", "assist", "card", "score", "xg", "situation", "is_sub", "text"])
    return event_df.sort_values("minute").reset_index(drop=True)


def build_period_stats_df(page_props: dict, team_id: int) -> pd.DataFrame:
    periods = page_props.get("content", {}).get("stats", {}).get("Periods", {})
    side = get_team_side(page_props, team_id)
    opp_side = 1 - side
    keys_to_keep = {
        "Ball possession",
        "Expected goals (xG)",
        "Total shots",
        "Shots on target",
        "Big chances",
        "Accurate passes",
        "Corners",
        "Shots inside box",
        "xG open play",
        "xG set play",
    }
    rows = []
    for period_name in ["All", "FirstHalf", "SecondHalf"]:
        period = periods.get(period_name, {})
        for group in period.get("stats", []):
            for stat in group.get("stats", []):
                title = stat.get("title")
                if title not in keys_to_keep:
                    continue
                values = stat.get("stats", [None, None])
                if len(values) < 2:
                    continue
                rows.append(
                    {
                        "Period": period_name,
                        "Metric": title,
                        "Arsenal": values[side],
                        "Opponent": values[opp_side],
                    }
                )
    return pd.DataFrame(rows)


def build_substitution_impact_df(event_df: pd.DataFrame, all_shot_df: pd.DataFrame, team_id: int) -> pd.DataFrame:
    if event_df.empty or all_shot_df.empty:
        return pd.DataFrame(columns=["Minute", "Player", "Team", "Before xG", "After xG", "Delta"])
    subs = event_df[event_df["event_type"] == "Substitution"].copy()
    if subs.empty:
        return pd.DataFrame(columns=["Minute", "Player", "Team", "Before xG", "After xG", "Delta"])
    shots = all_shot_df.copy()
    shots["minute_num"] = shots["minute"].apply(lambda value: int(numeric_or_default(value)))
    shots["xg_num"] = shots["xg"].apply(numeric_or_default)
    shots["team_label"] = shots["team_id"].apply(lambda value: "Arsenal" if value == team_id else "Opponent")
    rows = []
    for _, sub in subs.iterrows():
        minute = int(numeric_or_default(sub["minute"]))
        team_label = sub["team"]
        before = shots[(shots["team_label"] == team_label) & (shots["minute_num"] < minute)]["xg_num"].sum()
        after = shots[(shots["team_label"] == team_label) & (shots["minute_num"] >= minute)]["xg_num"].sum()
        rows.append(
            {
                "Minute": f"{minute}'",
                "Player": sub["player"] or "Substitution",
                "Team": team_label,
                "Before xG": round(float(before), 2),
                "After xG": round(float(after), 2),
                "Delta": round(float(after - before), 2),
            }
        )
    return pd.DataFrame(rows)


def create_event_timeline_chart(event_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if event_df.empty:
        return base_chart_layout(fig, height=280)
    plot_df = event_df[event_df["event_type"].isin(["Goal", "Card", "Substitution"])].copy()
    if plot_df.empty:
        return base_chart_layout(fig, height=280)
    y_map = {"Goal": 3, "Card": 2, "Substitution": 1}
    color_map = {"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"}
    plot_df["y"] = plot_df["event_type"].map(y_map).fillna(0)
    fig.add_trace(
        go.Scatter(
            x=plot_df["minute"],
            y=plot_df["y"],
            mode="markers+text",
            text=plot_df["player"].fillna(plot_df["event_type"]),
            textposition="top center",
            marker=dict(
                size=14,
                color=plot_df["team"].map(color_map),
                line=dict(color="white", width=1),
            ),
            customdata=plot_df[["event_type", "team", "score"]],
            hovertemplate="<b>%{text}</b><br>%{customdata[0]}<br>%{customdata[1]}<br>%{customdata[2]}<extra></extra>",
            showlegend=False,
        )
    )
    fig = base_chart_layout(fig, height=280)
    fig.update_xaxes(title="Minute", dtick=15, showgrid=False)
    fig.update_yaxes(
        title=None,
        tickmode="array",
        tickvals=[1, 2, 3],
        ticktext=["Sub", "Card", "Goal"],
        gridcolor="rgba(159,176,196,0.14)",
    )
    return fig


def build_xg_race_df(shot_df: pd.DataFrame, arsenal_team_id: int) -> pd.DataFrame:
    if shot_df.empty:
        return pd.DataFrame(columns=["minute", "team", "xg", "cum_xg"])
    race = shot_df.copy()
    race["minute_num"] = race["minute"].apply(lambda value: int(numeric_or_default(value)))
    race["xg_num"] = race["xg"].apply(numeric_or_default)
    race["team"] = race["team_id"].apply(lambda value: "Arsenal" if value == arsenal_team_id else "Opponent")
    race = race.sort_values(["minute_num", "xg_num"]).reset_index(drop=True)
    frames = []
    for team_name in ["Arsenal", "Opponent"]:
        team_df = race[race["team"] == team_name][["minute_num", "xg_num"]].copy()
        if team_df.empty:
            continue
        team_df["cum_xg"] = team_df["xg_num"].cumsum()
        team_df["team"] = team_name
        frames.append(team_df.rename(columns={"minute_num": "minute", "xg_num": "xg"}))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["minute", "team", "xg", "cum_xg"])


def create_xg_race_chart(race_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if race_df.empty:
        return base_chart_layout(fig, height=320)
    color_map = {"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"}
    for team_name in ["Arsenal", "Opponent"]:
        team_df = race_df[race_df["team"] == team_name]
        if team_df.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=team_df["minute"],
                y=team_df["cum_xg"],
                mode="lines+markers",
                name=team_name,
                line=dict(color=color_map[team_name], width=3, shape="hv"),
                marker=dict(size=7),
                customdata=team_df[["xg"]],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Minute: %{x}<br>"
                    "Shot xG: %{customdata[0]:.2f}<br>"
                    "Cumulative xG: %{y:.2f}<extra></extra>"
                ),
            )
        )
    fig = base_chart_layout(fig, height=320)
    fig.update_xaxes(title="Minute", dtick=15, showgrid=False)
    fig.update_yaxes(title="Cumulative xG", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_phase_split(shot_df: pd.DataFrame, team_label: str) -> pd.DataFrame:
    if shot_df.empty:
        return pd.DataFrame(columns=["Phase", "Team", "Shots", "xG"])
    phases = [
        ("0-30", 0, 30),
        ("31-60", 31, 60),
        ("61-90+", 61, 130),
    ]
    rows = []
    shot_df = shot_df.copy()
    shot_df["minute_num"] = shot_df["minute"].apply(lambda value: int(numeric_or_default(value)))
    shot_df["xg_num"] = shot_df["xg"].apply(numeric_or_default)
    for label, start, end in phases:
        phase_df = shot_df[shot_df["minute_num"].between(start, end)]
        rows.append(
            {
                "Phase": label,
                "Team": team_label,
                "Shots": int(len(phase_df)),
                "xG": float(phase_df["xg_num"].sum()),
            }
        )
    return pd.DataFrame(rows)


def create_phase_split_chart(arsenal_phase_df: pd.DataFrame, opponent_phase_df: pd.DataFrame) -> go.Figure:
    combined = pd.concat([arsenal_phase_df, opponent_phase_df], ignore_index=True)
    fig = px.bar(
        combined,
        x="Phase",
        y="xG",
        color="Team",
        barmode="group",
        color_discrete_map={"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"},
        text_auto=".2f",
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="xG by phase", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_zone_profile(shot_df: pd.DataFrame) -> dict[str, float]:
    if shot_df.empty:
        return {
            "zone14_entries": 0,
            "left_half_space_shots": 0,
            "right_half_space_shots": 0,
            "central_box_shots": 0,
        }
    zone14 = shot_df[(shot_df["x"].between(85, 100)) & (shot_df["y"].between(30, 50))]
    left_half = shot_df[(shot_df["x"].between(84, 110)) & (shot_df["y"].between(50, 68))]
    right_half = shot_df[(shot_df["x"].between(84, 110)) & (shot_df["y"].between(12, 30))]
    central_box = shot_df[(shot_df["x"] >= 102) & (shot_df["y"].between(24, 56))]
    return {
        "zone14_entries": int(len(zone14)),
        "left_half_space_shots": int(len(left_half)),
        "right_half_space_shots": int(len(right_half)),
        "central_box_shots": int(len(central_box)),
    }


def build_review_history(matches_df: pd.DataFrame) -> pd.DataFrame:
    completed = matches_df[matches_df["finished"]].copy().sort_values("date", ascending=False).head(8)
    if completed.empty:
        return pd.DataFrame(columns=["Date", "Competition", "Opponent", "Score", "Result"])
    return pd.DataFrame(
        {
            "Date": completed["date"].dt.strftime("%d %b %Y"),
            "Competition": completed["competition"],
            "Opponent": completed["opponent"],
            "Score": completed["score"],
            "Result": completed["result"],
        }
    )


def build_trend_summary(matches_df: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    completed = matches_df[matches_df["finished"]].copy().sort_values("date", ascending=False).head(limit)
    if completed.empty:
        return pd.DataFrame(columns=["Metric", "Value", "Direction"])
    goals_for = completed["arsenal_goals"].fillna(0).mean()
    goals_against = completed["opponent_goals"].fillna(0).mean()
    win_rate = (completed["result"] == "Win").mean() * 100
    goal_diff = (completed["arsenal_goals"].fillna(0) - completed["opponent_goals"].fillna(0)).mean()
    rows = [
        {"Metric": "Avg Goals For", "Value": round(goals_for, 2), "Direction": "Higher is better"},
        {"Metric": "Avg Goals Against", "Value": round(goals_against, 2), "Direction": "Lower is better"},
        {"Metric": "Win Rate %", "Value": round(win_rate, 1), "Direction": "Higher is better"},
        {"Metric": "Avg Goal Diff", "Value": round(goal_diff, 2), "Direction": "Higher is better"},
    ]
    return pd.DataFrame(rows)


def build_recent_results_benchmark(matches_df: pd.DataFrame, limit: int = 5) -> tuple[pd.DataFrame, list[str]]:
    columns = ["Metric", "Recent", "Season Avg", "Target", "Status", "Delta vs Avg"]
    completed = matches_df[matches_df["finished"]].copy().sort_values("date", ascending=False)
    if completed.empty:
        return pd.DataFrame(columns=columns), ["比較できる完了済み試合がありません。"]

    recent = completed.head(limit)
    all_completed = completed.copy()
    recent_gf = float(recent["arsenal_goals"].fillna(0).mean())
    recent_ga = float(recent["opponent_goals"].fillna(0).mean())
    recent_gd = recent_gf - recent_ga
    recent_win_rate = float((recent["result"] == "Win").mean() * 100)
    recent_clean_sheet = float((recent["opponent_goals"].fillna(0) == 0).mean() * 100)
    recent_unbeaten = float((recent["result"] != "Loss").mean() * 100)

    season_gf = float(all_completed["arsenal_goals"].fillna(0).mean())
    season_ga = float(all_completed["opponent_goals"].fillna(0).mean())
    season_gd = season_gf - season_ga
    season_win_rate = float((all_completed["result"] == "Win").mean() * 100)
    season_clean_sheet = float((all_completed["opponent_goals"].fillna(0) == 0).mean() * 100)
    season_unbeaten = float((all_completed["result"] != "Loss").mean() * 100)

    metric_specs = [
        ("Goals For / match", recent_gf, season_gf, 2.0, "higher"),
        ("Goals Against / match", recent_ga, season_ga, 1.0, "lower"),
        ("Goal Difference / match", recent_gd, season_gd, 1.0, "higher"),
        ("Win Rate", recent_win_rate, season_win_rate, 70.0, "higher"),
        ("Clean Sheet Rate", recent_clean_sheet, season_clean_sheet, 40.0, "higher"),
        ("Unbeaten Rate", recent_unbeaten, season_unbeaten, 80.0, "higher"),
    ]

    rows = []
    for metric, recent_value, season_value, target, direction in metric_specs:
        if direction == "higher":
            status = "Good" if recent_value >= target else ("Watch" if recent_value >= season_value else "Concern")
            delta = recent_value - season_value
        else:
            status = "Good" if recent_value <= target else ("Watch" if recent_value <= season_value else "Concern")
            delta = season_value - recent_value
        rows.append(
            {
                "Metric": metric,
                "Recent": round(recent_value, 2),
                "Season Avg": round(season_value, 2),
                "Target": round(target, 2),
                "Status": status,
                "Delta vs Avg": round(delta, 2),
            }
        )
    benchmark_df = pd.DataFrame(rows, columns=columns)
    good_count = int((benchmark_df["Status"] == "Good").sum())
    concern_count = int((benchmark_df["Status"] == "Concern").sum())
    notes = [
        f"直近{len(recent)}試合で Good が {good_count} 項目、Concern が {concern_count} 項目です。",
    ]
    if recent_gd > season_gd:
        notes.append(f"得失点差は直近 {recent_gd:+.2f}/match で、選択範囲平均 {season_gd:+.2f} より良化しています。")
    else:
        notes.append(f"得失点差は直近 {recent_gd:+.2f}/match で、選択範囲平均 {season_gd:+.2f} を下回っています。")
    if recent_ga <= 1.0:
        notes.append("失点ペースは良好で、守備面の結果は安定しています。")
    else:
        notes.append("失点ペースが高めで、試合内容が良くても結果が不安定になりやすい状態です。")
    return benchmark_df, notes


def create_recent_results_benchmark_chart(benchmark_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if benchmark_df.empty:
        return base_chart_layout(fig, height=320)
    plot_df = benchmark_df.copy()
    status_colors = {"Good": "#22C55E", "Watch": ARSENAL_GOLD, "Concern": ARSENAL_RED}
    fig.add_trace(
        go.Bar(
            y=plot_df["Metric"],
            x=plot_df["Season Avg"],
            name="Selected range avg",
            orientation="h",
            marker=dict(color="rgba(147,197,253,0.42)"),
            hovertemplate="<b>%{y}</b><br>Selected range avg: %{x:.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=plot_df["Metric"],
            x=plot_df["Recent"],
            name="Recent form",
            orientation="h",
            marker=dict(color=plot_df["Status"].map(status_colors)),
            customdata=plot_df[["Target", "Status", "Delta vs Avg"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Recent: %{x:.2f}<br>"
                "Target: %{customdata[0]:.2f}<br>"
                "Status: %{customdata[1]}<br>"
                "Delta vs avg: %{customdata[2]:+.2f}<extra></extra>"
            ),
        )
    )
    fig = base_chart_layout(fig, height=360)
    fig.update_layout(barmode="group", legend=dict(orientation="h", y=1.08, x=0))
    fig.update_xaxes(title="Value", gridcolor="rgba(159,176,196,0.14)")
    fig.update_yaxes(title=None, autorange="reversed")
    return fig


def build_top_players_df(payload: dict) -> pd.DataFrame:
    top_players = payload.get("overview", {}).get("topPlayers", {})
    rows = []
    for category, label in [("byRating", "Rating"), ("byGoals", "Goals"), ("byAssists", "Assists")]:
        players = top_players.get(category, {}).get("players", [])
        for player in players:
            rows.append(
                {
                    "Category": label,
                    "Player": player.get("name"),
                    "Value": player.get("value"),
                    "Rank": player.get("rank"),
                }
            )
    return pd.DataFrame(rows)


def build_season_player_performance_df(payload: dict, top_players_df: pd.DataFrame) -> pd.DataFrame:
    player_df = build_player_df(payload)
    columns = [
        "Player",
        "Role",
        "Status",
        "Season Rating",
        "Goals",
        "Assists",
        "Goal Contributions",
        "Last Match Rating",
        "Availability",
        "Recognition",
        "Performance Score",
        "Profile",
        "Verdict",
    ]
    if player_df.empty:
        return pd.DataFrame(columns=columns)

    available = player_df[player_df["role"] != "Unavailable"].copy()
    if available.empty:
        return pd.DataFrame(columns=columns)

    available["rating_num"] = available["season_rating"].apply(lambda value: numeric_or_default(value, 6.0))
    available["last_rating_num"] = available["rating_last_match"].apply(lambda value: numeric_or_default(value, 6.0))
    available["goals_num"] = available["season_goals"].apply(numeric_or_default)
    available["assists_num"] = available["season_assists"].apply(numeric_or_default)
    available["goal_contributions"] = available["goals_num"] + available["assists_num"]
    available["availability_score"] = available["status"].apply(lambda value: 100 if value == "Available" else 35)

    recognition_scores: dict[str, float] = {str(player): 0.0 for player in available["player"].tolist()}
    if not top_players_df.empty:
        for _, row in top_players_df.iterrows():
            player = str(row.get("Player", ""))
            rank = numeric_or_default(row.get("Rank"), 10)
            category = row.get("Category")
            base = max(0.0, 30.0 - rank * 4.0)
            multiplier = {"Rating": 1.25, "Goals": 1.0, "Assists": 1.0}.get(category, 0.8)
            recognition_scores[player] = recognition_scores.get(player, 0.0) + base * multiplier

    def percentile(series: pd.Series) -> pd.Series:
        if series.nunique(dropna=False) <= 1:
            return pd.Series([50.0] * len(series), index=series.index)
        return series.rank(pct=True).fillna(0.5) * 100

    available["rating_pct"] = percentile(available["rating_num"])
    available["last_rating_pct"] = percentile(available["last_rating_num"])
    available["gc_pct"] = percentile(available["goal_contributions"])
    available["recognition"] = available["player"].map(recognition_scores).fillna(0).clip(upper=100)
    available["score"] = (
        available["rating_pct"] * 0.38
        + available["gc_pct"] * 0.24
        + available["last_rating_pct"] * 0.16
        + available["recognition"] * 0.14
        + available["availability_score"] * 0.08
    ).round(1)

    def profile(row: pd.Series) -> str:
        if row["goals_num"] >= row["assists_num"] + 3:
            return "Finisher"
        if row["assists_num"] >= row["goals_num"] + 2:
            return "Creator"
        if row["rating_num"] >= 7.0 and row["goal_contributions"] <= 3:
            return "Control Piece"
        if row["recognition"] >= 30:
            return "High-visibility performer"
        return "Balanced contributor"

    def verdict(row: pd.Series) -> str:
        if row["score"] >= 78:
            return "Excellent season signal"
        if row["score"] >= 62:
            return "Positive contributor"
        if row["score"] >= 45:
            return "Useful but needs context"
        return "Limited signal so far"

    rows = pd.DataFrame(
        {
            "Player": available["player"],
            "Role": available["role"],
            "Status": available["status"],
            "Season Rating": available["rating_num"].round(2),
            "Goals": available["goals_num"].astype(int),
            "Assists": available["assists_num"].astype(int),
            "Goal Contributions": available["goal_contributions"].astype(int),
            "Last Match Rating": available["last_rating_num"].round(2),
            "Availability": available["availability_score"].astype(int),
            "Recognition": available["recognition"].round(1),
            "Performance Score": available["score"],
            "Profile": available.apply(profile, axis=1),
            "Verdict": available.apply(verdict, axis=1),
        }
    )
    return rows.sort_values(["Performance Score", "Season Rating", "Goal Contributions"], ascending=False).reset_index(drop=True)


def create_season_performance_chart(season_df: pd.DataFrame) -> go.Figure:
    plot_df = season_df.head(12).copy()
    fig = px.scatter(
        plot_df,
        x="Season Rating",
        y="Goal Contributions",
        size="Performance Score",
        color="Profile",
        hover_name="Player",
        hover_data={
            "Goals": True,
            "Assists": True,
            "Recognition": ":.1f",
            "Performance Score": ":.1f",
            "Profile": True,
        },
        color_discrete_sequence=[ARSENAL_RED, ARSENAL_GOLD, "#7DD3FC", "#8DD3C7", "#CBD5E1"],
    )
    fig = base_chart_layout(fig, height=360)
    fig.update_xaxes(title="Season rating", gridcolor="rgba(159,176,196,0.14)")
    fig.update_yaxes(title="Goals + assists", gridcolor="rgba(159,176,196,0.14)")
    return fig


def create_player_score_breakdown(season_df: pd.DataFrame, selected_player: str) -> go.Figure:
    row_df = season_df[season_df["Player"] == selected_player]
    metrics = pd.DataFrame(
        {
            "Metric": ["Season Rating", "Goal Contributions", "Last Match Rating", "Recognition", "Availability"],
            "Score": [0, 0, 0, 0, 0],
        }
    )
    if not row_df.empty:
        row = row_df.iloc[0]
        max_gc = max(float(season_df["Goal Contributions"].max()), 1.0)
        metrics["Score"] = [
            min(100, numeric_or_default(row["Season Rating"], 6.0) / 8.0 * 100),
            min(100, numeric_or_default(row["Goal Contributions"]) / max_gc * 100),
            min(100, numeric_or_default(row["Last Match Rating"], 6.0) / 8.0 * 100),
            numeric_or_default(row["Recognition"]),
            numeric_or_default(row["Availability"]),
        ]
    fig = px.bar(
        metrics,
        x="Metric",
        y="Score",
        color="Score",
        color_continuous_scale=[[0, "#93C5FD"], [0.55, "#FFE8A3"], [1, ARSENAL_RED]],
        text_auto=".0f",
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Score / 100", range=[0, 100], gridcolor="rgba(159,176,196,0.14)")
    fig.update_layout(coloraxis_showscale=False)
    return fig


def build_injury_df(payload: dict) -> pd.DataFrame:
    unavailable = payload.get("overview", {}).get("lastLineupStats", {}).get("unavailable", [])
    rows = []
    for player in unavailable:
        unavailability = player.get("unavailability", {})
        rows.append(
            {
                "Player": player.get("name"),
                "Status": unavailability.get("type", "Unavailable").title(),
                "Expected Return": unavailability.get("expectedReturn", "TBD"),
            }
        )
    return pd.DataFrame(rows)


def build_news_df(payload: dict) -> pd.DataFrame:
    team_news = payload.get("overview", {}).get("newsSummary", {}).get("items", [])
    rows = []
    for item in team_news:
        source = item.get("source", {})
        rows.append(
            {
                "title": source.get("title", "Untitled"),
                "summary": item.get("summary", ""),
                "link": source.get("uri", ""),
                "source": source.get("sourceName", "FotMob"),
                "published": "Latest",
            }
        )
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(fetch_google_news())


def format_money(value: float | int | None) -> str:
    if not value:
        return "N/A"
    return f"EUR {value / 1_000_000:.1f}M"


def base_chart_layout(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=12, r=12, t=42, b=12),
        height=height,
        legend_title_text="",
    )
    return fig


def add_pitch_shapes(fig: go.Figure) -> None:
    line = dict(color="rgba(255,255,255,0.7)", width=2)
    fig.add_shape(type="rect", x0=0, y0=0, x1=120, y1=80, line=line)
    fig.add_shape(type="line", x0=60, y0=0, x1=60, y1=80, line=line)
    fig.add_shape(type="circle", x0=50, y0=30, x1=70, y1=50, line=line)
    fig.add_shape(type="circle", x0=59.2, y0=39.2, x1=60.8, y1=40.8, line=line, fillcolor="white")
    fig.add_shape(type="rect", x0=0, y0=18, x1=18, y1=62, line=line)
    fig.add_shape(type="rect", x0=102, y0=18, x1=120, y1=62, line=line)
    fig.add_shape(type="rect", x0=0, y0=30, x1=6, y1=50, line=line)
    fig.add_shape(type="rect", x0=114, y0=30, x1=120, y1=50, line=line)


def build_pitch_positions(player_df: pd.DataFrame) -> pd.DataFrame:
    on_pitch = player_df[player_df["x"].notna()].copy()
    if on_pitch.empty:
        return on_pitch
    on_pitch["pitch_x"] = on_pitch["x"] * 120
    on_pitch["pitch_y"] = on_pitch["y"] * 80
    return on_pitch


def create_shot_threat_map(player_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=500,
    )
    add_pitch_shapes(fig)
    starters = build_pitch_positions(player_df[player_df["role"] == "Starter"])
    if starters.empty:
        fig.update_xaxes(range=[0, 120], visible=False)
        fig.update_yaxes(range=[0, 80], visible=False, scaleanchor="x", scaleratio=1)
        return fig
    starters["season_goals_num"] = starters["season_goals"].apply(numeric_or_default)
    starters["season_rating_num"] = starters["season_rating"].apply(lambda value: numeric_or_default(value, 6.0))
    starters["bubble"] = starters["season_goals_num"] * 6 + starters["season_rating_num"] * 2
    fig.add_trace(
        go.Scatter(
            x=starters["pitch_x"],
            y=starters["pitch_y"],
            mode="markers+text",
            text=starters["player"],
            textposition="top center",
            marker=dict(
                size=starters["bubble"].clip(lower=16, upper=44),
                color=starters["season_goals_num"],
                colorscale=[[0, "#FFE8A3"], [1, ARSENAL_RED]],
                line=dict(color="white", width=1.2),
                opacity=0.92,
                colorbar=dict(title="Goals", bgcolor=PANEL_BG),
            ),
            customdata=starters[["season_goals_num", "season_assists", "season_rating_num"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Season goals: %{customdata[0]}<br>"
                "Season assists: %{customdata[1]}<br>"
                "Season rating: %{customdata[2]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def create_match_shot_map(shot_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=500,
    )
    add_pitch_shapes(fig)
    if shot_df.empty:
        fig.update_xaxes(range=[0, 120], visible=False)
        fig.update_yaxes(range=[0, 80], visible=False, scaleanchor="x", scaleratio=1)
        return fig
    color_map = {
        "Goal": ARSENAL_RED,
        "Saved": ARSENAL_GOLD,
        "Miss": "#CBD5E1",
        "Post": "#7DD3FC",
    }
    fig.add_trace(
        go.Scatter(
            x=shot_df["x"],
            y=shot_df["y"],
            mode="markers+text",
            text=shot_df["player"],
            textposition="top center",
            marker=dict(
                size=shot_df["xg"].apply(lambda value: max(10, numeric_or_default(value) * 85 + 10)),
                color=shot_df["event_type"].map(color_map).fillna("#94A3B8"),
                line=dict(color="white", width=1.1),
                opacity=0.92,
            ),
            customdata=shot_df[["minute", "xg", "situation", "event_type"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Minute: %{customdata[0]}'<br>"
                "xG: %{customdata[1]:.2f}<br>"
                "Situation: %{customdata[2]}<br>"
                "Outcome: %{customdata[3]}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def build_shot_profile(shot_df: pd.DataFrame) -> dict[str, float]:
    if shot_df.empty:
        return {
            "shots": 0,
            "xg": 0.0,
            "big_chances": 0,
            "box_shots": 0,
            "central_shots": 0,
            "set_piece_xg": 0.0,
            "open_play_xg": 0.0,
        }
    xg_series = shot_df["xg"].apply(numeric_or_default)
    central = shot_df[(shot_df["x"] >= 90) & (shot_df["y"].between(26, 54))]
    set_piece_mask = shot_df["situation"].isin(["FromCorner", "SetPiece", "DirectFreekick"])
    return {
        "shots": int(len(shot_df)),
        "xg": float(xg_series.sum()),
        "big_chances": int((xg_series >= 0.2).sum()),
        "box_shots": int(shot_df["inside_box"].fillna(False).sum()),
        "central_shots": int(len(central)),
        "set_piece_xg": float(xg_series[set_piece_mask].sum()),
        "open_play_xg": float(xg_series[~set_piece_mask].sum()),
    }


def build_tactical_summary(player_df: pd.DataFrame, shot_df: pd.DataFrame) -> dict[str, float]:
    starters = player_df[player_df["role"] == "Starter"].copy()
    if starters.empty:
        return {
            "final_third_passes": 0.0,
            "mean_attack_height": 0.0,
            "rest_defence_count": 0.0,
            "right_lane_bias": 0.0,
        }
    starters["pass3_num"] = starters["passes_into_final_third"].apply(numeric_or_default)
    starters["x_num"] = starters["x"].apply(numeric_or_default)
    starters["y_num"] = starters["y"].apply(numeric_or_default)
    attacking_unit = starters[starters["x_num"] >= 0.48]
    right_bias = 0.0
    if not shot_df.empty:
        right_bias = float((shot_df["y"] > 40).mean() * 100)
    return {
        "final_third_passes": float(starters["pass3_num"].sum()),
        "mean_attack_height": float(attacking_unit["x_num"].mean() * 100) if not attacking_unit.empty else 0.0,
        "rest_defence_count": float((starters["x_num"] <= 0.42).sum()),
        "right_lane_bias": right_bias,
    }


def build_match_review(
    page_props: dict,
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    race_df: pd.DataFrame,
) -> tuple[str, list[str]]:
    facts = page_props.get("content", {}).get("matchFacts", {})
    player_of_match = facts.get("playerOfTheMatch", {})
    insights = facts.get("insights", [])
    title_map = {
        "Win": "なぜ勝てたか",
        "Draw": "引き分けの分岐点",
        "Loss": "なぜ勝ち切れなかったか",
        "Upcoming": "試合前の注目点",
    }
    lines: list[str] = []
    xg = shot_profile["xg"]
    opp_xg = opp_shot_profile["xg"]
    xg_margin = xg - opp_xg
    if xg_margin >= 0.6:
        lines.append(f"Arsenal は xG で {xg:.2f} - {opp_xg:.2f} と上回り、試合の質的優位を作れていました。")
    elif xg_margin <= -0.4:
        lines.append(f"xG は {xg:.2f} - {opp_xg:.2f} で相手優位。そもそものチャンス交換で押し込まれた試合です。")
    elif xg >= 1.0:
        lines.append(f"xG は {xg:.2f} - {opp_xg:.2f} と拮抗。細部の実行精度が結果を分けました。")
    else:
        lines.append(f"Arsenal の xG は {xg:.2f} に留まり、そもそもの決定機創出量が制約になりました。")

    if shot_profile["central_shots"] >= 3:
        lines.append(f"中央エリアから {shot_profile['central_shots']} 本打てており、最も価値の高いレーンには入れていました。")
    elif tactical_summary["right_lane_bias"] >= 60:
        lines.append(f"ショットの {tactical_summary['right_lane_bias']:.0f}% が右レーン寄りで、攻撃が片側に寄ったことが見えます。")
    else:
        lines.append("中央のボックス前で十分に厚みを作れず、フィニッシュ地点が分散しました。")

    if tactical_summary["final_third_passes"] >= 30:
        lines.append(f"Final-third passes は {tactical_summary['final_third_passes']:.0f} 本で、前進量はしっかり確保できています。")
    elif tactical_summary["final_third_passes"] >= 18:
        lines.append(f"Final-third passes は {tactical_summary['final_third_passes']:.0f} 本。前進はできた一方、最後の崩しがもう一段必要でした。")
    else:
        lines.append(f"Final-third passes が {tactical_summary['final_third_passes']:.0f} 本と少なく、相手陣での定着不足が目立ちました。")

    if not race_df.empty:
        arsenal_final = race_df[race_df["team"] == "Arsenal"]["cum_xg"].max() if not race_df[race_df["team"] == "Arsenal"].empty else 0
        opp_final = race_df[race_df["team"] == "Opponent"]["cum_xg"].max() if not race_df[race_df["team"] == "Opponent"].empty else 0
        arsenal_60 = race_df[(race_df["team"] == "Arsenal") & (race_df["minute"] <= 60)]["cum_xg"].max() if not race_df[(race_df["team"] == "Arsenal") & (race_df["minute"] <= 60)].empty else 0
        opp_60 = race_df[(race_df["team"] == "Opponent") & (race_df["minute"] <= 60)]["cum_xg"].max() if not race_df[(race_df["team"] == "Opponent") & (race_df["minute"] <= 60)].empty else 0
        if arsenal_60 - opp_60 >= 0.4:
            lines.append("xG race では 60 分まで Arsenal が先に主導権を握っており、試合の流れを先行して作れていました。")
        elif opp_60 - arsenal_60 >= 0.4:
            lines.append("前半から 60 分付近まで相手の xG ペースが上回り、Arsenal は試合の流れを奪い返す展開になりました。")
        elif arsenal_final > opp_final:
            lines.append("xG race は終盤にかけて Arsenal 側へ傾いており、試合後半の押し込みが結果に繋がった形です。")

    if shot_profile["set_piece_xg"] > 0.35:
        lines.append(f"Set-piece xG が {shot_profile['set_piece_xg']:.2f} と高く、流れの中だけでなく再開局面も鍵になっています。")
    if opp_shot_profile["set_piece_xg"] > 0.3:
        lines.append(f"一方で相手にも set-piece xG を {opp_shot_profile['set_piece_xg']:.2f} 許しており、守備面の弱点はそこにありました。")

    if player_of_match:
        full_name = player_of_match.get("name", {}).get("fullName", "Key player")
        rating = player_of_match.get("rating", {}).get("num", "")
        lines.append(f"キーマンは {full_name}。FotMob の Player of the Match で、レーティングは {rating} でした。")

    team_insight = next((item.get("text") for item in insights if item.get("teamId") == TEAM_ID and item.get("text")), None)
    if team_insight:
        lines.append(f"FotMob insight: {team_insight}")

    return title_map.get(selected_match["result"], "試合レビュー"), lines[:5]


def build_result_drivers(
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
    race_df: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    arsenal_edges: list[str] = []
    opponent_edges: list[str] = []

    if shot_profile["xg"] - opp_shot_profile["xg"] >= 0.4:
        arsenal_edges.append(f"xG edge: {shot_profile['xg']:.2f} vs {opp_shot_profile['xg']:.2f}")
    elif opp_shot_profile["xg"] - shot_profile["xg"] >= 0.4:
        opponent_edges.append(f"xG edge allowed: {opp_shot_profile['xg']:.2f} vs {shot_profile['xg']:.2f}")

    if shot_profile["central_shots"] > opp_shot_profile["central_shots"]:
        arsenal_edges.append(f"Central shot control: {shot_profile['central_shots']} vs {opp_shot_profile['central_shots']}")
    elif opp_shot_profile["central_shots"] > shot_profile["central_shots"]:
        opponent_edges.append(
            f"Central box access conceded: {opp_shot_profile['central_shots']} vs {shot_profile['central_shots']}"
        )

    if tactical_summary["final_third_passes"] >= 25:
        arsenal_edges.append(f"Final-third progression: {tactical_summary['final_third_passes']:.0f} passes")
    else:
        opponent_edges.append(f"Limited territorial control: {tactical_summary['final_third_passes']:.0f} final-third passes")

    if arsenal_zone_profile["zone14_entries"] > opponent_zone_profile["zone14_entries"]:
        arsenal_edges.append(
            f"Zone 14 access: {arsenal_zone_profile['zone14_entries']} vs {opponent_zone_profile['zone14_entries']}"
        )
    elif opponent_zone_profile["zone14_entries"] > arsenal_zone_profile["zone14_entries"]:
        opponent_edges.append(
            f"Opponent Zone 14 access: {opponent_zone_profile['zone14_entries']} vs {arsenal_zone_profile['zone14_entries']}"
        )

    if opp_shot_profile["set_piece_xg"] >= 0.3:
        opponent_edges.append(f"Set-piece threat conceded: {opp_shot_profile['set_piece_xg']:.2f} xG")
    if shot_profile["set_piece_xg"] >= 0.25:
        arsenal_edges.append(f"Set-piece threat created: {shot_profile['set_piece_xg']:.2f} xG")

    if not race_df.empty:
        arsenal_60 = (
            race_df[(race_df["team"] == "Arsenal") & (race_df["minute"] <= 60)]["cum_xg"].max()
            if not race_df[(race_df["team"] == "Arsenal") & (race_df["minute"] <= 60)].empty
            else 0
        )
        opp_60 = (
            race_df[(race_df["team"] == "Opponent") & (race_df["minute"] <= 60)]["cum_xg"].max()
            if not race_df[(race_df["team"] == "Opponent") & (race_df["minute"] <= 60)].empty
            else 0
        )
        if arsenal_60 - opp_60 >= 0.35:
            arsenal_edges.append("Early control: Arsenal led the xG race by 60'")
        elif opp_60 - arsenal_60 >= 0.35:
            opponent_edges.append("Early control lost: opponent led the xG race by 60'")

    return arsenal_edges[:4], opponent_edges[:4]


def build_match_swing_notes(race_df: pd.DataFrame) -> list[str]:
    if race_df.empty:
        return ["十分な shot-by-shot データがなく、流れの転換点は特定できません。"]

    arsenal = race_df[race_df["team"] == "Arsenal"][["minute", "cum_xg"]].rename(columns={"cum_xg": "arsenal_cum"})
    opponent = race_df[race_df["team"] == "Opponent"][["minute", "cum_xg"]].rename(columns={"cum_xg": "opp_cum"})
    combined = (
        pd.merge(arsenal, opponent, on="minute", how="outer")
        .sort_values("minute")
        .ffill()
        .fillna(0)
    )
    combined["swing"] = combined["arsenal_cum"] - combined["opp_cum"]
    if combined.empty:
        return ["十分な shot-by-shot データがなく、流れの転換点は特定できません。"]

    biggest_edge = combined.loc[combined["swing"].idxmax()]
    deepest_deficit = combined.loc[combined["swing"].idxmin()]
    final_edge = float(combined["swing"].iloc[-1])
    notes = []
    notes.append(
        f"最大優位は {int(biggest_edge['minute'])}' 時点で {biggest_edge['swing']:+.2f} xG。"
    )
    notes.append(
        f"最も苦しかった局面は {int(deepest_deficit['minute'])}' 時点で {deepest_deficit['swing']:+.2f} xG。"
    )
    if final_edge >= 0.3:
        notes.append("最終的には Arsenal が試合終盤で質的優位を維持しました。")
    elif final_edge <= -0.3:
        notes.append("終盤まで相手に高品質のチャンス交換を許した試合です。")
    else:
        notes.append("最終的な chance quality は拮抗しており、決定力や守備の細部が勝敗を分けました。")
    return notes


def build_key_moments_df(shot_df: pd.DataFrame, arsenal_team_id: int) -> pd.DataFrame:
    if shot_df.empty:
        return pd.DataFrame(columns=["Minute", "Team", "Player", "xG", "Outcome", "Situation"])
    frame = shot_df.copy()
    frame["Team"] = frame["team_id"].apply(lambda value: "Arsenal" if value == arsenal_team_id else "Opponent")
    frame["xG_num"] = frame["xg"].apply(numeric_or_default)
    frame = frame.sort_values(["xG_num", "minute"], ascending=[False, True]).head(10)
    frame = frame.sort_values("minute")
    return pd.DataFrame(
        {
            "Minute": frame["minute"].astype(str) + "'",
            "Team": frame["Team"],
            "Player": frame["player"].fillna("Unknown"),
            "xG": frame["xG_num"].map(lambda value: f"{value:.2f}"),
            "Outcome": frame["event_type"].fillna("Shot"),
            "Situation": frame["situation"].fillna("OpenPlay"),
        }
    )


def build_control_profile(
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
) -> dict[str, float]:
    arsenal_pressure = (
        tactical_summary["final_third_passes"]
        + shot_profile["box_shots"] * 3
        + arsenal_zone_profile["zone14_entries"] * 2
        + shot_profile["big_chances"] * 4
    )
    opponent_pressure = (
        opp_shot_profile["shots"] * 2
        + opponent_zone_profile["zone14_entries"] * 2
        + opp_shot_profile["big_chances"] * 4
    )
    total_pressure = arsenal_pressure + opponent_pressure
    field_tilt_proxy = (arsenal_pressure / total_pressure * 100) if total_pressure else 50.0
    return {
        "field_tilt_proxy": field_tilt_proxy,
        "box_entry_proxy": float(
            arsenal_zone_profile["zone14_entries"]
            + arsenal_zone_profile["left_half_space_shots"]
            + arsenal_zone_profile["right_half_space_shots"]
        ),
        "box_touch_proxy": float(shot_profile["box_shots"] + shot_profile["big_chances"] * 1.5),
        "opponent_box_touch_proxy": float(opp_shot_profile["box_shots"] + opp_shot_profile["big_chances"] * 1.5),
    }


def build_recent_form_summary(matches_df: pd.DataFrame, limit: int = 5) -> tuple[str, int]:
    completed = matches_df[matches_df["finished"]].sort_values("date", ascending=False).head(limit)
    if completed.empty:
        return "N/A", 0
    mapping = {"Win": "W", "Draw": "D", "Loss": "L"}
    form = "".join(mapping.get(result, "-") for result in completed["result"].tolist())
    return form, int(len(completed))


def build_defensive_review(
    opp_shot_profile: dict[str, float],
    opponent_zone_profile: dict[str, int],
    tactical_summary: dict[str, float],
) -> list[str]:
    lines: list[str] = []
    if opp_shot_profile["xg"] >= 1.5:
        lines.append(f"相手に {opp_shot_profile['xg']:.2f} xG を許しており、守備の質としては不安定でした。")
    elif opp_shot_profile["xg"] >= 0.9:
        lines.append(f"相手の xG は {opp_shot_profile['xg']:.2f}。一定の危険はあったものの、崩壊まではしていません。")
    else:
        lines.append(f"相手の xG は {opp_shot_profile['xg']:.2f} に抑えられており、総量としては良い守備でした。")

    if opp_shot_profile["central_shots"] >= 3:
        lines.append(f"中央から {opp_shot_profile['central_shots']} 本を許し、最も危険なエリアを閉じ切れませんでした。")
    else:
        lines.append("中央のシュート数は抑えられており、危険地帯の封鎖自体は概ねできています。")

    if opponent_zone_profile["zone14_entries"] >= 3:
        lines.append(f"Zone 14 への侵入を {opponent_zone_profile['zone14_entries']} 回許し、前向きで持たれる場面がありました。")
    else:
        lines.append("Zone 14 への侵入は限定的で、前向きで差し込まれる回数は多くありませんでした。")

    if tactical_summary["rest_defence_count"] <= 2:
        lines.append("rest defence の人数が薄く、保持時の背後ケアにはリスクがありました。")
    else:
        lines.append("保持時にも後方の人数はある程度残せており、トランジション耐性は確保できています。")
    return lines[:4]


def build_score_state_df(shot_df: pd.DataFrame, arsenal_team_id: int) -> pd.DataFrame:
    if shot_df.empty:
        return pd.DataFrame(columns=["State", "Team", "Shots", "xG"])
    frame = shot_df.copy()
    frame["minute_num"] = frame["minute"].apply(lambda value: int(numeric_or_default(value)))
    frame["xg_num"] = frame["xg"].apply(numeric_or_default)
    frame = frame.sort_values(["minute_num", "xg_num"]).reset_index(drop=True)

    arsenal_goals = 0
    opponent_goals = 0
    states = []
    teams = []
    for _, row in frame.iterrows():
        if arsenal_goals > opponent_goals:
            state = "Leading"
        elif arsenal_goals < opponent_goals:
            state = "Trailing"
        else:
            state = "Level"
        states.append(state)
        teams.append("Arsenal" if row["team_id"] == arsenal_team_id else "Opponent")
        if str(row.get("event_type", "")).lower() == "goal":
            if row["team_id"] == arsenal_team_id:
                arsenal_goals += 1
            else:
                opponent_goals += 1

    frame["State"] = states
    frame["Team"] = teams
    grouped = (
        frame.groupby(["State", "Team"], dropna=False)
        .agg(Shots=("minute", "count"), xG=("xg_num", "sum"))
        .reset_index()
    )
    order = pd.CategoricalDtype(["Level", "Leading", "Trailing"], ordered=True)
    grouped["State"] = grouped["State"].astype(order)
    return grouped.sort_values(["State", "Team"]).reset_index(drop=True)


def create_score_state_chart(score_state_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        score_state_df,
        x="State",
        y="xG",
        color="Team",
        barmode="group",
        text_auto=".2f",
        color_discrete_map={"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"},
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="xG by score state", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_player_relationships(player_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    starters = build_pitch_positions(player_df[player_df["role"] == "Starter"])
    if starters.empty:
        empty_links = pd.DataFrame(columns=["Pair", "Weight", "Accurate Passes", "Final-third Passes"])
        empty_hubs = pd.DataFrame(columns=["Player", "Hub Score", "Touches", "Accurate Passes"])
        return empty_links, empty_hubs

    starters["accurate_passes_num"] = starters["accurate_passes"].apply(numeric_or_default)
    starters["passes_into_final_third_num"] = starters["passes_into_final_third"].apply(numeric_or_default)
    starters["touches_num"] = starters["touches"].apply(numeric_or_default)
    edges = build_pass_network_edges(starters)

    link_rows = []
    hub_scores: dict[str, float] = {player: 0.0 for player in starters["player"].tolist()}
    for left, right, weight in edges:
        link_rows.append(
            {
                "Pair": f"{left['player']} + {right['player']}",
                "Weight": round(weight, 2),
                "Accurate Passes": int(numeric_or_default(left.get("accurate_passes")) + numeric_or_default(right.get("accurate_passes"))),
                "Final-third Passes": int(
                    numeric_or_default(left.get("passes_into_final_third")) + numeric_or_default(right.get("passes_into_final_third"))
                ),
            }
        )
        hub_scores[str(left["player"])] += weight
        hub_scores[str(right["player"])] += weight

    links_df = pd.DataFrame(link_rows).sort_values("Weight", ascending=False).head(6) if link_rows else pd.DataFrame(
        columns=["Pair", "Weight", "Accurate Passes", "Final-third Passes"]
    )
    hubs_df = pd.DataFrame(
        {
            "Player": starters["player"],
            "Hub Score": starters["player"].map(hub_scores).round(2),
            "Touches": starters["touches_num"].astype(int),
            "Accurate Passes": starters["accurate_passes_num"].astype(int),
        }
    ).sort_values(["Hub Score", "Touches"], ascending=False).head(6)
    return links_df, hubs_df


def create_hub_chart(hubs_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        hubs_df,
        x="Player",
        y="Hub Score",
        color="Touches",
        color_continuous_scale=[[0, "#FFE8A3"], [1, ARSENAL_RED]],
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Hub score", gridcolor="rgba(159,176,196,0.14)")
    return fig


def create_match_report_comparison_chart(
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
) -> go.Figure:
    comparison_df = pd.DataFrame(
        [
            {"Metric": "xG", "Arsenal": shot_profile["xg"], "Opponent": opp_shot_profile["xg"]},
            {"Metric": "Central Shots", "Arsenal": shot_profile["central_shots"], "Opponent": opp_shot_profile["central_shots"]},
            {"Metric": "Box Shots", "Arsenal": shot_profile["box_shots"], "Opponent": opp_shot_profile["box_shots"]},
            {"Metric": "Zone 14", "Arsenal": arsenal_zone_profile["zone14_entries"], "Opponent": opponent_zone_profile["zone14_entries"]},
            {"Metric": "Box Touch Proxy", "Arsenal": control_profile["box_touch_proxy"], "Opponent": control_profile["opponent_box_touch_proxy"]},
            {"Metric": "Field Tilt %", "Arsenal": control_profile["field_tilt_proxy"], "Opponent": 100 - control_profile["field_tilt_proxy"]},
            {"Metric": "Final-third Passes", "Arsenal": tactical_summary["final_third_passes"], "Opponent": 0},
        ]
    )
    long_df = comparison_df.melt(id_vars="Metric", var_name="Team", value_name="Value")
    fig = px.bar(
        long_df,
        x="Metric",
        y="Value",
        color="Team",
        barmode="group",
        text_auto=".1f",
        color_discrete_map={"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"},
    )
    fig = base_chart_layout(fig, height=340)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_player_deep_dive(
    player_df: pd.DataFrame,
    shot_df: pd.DataFrame,
    relationship_hubs_df: pd.DataFrame,
    selected_player: str,
) -> dict[str, object]:
    player_row = player_df[player_df["player"] == selected_player]
    if player_row.empty:
        return {}
    row = player_row.iloc[0]
    player_shots = shot_df[shot_df["player"] == selected_player].copy() if not shot_df.empty else pd.DataFrame()
    player_shots["xg_num"] = player_shots["xg"].apply(numeric_or_default) if not player_shots.empty else []
    hub_row = relationship_hubs_df[relationship_hubs_df["Player"] == selected_player] if not relationship_hubs_df.empty else pd.DataFrame()
    return {
        "player": selected_player,
        "rating": row.get("rating_last_match"),
        "accurate_passes": int(numeric_or_default(row.get("accurate_passes"))),
        "final_third_passes": int(numeric_or_default(row.get("passes_into_final_third"))),
        "touches": int(numeric_or_default(row.get("touches"))),
        "recoveries": int(numeric_or_default(row.get("recoveries"))),
        "distance_covered": numeric_or_default(row.get("distance_covered")),
        "shots": int(len(player_shots)),
        "xg": float(player_shots["xg_num"].sum()) if not player_shots.empty else 0.0,
        "hub_score": float(hub_row.iloc[0]["Hub Score"]) if not hub_row.empty else 0.0,
        "shot_df": player_shots,
    }


def create_player_stat_bar(deep_dive: dict[str, object]) -> go.Figure:
    stat_df = pd.DataFrame(
        {
            "Metric": ["Accurate Passes", "Final-third Passes", "Touches", "Recoveries", "Shots", "Hub Score"],
            "Value": [
                deep_dive.get("accurate_passes", 0),
                deep_dive.get("final_third_passes", 0),
                deep_dive.get("touches", 0),
                deep_dive.get("recoveries", 0),
                deep_dive.get("shots", 0),
                deep_dive.get("hub_score", 0.0),
            ],
        }
    )
    fig = px.bar(
        stat_df,
        x="Metric",
        y="Value",
        color="Value",
        color_continuous_scale=[[0, "#FFE8A3"], [1, ARSENAL_RED]],
        text_auto=".1f",
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title=None, gridcolor="rgba(159,176,196,0.14)")
    fig.update_layout(coloraxis_showscale=False)
    return fig


def build_player_heatmap_points(
    heatmap_payload: dict,
    page_props: dict,
    player_name: str,
) -> pd.DataFrame:
    if not heatmap_payload:
        return pd.DataFrame(columns=["x", "y"])
    player_stats = page_props.get("content", {}).get("playerStats", {})
    target_opta_id = None
    for player in player_stats.values():
        if player.get("name") == player_name:
            target_opta_id = player.get("optaId")
            break
    if not target_opta_id:
        return pd.DataFrame(columns=["x", "y"])
    svg_fragment = heatmap_payload.get("players", {}).get(f"p{target_opta_id}")
    if not svg_fragment:
        return pd.DataFrame(columns=["x", "y"])
    try:
        wrapped = f"<root>{svg_fragment}</root>"
        root = ET.fromstring(wrapped)
    except ET.ParseError:
        return pd.DataFrame(columns=["x", "y"])
    rows = []
    for circle in root.findall("circle"):
        rows.append(
            {
                "x": numeric_or_default(circle.attrib.get("cx")) * (120 / 105),
                "y": numeric_or_default(circle.attrib.get("cy")) * (80 / 68),
            }
        )
    return pd.DataFrame(rows)


def create_player_heatmap(points_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=500,
    )
    add_pitch_shapes(fig)
    if points_df.empty:
        fig.update_xaxes(range=[-2, 122], visible=False)
        fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
        return fig
    fig.add_trace(
        go.Histogram2dContour(
            x=points_df["x"],
            y=points_df["y"],
            colorscale=[
                [0.0, "rgba(255,232,163,0.05)"],
                [0.25, "rgba(245,196,81,0.25)"],
                [0.5, "rgba(217,4,41,0.45)"],
                [1.0, "rgba(217,4,41,0.85)"],
            ],
            contours=dict(coloring="heatmap", showlines=False),
            showscale=False,
            ncontours=12,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=points_df["x"],
            y=points_df["y"],
            mode="markers",
            marker=dict(size=4, color="rgba(255,255,255,0.25)"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def build_key_player_summary(
    page_props: dict,
    player_df: pd.DataFrame,
    shot_df: pd.DataFrame,
    relationship_hubs_df: pd.DataFrame,
) -> tuple[str, list[str]]:
    facts = page_props.get("content", {}).get("matchFacts", {})
    pom = facts.get("playerOfTheMatch", {})
    pom_name = pom.get("name", {}).get("fullName")
    player_name = pom_name

    shot_work = {}
    if not shot_df.empty:
        shot_frame = shot_df.copy()
        shot_frame["xg_num"] = shot_frame["xg"].apply(numeric_or_default)
        shot_work = (
            shot_frame.groupby("player", dropna=False)
            .agg(Shots=("player", "count"), xG=("xg_num", "sum"))
            .reset_index()
            .sort_values(["xG", "Shots"], ascending=False)
        )
        if not player_name and not shot_work.empty:
            player_name = shot_work.iloc[0]["player"]

    if not player_name and not relationship_hubs_df.empty:
        player_name = relationship_hubs_df.iloc[0]["Player"]
    if not player_name and not player_df.empty:
        player_name = player_df.sort_values("rating_last_match", ascending=False, na_position="last").iloc[0]["player"]

    reasons: list[str] = []
    if player_name and isinstance(shot_work, pd.DataFrame) and not shot_work.empty:
        player_shots = shot_work[shot_work["player"] == player_name]
        if not player_shots.empty:
            row = player_shots.iloc[0]
            reasons.append(f"shot involvement: {int(row['Shots'])} shots, {row['xG']:.2f} xG")

    if player_name and not relationship_hubs_df.empty:
        hub_row = relationship_hubs_df[relationship_hubs_df["Player"] == player_name]
        if not hub_row.empty:
            row = hub_row.iloc[0]
            reasons.append(f"build-up hub: hub score {row['Hub Score']:.2f}, {int(row['Touches'])} touches")

    if player_name and not player_df.empty:
        player_row = player_df[player_df["player"] == player_name]
        if not player_row.empty:
            row = player_row.iloc[0]
            if pd.notna(row.get("accurate_passes")):
                reasons.append(f"ball circulation: {int(numeric_or_default(row.get('accurate_passes')))} accurate passes")
            if pd.notna(row.get("passes_into_final_third")):
                reasons.append(f"progression: {int(numeric_or_default(row.get('passes_into_final_third')))} final-third passes")

    return player_name or "Undetermined", reasons[:3]


def build_attack_review(
    shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    control_profile: dict[str, float],
) -> list[str]:
    lines: list[str] = []
    if shot_profile["xg"] >= 1.8:
        lines.append(f"攻撃は十分に機能していて、{shot_profile['xg']:.2f} xG を作れていました。")
    elif shot_profile["xg"] >= 1.0:
        lines.append(f"攻撃は一定水準で成立しており、{shot_profile['xg']:.2f} xG を確保しています。")
    else:
        lines.append(f"攻撃の総量は物足りず、xG は {shot_profile['xg']:.2f} に留まりました。")

    if shot_profile["central_shots"] >= 3:
        lines.append(f"中央から {shot_profile['central_shots']} 本打てていて、最重要レーンへ入れています。")
    else:
        lines.append("中央の危険地帯へのアクセスは足りず、フィニッシュの質が上がり切りませんでした。")

    if tactical_summary["final_third_passes"] >= 25 and control_profile["field_tilt_proxy"] >= 55:
        lines.append("相手陣での定着と押し込みは十分で、保持攻撃として主導権を持てています。")
    elif tactical_summary["final_third_passes"] >= 18:
        lines.append("前進自体はできていましたが、押し込みを決定機へ変える最後の精度が不足しました。")
    else:
        lines.append("相手陣での定着不足があり、攻撃を繰り返し打ち込む形にはできませんでした。")

    if arsenal_zone_profile["left_half_space_shots"] + arsenal_zone_profile["right_half_space_shots"] >= 4:
        lines.append("ハーフスペースも使えており、中央一辺倒ではない攻略ができています。")
    else:
        lines.append("ハーフスペース活用は限定的で、崩しの幅がやや足りませんでした。")
    return lines[:4]


def build_opponent_possession_review(
    opp_shot_profile: dict[str, float],
    opponent_zone_profile: dict[str, int],
    control_profile: dict[str, float],
) -> list[str]:
    lines: list[str] = []
    if control_profile["field_tilt_proxy"] <= 48:
        lines.append("相手保持の時間帯が長く、Arsenal は押し返される局面がありました。")
    else:
        lines.append("全体としては Arsenal が押し込んでおり、相手保持は断続的でした。")

    if opponent_zone_profile["zone14_entries"] >= 3:
        lines.append(f"相手は Zone 14 へ {opponent_zone_profile['zone14_entries']} 回入れており、中央前で前向きになる場面を作っていました。")
    else:
        lines.append("相手の Zone 14 侵入は限定されており、中央前で自由には持たせていません。")

    if opp_shot_profile["set_piece_xg"] >= 0.3:
        lines.append(f"相手の脅威はセットプレーでも大きく、{opp_shot_profile['set_piece_xg']:.2f} xG を許しています。")
    else:
        lines.append("相手のセットプレー脅威は大きくなく、主な問題は流れの中の局面管理でした。")

    if opp_shot_profile["central_shots"] >= 3:
        lines.append("相手は中央の危険地帯に入れており、守備ブロックの中を割られる局面がありました。")
    else:
        lines.append("相手のフィニッシュ地点は比較的外に追いやれており、守備の形自体は大きく崩れていません。")
    return lines[:4]


def build_player_impact_df(player_df: pd.DataFrame) -> pd.DataFrame:
    if player_df.empty:
        return pd.DataFrame(columns=["Player", "Impact", "Why"])
    frame = player_df[player_df["role"] != "Unavailable"].copy()
    frame["rating_num"] = frame["rating_last_match"].apply(lambda value: numeric_or_default(value, 0.0))
    frame["accurate_passes_num"] = frame["accurate_passes"].apply(numeric_or_default)
    frame["final_third_num"] = frame["passes_into_final_third"].apply(numeric_or_default)
    frame["touches_num"] = frame["touches"].apply(numeric_or_default)
    frame["impact"] = (
        frame["rating_num"] * 1.8
        + frame["final_third_num"] * 0.9
        + frame["accurate_passes_num"] * 0.08
        + frame["touches_num"] * 0.04
    )
    frame["Why"] = frame.apply(
        lambda row: (
            f"rating {row['rating_num']:.1f} | final-third {int(row['final_third_num'])} | "
            f"passes {int(row['accurate_passes_num'])} | touches {int(row['touches_num'])}"
        ),
        axis=1,
    )
    return (
        frame[["player", "impact", "Why"]]
        .rename(columns={"player": "Player", "impact": "Impact"})
        .sort_values("Impact", ascending=False)
        .head(8)
        .reset_index(drop=True)
    )


def build_phase_comparison_summary(shot_df: pd.DataFrame, opp_shot_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    def summarize(frame: pd.DataFrame, label: str, phase_name: str, start: int, end: int) -> dict[str, object]:
        phase_df = frame.copy()
        if phase_df.empty:
            return {"Phase": phase_name, "Team": label, "Shots": 0, "xG": 0.0, "Central Shots": 0}
        phase_df["minute_num"] = phase_df["minute"].apply(lambda value: int(numeric_or_default(value)))
        phase_df["xg_num"] = phase_df["xg"].apply(numeric_or_default)
        phase_df = phase_df[phase_df["minute_num"].between(start, end)]
        central = phase_df[(phase_df["x"] >= 90) & (phase_df["y"].between(26, 54))]
        return {
            "Phase": phase_name,
            "Team": label,
            "Shots": int(len(phase_df)),
            "xG": float(phase_df["xg_num"].sum()),
            "Central Shots": int(len(central)),
        }

    rows = [
        summarize(shot_df, "Arsenal", "First Half", 0, 45),
        summarize(opp_shot_df, "Opponent", "First Half", 0, 45),
        summarize(shot_df, "Arsenal", "Second Half", 46, 130),
        summarize(opp_shot_df, "Opponent", "Second Half", 46, 130),
    ]
    phase_df = pd.DataFrame(rows)
    notes = []
    arsenal_first = phase_df[(phase_df["Phase"] == "First Half") & (phase_df["Team"] == "Arsenal")]["xG"].iloc[0]
    arsenal_second = phase_df[(phase_df["Phase"] == "Second Half") & (phase_df["Team"] == "Arsenal")]["xG"].iloc[0]
    opp_first = phase_df[(phase_df["Phase"] == "First Half") & (phase_df["Team"] == "Opponent")]["xG"].iloc[0]
    opp_second = phase_df[(phase_df["Phase"] == "Second Half") & (phase_df["Team"] == "Opponent")]["xG"].iloc[0]
    if arsenal_second - arsenal_first >= 0.3:
        notes.append("後半の方が Arsenal の攻撃は改善しており、ハーフタイム以降の修正が効いた可能性があります。")
    elif arsenal_first - arsenal_second >= 0.3:
        notes.append("前半優位を後半に再現できず、試合後半の再調整が課題です。")
    if opp_second - opp_first >= 0.3:
        notes.append("相手は後半に脅威を増しており、試合中の対応が必要だった可能性があります。")
    return phase_df, notes[:3]


def create_phase_comparison_chart(phase_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        phase_df,
        x="Phase",
        y="xG",
        color="Team",
        barmode="group",
        facet_col="Team",
        text_auto=".2f",
        color_discrete_map={"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"},
    )
    fig = base_chart_layout(fig, height=320)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="xG", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_role_profile_df(player_df: pd.DataFrame, shot_df: pd.DataFrame, relationship_hubs_df: pd.DataFrame) -> pd.DataFrame:
    if player_df.empty:
        return pd.DataFrame(columns=["Player", "Role", "Evidence"])
    hub_map = {}
    if not relationship_hubs_df.empty:
        hub_map = dict(zip(relationship_hubs_df["Player"], relationship_hubs_df["Hub Score"]))
    shot_counts = shot_df.groupby("player").size().to_dict() if not shot_df.empty else {}
    rows = []
    for _, row in player_df[player_df["role"] != "Unavailable"].iterrows():
        name = row["player"]
        final_third = int(numeric_or_default(row.get("passes_into_final_third")))
        accurate_passes = int(numeric_or_default(row.get("accurate_passes")))
        touches = int(numeric_or_default(row.get("touches")))
        recoveries = int(numeric_or_default(row.get("recoveries")))
        shots = int(shot_counts.get(name, 0))
        hub_score = float(hub_map.get(name, 0.0))
        role = "Connector"
        if shots >= 3 or (shots >= 1 and numeric_or_default(row.get("rating_last_match")) >= 7.5):
            role = "Finisher"
        elif final_third >= 6 or accurate_passes >= 50:
            role = "Progressor"
        elif recoveries >= 6:
            role = "Ball Winner"
        elif hub_score >= 3.0 or touches >= 55:
            role = "Connector"
        evidence = f"shots {shots} | final-third {final_third} | passes {accurate_passes} | recoveries {recoveries} | hub {hub_score:.2f}"
        rows.append({"Player": name, "Role": role, "Evidence": evidence})
    return pd.DataFrame(rows)


def build_opponent_game_plan(
    next_match: dict | None,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    structural_diagnosis_df: pd.DataFrame,
) -> list[str]:
    plan = []
    opponent_name = next_match["opponent"]["name"] if next_match else "the next opponent"
    plan.append(f"次戦の {opponent_name} 戦では、今回の構造で機能した点を先に再現するべきです。")
    if shot_profile["central_shots"] >= 3:
        plan.append("中央侵入が作れているので、同じくボックス中央へ届く形を優先したいです。")
    else:
        plan.append("中央侵入が足りないので、外回しだけで終わらない中央経由の崩しを増やしたいです。")
    if opp_shot_profile["central_shots"] >= 3:
        plan.append("守備では中央封鎖を優先し、相手に最も危険なエリアを使わせない準備が必要です。")
    if tactical_summary["rest_defence_count"] <= 2:
        plan.append("保持時の後方配置を調整し、トランジション耐性を上げるべきです。")
    if control_profile["field_tilt_proxy"] < 50:
        plan.append("試合の入りから押し込めていないので、最初の20分で相手陣に定着するプランが重要です。")
    if not structural_diagnosis_df.empty:
        weakest = structural_diagnosis_df.sort_values("Score").iloc[0]["Factor"]
        plan.append(f"優先修正ポイントは {weakest} です。次戦準備はここから始めるのが妥当です。")
    return plan[:5]


def build_analysis_template_sections(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
    match_swing_notes: list[str],
    structural_summary_lines: list[str],
    attack_review_lines: list[str],
    defensive_review_lines: list[str],
    opponent_possession_review_lines: list[str],
    role_profile_df: pd.DataFrame,
    coach_takeaways: dict[str, list[str] | str],
    opponent_game_plan_lines: list[str],
) -> list[dict[str, object]]:
    top_roles = []
    if not role_profile_df.empty:
        top_roles = [
            f"{row['Player']}: {row['Role']}"
            for _, row in role_profile_df.head(4).iterrows()
        ]

    return [
        {
            "section": "1. Result Context",
            "question": "What kind of match was this?",
            "metrics": [
                f"Opponent: {selected_match['opponent']}",
                f"Score: {selected_match['score']}",
                f"Result: {selected_match['result']}",
            ],
            "visual": "Match Center, Recent Results, Event Timeline",
            "interpretation": "結果だけでなく、会場・相手・試合展開を前提条件として読む。",
            "action": "評価は必ずゲームステートと相手文脈込みで判断する。",
        },
        {
            "section": "2. Chance Quality",
            "question": "Did Arsenal create better chances?",
            "metrics": [
                f"xG: {shot_profile['xg']:.2f} vs {opp_shot_profile['xg']:.2f}",
                f"Open-play xG: {shot_profile['open_play_xg']:.2f}",
                f"Set-piece xG: {shot_profile['set_piece_xg']:.2f}",
                f"Big chances: {shot_profile['big_chances']}",
            ],
            "visual": "Chance Quality Profile, xG Race, Shot Map",
            "interpretation": "Cannon Stats 風に、まずショット数ではなく質を読む。",
            "action": "open play と set piece を分けて、再現性の高い得点源を判断する。",
        },
        {
            "section": "3. Territory",
            "question": "Where was the match played?",
            "metrics": [
                f"Field tilt proxy: {control_profile['field_tilt_proxy']:.0f}%",
                f"Final-third passes: {tactical_summary['final_third_passes']:.0f}",
                f"Box entry proxy: {control_profile['box_entry_proxy']:.0f}",
            ],
            "visual": "Territory & Access, Zone Profile",
            "interpretation": "押し込めたか、押し込まれたかを結果の土台として読む。",
            "action": "押し込めているのに質が低いなら崩し、押し込めていないなら前進構造を修正する。",
        },
        {
            "section": "4. Shot Profile",
            "question": "Where did the shots come from?",
            "metrics": [
                f"Central shots: {shot_profile['central_shots']} vs {opp_shot_profile['central_shots']}",
                f"Box shots: {shot_profile['box_shots']} vs {opp_shot_profile['box_shots']}",
                f"Zone 14: {arsenal_zone_profile['zone14_entries']} vs {opponent_zone_profile['zone14_entries']}",
            ],
            "visual": "Match Shot Map, Zone Profile",
            "interpretation": "中央・ボックス内・Zone 14 の占有が攻撃の質を説明する。",
            "action": "低価値ショットが多い場合は、シュート地点より前の侵入経路を修正する。",
        },
        {
            "section": "5. Game Flow",
            "question": "When did control change?",
            "metrics": match_swing_notes[:3],
            "visual": "xG Race, Phase Control, Half-by-Half Adjustments",
            "interpretation": "90分平均ではなく、どの時間帯で流れを失ったかを見る。",
            "action": "前後半差や交代後の変化を次戦の介入タイミングに変換する。",
        },
        {
            "section": "6. Possession Structure",
            "question": "How did Arsenal progress the ball?",
            "metrics": [
                f"Attack height: {tactical_summary['mean_attack_height']:.0f}",
                f"Right lane bias: {tactical_summary['right_lane_bias']:.0f}%",
                f"Rest defence count: {tactical_summary['rest_defence_count']:.0f}",
            ],
            "visual": "Pass Network, Player Relationships, Player Heatmap",
            "interpretation": "誰がハブで、どのレーンから前進したかを構造として読む。",
            "action": "機能した関係性は残し、詰まったレーンには受け手や立ち位置を足す。",
        },
        {
            "section": "7. Defensive Structure",
            "question": "How did the opponent hurt Arsenal?",
            "metrics": defensive_review_lines[:4],
            "visual": "Defensive Review, Opponent Threat, Event Timeline",
            "interpretation": "失点や被 xG を、中央管理・セットプレー・rest defence に分解する。",
            "action": "相手の脅威が中央か外か、セットプレーか流れかを分けて次戦準備に落とす。",
        },
        {
            "section": "8. Player Roles",
            "question": "Who performed which job?",
            "metrics": top_roles,
            "visual": "Role Evaluation, Player Deep Dive, Heatmap",
            "interpretation": "選手を得点/アシストだけでなく、役割と証拠で評価する。",
            "action": "次戦の起用は名前ではなく、必要な役割から逆算する。",
        },
        {
            "section": "9. Structural Diagnosis",
            "question": "Why did the result happen structurally?",
            "metrics": structural_summary_lines[:4],
            "visual": "Structural Diagnosis",
            "interpretation": "攻撃・守備・陣地・ゲームステート・選手間構造を同じ型で比較する。",
            "action": "最も弱かった構造要因を、次戦の最優先修正テーマにする。",
        },
        {
            "section": "10. Coach Takeaways",
            "question": "What changes next?",
            "metrics": opponent_game_plan_lines[:4],
            "visual": "Coach Takeaways, Next Match Prep",
            "interpretation": "試合後レビューを、次戦の継続点・修正点・起用判断に変換する。",
            "action": "; ".join(coach_takeaways.get("change", [])) or "次戦準備へ変換する。",
        },
    ]


def build_analysis_template_markdown(sections: list[dict[str, object]]) -> str:
    lines = ["## Analysis Template"]
    for section in sections:
        lines.extend(
            [
                "",
                f"### {section['section']}",
                f"- Question: {section['question']}",
                f"- Visual: {section['visual']}",
                f"- Interpretation: {section['interpretation']}",
                f"- Coaching action: {section['action']}",
            ]
        )
        metrics = section.get("metrics", [])
        for metric in metrics:
            lines.append(f"- Signal: {metric}")
    return "\n".join(lines)


def build_full_match_report(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
    review_lines: list[str],
    attack_review_lines: list[str],
    defensive_review_lines: list[str],
    opponent_possession_review_lines: list[str],
    match_swing_notes: list[str],
    arsenal_edges: list[str],
    opponent_edges: list[str],
    key_player_name: str,
    key_player_reasons: list[str],
    player_impact_df: pd.DataFrame,
    coach_takeaways: dict[str, list[str] | str],
    structural_summary_lines: list[str],
    phase_comparison_notes: list[str],
    opponent_game_plan_lines: list[str],
    analysis_template_sections: list[dict[str, object]],
) -> str:
    top_impacts = []
    if not player_impact_df.empty:
        for _, row in player_impact_df.head(5).iterrows():
            top_impacts.append(f"- {row['Player']}: {row['Why']}")

    sections = [
        f"# Arsenal Match Report",
        "",
        f"## Match",
        f"- Competition: {selected_match['competition']}",
        f"- Opponent: {selected_match['opponent']}",
        f"- Score: {selected_match['score']}",
        f"- Result: {selected_match['result']}",
        "",
        "## Executive Summary",
        *[f"- {line}" for line in review_lines],
        "",
        build_analysis_template_markdown(analysis_template_sections),
        "",
        "## Arsenal Performance",
        f"- Arsenal xG: {shot_profile['xg']:.2f}",
        f"- Opponent xG: {opp_shot_profile['xg']:.2f}",
        f"- Open play xG: {shot_profile['open_play_xg']:.2f}",
        f"- Set-piece xG: {shot_profile['set_piece_xg']:.2f}",
        f"- Central shots: {shot_profile['central_shots']}",
        f"- Final-third passes: {tactical_summary['final_third_passes']:.0f}",
        f"- Field tilt proxy: {control_profile['field_tilt_proxy']:.0f}%",
        "",
        "## Attack Review",
        *[f"- {line}" for line in attack_review_lines],
        "",
        "## Defensive Review",
        *[f"- {line}" for line in defensive_review_lines],
        "",
        "## Opponent Possession Review",
        *[f"- {line}" for line in opponent_possession_review_lines],
        "",
        "## Territory And Zone Access",
        f"- Arsenal Zone 14 entries: {arsenal_zone_profile['zone14_entries']}",
        f"- Arsenal central box shots: {arsenal_zone_profile['central_box_shots']}",
        f"- Arsenal left half-space shots: {arsenal_zone_profile['left_half_space_shots']}",
        f"- Arsenal right half-space shots: {arsenal_zone_profile['right_half_space_shots']}",
        f"- Opponent Zone 14 entries: {opponent_zone_profile['zone14_entries']}",
        f"- Opponent central box shots: {opponent_zone_profile['central_box_shots']}",
        "",
        "## Match Flow",
        *[f"- {line}" for line in match_swing_notes],
        "",
        "## Half-by-Half Adjustments",
        *[f"- {line}" for line in phase_comparison_notes],
        "",
        "## Why Arsenal Had The Edge",
        *([f"- {line}" for line in arsenal_edges] if arsenal_edges else ["- No clear single dominant edge; this was decided by small margins."]),
        "",
        "## Why The Opponent Was Dangerous",
        *([f"- {line}" for line in opponent_edges] if opponent_edges else ["- Opponent threat remained limited for most of the match."]),
        "",
        "## Structural Diagnosis",
        *[f"- {line}" for line in structural_summary_lines],
        "",
        "## Key Player",
        f"- {key_player_name}",
        *[f"- {line}" for line in key_player_reasons],
        "",
        "## Coach Takeaways",
        f"- {coach_takeaways['next_up']}",
        *[f"- Continue: {line}" for line in coach_takeaways["continue"]],
        *[f"- Change: {line}" for line in coach_takeaways["change"]],
        *[f"- Selection: {line}" for line in coach_takeaways["selection"]],
        *[f"- Plan: {line}" for line in opponent_game_plan_lines],
        "",
        "## Impact Ranking",
        *(top_impacts if top_impacts else ["- Player impact ranking unavailable for this match."]),
        "",
    ]
    return "\n".join(sections)


def build_x_post_pack(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    match_swing_notes: list[str],
    arsenal_edges: list[str],
    opponent_edges: list[str],
    key_player_name: str,
    match_how_line: str,
    match_why_line: str,
    match_missing_line: str,
    control_room_lines: list[str],
) -> str:
    opponent = selected_match["opponent"]
    score = selected_match["score"]
    competition = selected_match["competition"]
    strongest_edge = arsenal_edges[0] if arsenal_edges else match_why_line
    main_risk = opponent_edges[0] if opponent_edges else match_missing_line
    swing = match_swing_notes[0] if match_swing_notes else "流れの転換点はショットデータ上では限定的。"
    control_note = control_room_lines[0] if control_room_lines else "構造的な優位は複数要素の合算で判断。"

    single_post = (
        f"Arsenal {score} {opponent} ({competition})\n"
        f"xG {shot_profile['xg']:.2f}-{opp_shot_profile['xg']:.2f} / Field tilt proxy {control_profile['field_tilt_proxy']:.0f}%\n"
        f"勝敗を分けたのは {strongest_edge}。キーマンは {key_player_name}。\n"
        f"#Arsenal #COYG"
    )
    thread = [
        f"1/ Arsenal {score} {opponent}。まず全体像はこれ。\n{match_how_line}\n\nxG: {shot_profile['xg']:.2f}-{opp_shot_profile['xg']:.2f}",
        f"2/ 勝敗の分岐点。\n{match_why_line}\n\nSignal: {strongest_edge}",
        f"3/ 試合の流れ。\n{swing}\n\nFinal-third passes: {tactical_summary['final_third_passes']:.0f}",
        f"4/ 構造的に見た優位。\n{control_note}\nCentral shots: {shot_profile['central_shots']} / Opp central shots: {opp_shot_profile['central_shots']}",
        f"5/ 修正点。\n{main_risk}\n\n次戦に向けては、機能した構造を残しつつこのリスクを消したい。",
    ]
    data_card = [
        "DATA CARD",
        f"Match: Arsenal vs {opponent}",
        f"Competition: {competition}",
        f"Score: {score}",
        f"xG: Arsenal {shot_profile['xg']:.2f} - Opponent {opp_shot_profile['xg']:.2f}",
        f"Open-play xG: {shot_profile['open_play_xg']:.2f}",
        f"Set-piece xG: {shot_profile['set_piece_xg']:.2f}",
        f"Central shots: {shot_profile['central_shots']} - {opp_shot_profile['central_shots']}",
        f"Final-third passes: {tactical_summary['final_third_passes']:.0f}",
        f"Field tilt proxy: {control_profile['field_tilt_proxy']:.0f}%",
        f"Key player: {key_player_name}",
    ]
    sections = [
        "SINGLE POST",
        single_post,
        "",
        "THREAD DRAFT",
        *thread,
        "",
        *data_card,
    ]
    return "\n\n".join(sections)


def build_coach_takeaways(
    selected_match: pd.Series,
    next_match: dict | None,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    defensive_review_lines: list[str],
    attack_review_lines: list[str],
    key_player_name: str,
    player_impact_df: pd.DataFrame,
) -> dict[str, list[str] | str]:
    continue_items: list[str] = []
    change_items: list[str] = []
    selection_items: list[str] = []

    if shot_profile["central_shots"] >= 3:
        continue_items.append("中央侵入は継続価値があります。ボックス中央へ入る形は次戦でも再現したいです。")
    if tactical_summary["final_third_passes"] >= 25:
        continue_items.append("相手陣での定着と前進量は維持したいポイントです。")
    if control_profile["field_tilt_proxy"] >= 55:
        continue_items.append("主導権を握る押し込み構造は維持し、試合の入りから再現したいです。")
    if shot_profile["set_piece_xg"] >= 0.25:
        continue_items.append("セットプレーの攻撃価値は次戦も武器として残せます。")

    if shot_profile["xg"] < 1.0:
        change_items.append("チャンス総量が不足しているので、中央経由の崩しとボックス内の人数を増やしたいです。")
    if opp_shot_profile["central_shots"] >= 3:
        change_items.append("中央の守備管理を修正し、相手に最も危険なエリアを使わせないことが優先です。")
    if opp_shot_profile["set_piece_xg"] >= 0.3:
        change_items.append("セットプレー守備は明確な修正対象です。マークとセカンド回収を再確認したいです。")
    if tactical_summary["rest_defence_count"] <= 2:
        change_items.append("保持時の後方枚数が薄いので、トランジション耐性を上げる配置修正が必要です。")

    selection_items.append(f"{key_player_name} は次戦でも中心に据えたい選手です。")
    if not player_impact_df.empty:
        for _, row in player_impact_df.head(3).iterrows():
            if row["Player"] == key_player_name:
                continue
            selection_items.append(f"{row['Player']} は起用価値が高く、試合への関与量が大きかったです。")
            if len(selection_items) >= 3:
                break

    next_up = "Next opponent unavailable."
    if next_match:
        next_up = (
            f"次戦は {next_match['opponent']['name']} 戦。"
            f" {normalize_competition(next_match['tournament']['name'])} に向けて今回の示唆を転用します。"
        )

    if not continue_items:
        continue_items.append("大きな再現ポイントは限定的で、試合ごとの微調整が必要です。")
    if not change_items:
        change_items.append("大きな修正点は少なく、仕上げと試合管理の精度を高める段階です。")

    return {
        "next_up": next_up,
        "continue": continue_items[:4],
        "change": change_items[:4],
        "selection": selection_items[:4],
        "staff_note": f"{selected_match['opponent']} 戦の内容を次戦準備へ直結させるための監督メモです。",
    }


def build_structural_diagnosis(
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
    score_state_df: pd.DataFrame,
    relationship_links_df: pd.DataFrame,
    relationship_hubs_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, object]] = []

    attack_score = (
        (shot_profile["xg"] - opp_shot_profile["xg"]) * 20
        + (shot_profile["central_shots"] - opp_shot_profile["central_shots"]) * 8
        + (tactical_summary["final_third_passes"] - 20) * 1.2
    )
    attack_signal = (
        f"xG {shot_profile['xg']:.2f} vs {opp_shot_profile['xg']:.2f}, "
        f"central shots {shot_profile['central_shots']} vs {opp_shot_profile['central_shots']}"
    )
    attack_reason = "チャンス質と中央攻略の差が、最終結果を直接動かした可能性。"
    rows.append({"Factor": "Attack Structure", "Score": round(attack_score, 1), "Signal": attack_signal, "Why": attack_reason})

    defence_score = (
        (1.2 - opp_shot_profile["xg"]) * 18
        - opponent_zone_profile["zone14_entries"] * 6
        - opp_shot_profile["central_shots"] * 5
        + tactical_summary["rest_defence_count"] * 4
    )
    defence_signal = (
        f"opp xG {opp_shot_profile['xg']:.2f}, "
        f"opp Zone 14 {opponent_zone_profile['zone14_entries']}, opp central shots {opp_shot_profile['central_shots']}"
    )
    defence_reason = "相手の中央侵入と危険地帯管理が、守備の安定性を左右した可能性。"
    rows.append({"Factor": "Defensive Structure", "Score": round(defence_score, 1), "Signal": defence_signal, "Why": defence_reason})

    game_state_score = 0.0
    game_state_signal = "Limited score-state data"
    if not score_state_df.empty:
        arsenal_level = score_state_df[(score_state_df["State"] == "Level") & (score_state_df["Team"] == "Arsenal")]["xG"]
        opp_level = score_state_df[(score_state_df["State"] == "Level") & (score_state_df["Team"] == "Opponent")]["xG"]
        arsenal_leading = score_state_df[(score_state_df["State"] == "Leading") & (score_state_df["Team"] == "Arsenal")]["xG"]
        opp_trailing = score_state_df[(score_state_df["State"] == "Trailing") & (score_state_df["Team"] == "Opponent")]["xG"]
        level_edge = float(arsenal_level.iloc[0]) - float(opp_level.iloc[0]) if not arsenal_level.empty and not opp_level.empty else 0.0
        lead_control = float(arsenal_leading.iloc[0]) - float(opp_trailing.iloc[0]) if not arsenal_leading.empty and not opp_trailing.empty else 0.0
        game_state_score = level_edge * 20 + lead_control * 14
        game_state_signal = f"level-state edge {level_edge:+.2f}, lead-control {lead_control:+.2f}"
    game_state_reason = "同点時とリード後の試合運びが、構造的な主導権の差として表れた可能性。"
    rows.append({"Factor": "Game State Control", "Score": round(game_state_score, 1), "Signal": game_state_signal, "Why": game_state_reason})

    relationship_score = 0.0
    relationship_signal = "No strong passing hubs available"
    if not relationship_hubs_df.empty:
        top_hub = relationship_hubs_df.iloc[0]
        top_link = relationship_links_df.iloc[0]["Pair"] if not relationship_links_df.empty else "No dominant pair"
        relationship_score = float(top_hub["Hub Score"]) * 6
        relationship_signal = f"top hub {top_hub['Player']} ({top_hub['Hub Score']:.2f}), top link {top_link}"
    relationship_reason = "選手間の関係性とハブの存在が、前進と再現性を支えた可能性。"
    rows.append({"Factor": "Player Structure", "Score": round(relationship_score, 1), "Signal": relationship_signal, "Why": relationship_reason})

    territory_score = (
        (control_profile["field_tilt_proxy"] - 50) * 1.6
        + arsenal_zone_profile["zone14_entries"] * 4
        - opponent_zone_profile["zone14_entries"] * 4
    )
    territory_signal = (
        f"field tilt {control_profile['field_tilt_proxy']:.0f}%, "
        f"Zone 14 {arsenal_zone_profile['zone14_entries']} vs {opponent_zone_profile['zone14_entries']}"
    )
    territory_reason = "どこでプレーされたかが、結果の前提条件として効いた可能性。"
    rows.append({"Factor": "Territory Structure", "Score": round(territory_score, 1), "Signal": territory_signal, "Why": territory_reason})

    diagnosis_df = pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)
    summary_lines = []
    if not diagnosis_df.empty:
        top_factor = diagnosis_df.iloc[0]
        bottom_factor = diagnosis_df.iloc[-1]
        summary_lines.append(f"最も結果を押した構造要因は {top_factor['Factor']} で、signal は {top_factor['Signal']} です。")
        summary_lines.append(f"最も脆かった構造要因は {bottom_factor['Factor']} で、signal は {bottom_factor['Signal']} です。")
        positive_factors = diagnosis_df[diagnosis_df["Score"] > 0]["Factor"].tolist()
        if positive_factors:
            summary_lines.append(f"優位だった構造要因: {', '.join(positive_factors[:3])}")
        negative_factors = diagnosis_df[diagnosis_df["Score"] < 0]["Factor"].tolist()
        if negative_factors:
            summary_lines.append(f"弱点になった構造要因: {', '.join(negative_factors[:3])}")
    return diagnosis_df, summary_lines[:4]


def create_structural_diagnosis_chart(diagnosis_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        diagnosis_df,
        x="Factor",
        y="Score",
        color="Score",
        color_continuous_scale=[[0, "#93C5FD"], [0.5, "#FFE8A3"], [1, ARSENAL_RED]],
        text_auto=".1f",
    )
    fig = base_chart_layout(fig, height=320)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Structural impact score", gridcolor="rgba(159,176,196,0.14)")
    fig.update_layout(coloraxis_showscale=False)
    return fig


def build_match_verdict(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    control_profile: dict[str, float],
    review_lines: list[str],
    defensive_review_lines: list[str],
    key_player_name: str,
) -> tuple[str, str, str]:
    if shot_profile["xg"] - opp_shot_profile["xg"] >= 0.4 and control_profile["field_tilt_proxy"] >= 55:
        how = "Arsenal は全体として押し込みながら、より質の高いチャンスを作れた試合でした。"
    elif opp_shot_profile["xg"] - shot_profile["xg"] >= 0.4:
        how = "Arsenal は試合全体では押し返される時間があり、相手の方が危険な局面を多く作っていました。"
    else:
        how = "Arsenal は拮抗した試合を戦っていて、主導権は時間帯ごとに入れ替わる展開でした。"

    why = review_lines[0] if review_lines else f"結果は {selected_match['result']} でした。"

    if shot_profile["central_shots"] < 3 and tactical_summary["final_third_passes"] < 20:
        missing = "足りなかったのは、相手陣での定着から中央へ差し込む質です。前進量も中央攻略ももう一段必要でした。"
    elif opp_shot_profile["central_shots"] >= 3:
        missing = "足りなかったのは、危険地帯の守備管理です。相手の中央アクセスをもう少し抑える必要がありました。"
    elif shot_profile["big_chances"] == 0 and shot_profile["xg"] < 1.0:
        missing = "足りなかったのは、決定機の総量です。良い形はあっても、試合を決めるだけの高品質チャンスが不足していました。"
    else:
        missing = f"足りなかったのは、優位をより確実に結果へ変える仕上げの部分です。キープレイヤーは {key_player_name} でしたが、周辺の再現性をさらに高めたい試合でした。"

    return how, why, missing


def build_analyst_snapshot(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
) -> list[str]:
    lines = []
    lines.append(
        f"{selected_match['opponent']} 戦は {selected_match['score']}。Arsenal の xG は {shot_profile['xg']:.2f}、相手は {opp_shot_profile['xg']:.2f}。"
    )
    lines.append(
        f"Arsenal は central shots {shot_profile['central_shots']} 本、Zone 14 {arsenal_zone_profile['zone14_entries']} 回、"
        f"final-third passes {tactical_summary['final_third_passes']:.0f} 本。"
    )
    lines.append(
        f"相手には central shots {opp_shot_profile['central_shots']} 本、Zone 14 {opponent_zone_profile['zone14_entries']} 回を許していました。"
    )
    if tactical_summary["right_lane_bias"] >= 58:
        lines.append("攻撃は右レーン寄りで、片側優勢の構図が強い試合でした。")
    elif tactical_summary["right_lane_bias"] <= 42 and shot_profile["shots"] > 0:
        lines.append("右偏重ではなく、比較的バランスよくフィニッシュ地点を散らせています。")
    else:
        lines.append("レーン配分は中庸で、中央進入の質が結果により強く影響した試合でした。")
    return lines


def build_match_context_bundle(
    selected_match: pd.Series,
    shot_profile: dict[str, float],
    opp_shot_profile: dict[str, float],
    tactical_summary: dict[str, float],
    arsenal_zone_profile: dict[str, int],
    opponent_zone_profile: dict[str, int],
    arsenal_edges: list[str],
    opponent_edges: list[str],
    match_swing_notes: list[str],
    review_lines: list[str],
    control_profile: dict[str, float],
    defensive_review_lines: list[str],
    score_state_df: pd.DataFrame,
    relationship_links_df: pd.DataFrame,
    relationship_hubs_df: pd.DataFrame,
    attack_review_lines: list[str],
    opponent_possession_review_lines: list[str],
    player_impact_df: pd.DataFrame,
    structural_diagnosis_df: pd.DataFrame,
    structural_summary_lines: list[str],
    phase_comparison_notes: list[str],
    role_profile_df: pd.DataFrame,
    opponent_game_plan_lines: list[str],
    analysis_template_sections: list[dict[str, object]],
    recent_form_string: str,
    selected_record: str,
    key_player_name: str,
    key_player_reasons: list[str],
    match_how_line: str,
    match_why_line: str,
    match_missing_line: str,
    zone_threat_df: pd.DataFrame,
    possession_wave_df: pd.DataFrame,
    pressing_profile_df: pd.DataFrame,
    pressing_profile_lines: list[str],
    build_up_structure_df: pd.DataFrame,
    build_up_structure_lines: list[str],
    control_room_lines: list[str],
) -> dict[str, object]:
    return {
        "opponent": selected_match["opponent"],
        "competition": selected_match["competition"],
        "score": selected_match["score"],
        "result": selected_match["result"],
        "shot_profile": shot_profile,
        "opp_shot_profile": opp_shot_profile,
        "tactical_summary": tactical_summary,
        "arsenal_zone_profile": arsenal_zone_profile,
        "opponent_zone_profile": opponent_zone_profile,
        "arsenal_edges": arsenal_edges,
        "opponent_edges": opponent_edges,
        "match_swing_notes": match_swing_notes,
        "review_lines": review_lines,
        "control_profile": control_profile,
        "defensive_review_lines": defensive_review_lines,
        "score_state_df": score_state_df,
        "relationship_links_df": relationship_links_df,
        "relationship_hubs_df": relationship_hubs_df,
        "attack_review_lines": attack_review_lines,
        "opponent_possession_review_lines": opponent_possession_review_lines,
        "player_impact_df": player_impact_df,
        "structural_diagnosis_df": structural_diagnosis_df,
        "structural_summary_lines": structural_summary_lines,
        "phase_comparison_notes": phase_comparison_notes,
        "role_profile_df": role_profile_df,
        "opponent_game_plan_lines": opponent_game_plan_lines,
        "analysis_template_sections": analysis_template_sections,
        "recent_form_string": recent_form_string,
        "selected_record": selected_record,
        "key_player_name": key_player_name,
        "key_player_reasons": key_player_reasons,
        "match_how_line": match_how_line,
        "match_why_line": match_why_line,
        "match_missing_line": match_missing_line,
        "zone_threat_df": zone_threat_df,
        "possession_wave_df": possession_wave_df,
        "pressing_profile_df": pressing_profile_df,
        "pressing_profile_lines": pressing_profile_lines,
        "build_up_structure_df": build_up_structure_df,
        "build_up_structure_lines": build_up_structure_lines,
        "control_room_lines": control_room_lines,
    }


def generate_analyst_answer(question: str, context: dict[str, object]) -> str:
    q = question.lower()
    shot_profile = context["shot_profile"]
    opp_shot_profile = context["opp_shot_profile"]
    tactical_summary = context["tactical_summary"]
    arsenal_zone_profile = context["arsenal_zone_profile"]
    opponent_zone_profile = context["opponent_zone_profile"]
    arsenal_edges = context["arsenal_edges"]
    opponent_edges = context["opponent_edges"]
    match_swing_notes = context["match_swing_notes"]
    review_lines = context["review_lines"]
    control_profile = context["control_profile"]
    defensive_review_lines = context["defensive_review_lines"]
    score_state_df = context["score_state_df"]
    relationship_links_df = context["relationship_links_df"]
    relationship_hubs_df = context["relationship_hubs_df"]
    attack_review_lines = context["attack_review_lines"]
    opponent_possession_review_lines = context["opponent_possession_review_lines"]
    player_impact_df = context["player_impact_df"]
    structural_diagnosis_df = context["structural_diagnosis_df"]
    structural_summary_lines = context["structural_summary_lines"]
    phase_comparison_notes = context["phase_comparison_notes"]
    role_profile_df = context["role_profile_df"]
    opponent_game_plan_lines = context["opponent_game_plan_lines"]
    analysis_template_sections = context["analysis_template_sections"]
    recent_form_string = context["recent_form_string"]
    selected_record = context["selected_record"]
    key_player_name = context["key_player_name"]
    key_player_reasons = context["key_player_reasons"]
    match_how_line = context["match_how_line"]
    match_why_line = context["match_why_line"]
    match_missing_line = context["match_missing_line"]
    zone_threat_df = context["zone_threat_df"]
    possession_wave_df = context["possession_wave_df"]
    pressing_profile_df = context["pressing_profile_df"]
    pressing_profile_lines = context["pressing_profile_lines"]
    build_up_structure_df = context["build_up_structure_df"]
    build_up_structure_lines = context["build_up_structure_lines"]
    control_room_lines = context["control_room_lines"]
    opponent = context["opponent"]
    result = context["result"]
    score = context["score"]

    if any(token in q for token in ["form", "record", "points", "フォーム", "ポイント"]):
        return "\n".join(
            [
                "この画面では、曖昧な points 表示はやめています。",
                f"- Recent Form: {recent_form_string} で、直近試合の並びです。W=win, D=draw, L=loss。",
                f"- Selected Record: {selected_record} で、今の competition filter に入っている試合群の通算 W-D-L です。",
            ]
        )

    if any(token in q for token in ["なぜ勝", "勝因", "why win", "why won", "won"]):
        lines = [f"{opponent} 戦を {score} で終えた中で、勝因として強いのは次の点です。"]
        lines.extend([f"- {item}" for item in (arsenal_edges or review_lines[:3])[:4]])
        return "\n".join(lines)

    if any(token in q for token in ["敗因", "なぜ負", "why lose", "why lost", "失点", "苦し"]):
        lines = [f"{result} になった要因や危険だった部分は次の通りです。"]
        lines.extend([f"- {item}" for item in (opponent_edges or match_swing_notes[:2])[:4]])
        return "\n".join(lines)

    if any(token in q for token in ["xg", "流れ", "swing", "momentum", "主導権", "時間帯"]):
        return "\n".join(
            [
                f"xG ベースでは Arsenal {shot_profile['xg']:.2f} - {opp_shot_profile['xg']:.2f} {opponent} でした。",
                *[f"- {item}" for item in match_swing_notes[:3]],
            ]
        )

    if any(token in q for token in ["xt", "threat", "脅威", "どこで優位", "優位ゾーン", "関与", "contributor", "builder"]):
        lines = ["Threat Zones の読み方です。"]
        if isinstance(zone_threat_df, pd.DataFrame) and not zone_threat_df.empty:
            for _, row in zone_threat_df.sort_values("Threat", ascending=False).head(3).iterrows():
                lines.append(
                    f"- {row['Zone']}: Threat {row['Threat']:.2f} / builder {row.get('Primary Builder', 'N/A')} / contributors {row.get('Top Contributors', 'N/A')} / shooter {row.get('Main Shooter', 'N/A')}"
                )
        return "\n".join(lines)

    if any(token in q for token in ["wave", "possession", "ポゼッション", "攻撃の波", "局面"]):
        lines = ["攻撃の波を見ます。"]
        if isinstance(possession_wave_df, pd.DataFrame) and not possession_wave_df.empty:
            for _, row in possession_wave_df.sort_values("xG", ascending=False).head(4).iterrows():
                lines.append(f"- {row['Minutes']}: {row['Signal']} / {row['xG']:.2f} xG / main player {row['Main Player']}")
        else:
            lines.append("- シュート連続性が少なく、明確な攻撃の波は検出できません。")
        return "\n".join(lines)

    if any(token in q for token in ["press", "pressing", "プレッシング", "奪回", "ハイプレス"]):
        lines = ["プレッシングの読みです。"]
        lines.extend([f"- {item}" for item in pressing_profile_lines[:3]])
        if isinstance(pressing_profile_df, pd.DataFrame) and not pressing_profile_df.empty:
            for _, row in pressing_profile_df.sort_values("Score", ascending=False).head(2).iterrows():
                lines.append(f"- {row['Metric']}: {row['Score']:.0f}/100 ({row['Signal']})")
        return "\n".join(lines)

    if any(token in q for token in ["build", "build-up", "ビルドアップ", "配置", "保持時"]):
        lines = ["ビルドアップ構造の読みです。"]
        lines.extend([f"- {item}" for item in build_up_structure_lines[:3]])
        if isinstance(build_up_structure_df, pd.DataFrame) and not build_up_structure_df.empty:
            progressors = build_up_structure_df.sort_values("Final-third Passes", ascending=False).head(3)
            for _, row in progressors.iterrows():
                lines.append(f"- {row['Player']}: {row['Line']} / {row['Lane']} / final-third passes {row['Final-third Passes']}")
        return "\n".join(lines)

    if any(token in q for token in ["zone", "中央", "half-space", "レーン", "box"]):
        return "\n".join(
            [
                "進入経路の整理です。",
                f"- Arsenal: Zone 14 {arsenal_zone_profile['zone14_entries']} / Central box {arsenal_zone_profile['central_box_shots']} / "
                f"LHS {arsenal_zone_profile['left_half_space_shots']} / RHS {arsenal_zone_profile['right_half_space_shots']}",
                f"- Opponent: Zone 14 {opponent_zone_profile['zone14_entries']} / Central box {opponent_zone_profile['central_box_shots']} / "
                f"LHS {opponent_zone_profile['left_half_space_shots']} / RHS {opponent_zone_profile['right_half_space_shots']}",
            ]
        )

    if any(token in q for token in ["pass", "前進", "territory", "押し込", "保持"]):
        return "\n".join(
            [
                "前進と陣地獲得の観点です。",
                f"- Final-third passes: {tactical_summary['final_third_passes']:.0f}",
                f"- Attack height: {tactical_summary['mean_attack_height']:.0f}",
                f"- Rest defence: {tactical_summary['rest_defence_count']:.0f}",
                f"- Right lane bias: {tactical_summary['right_lane_bias']:.0f}%",
                f"- Field tilt proxy: {control_profile['field_tilt_proxy']:.0f}%",
            ]
        )

    if any(token in q for token in ["守備", "defence", "defense", "防げ", "失点要因"]):
        return "\n".join(["守備レビューです。", *[f"- {item}" for item in defensive_review_lines[:4]]])

    if any(token in q for token in ["攻撃", "attack", "chance creation", "崩し", "保持攻撃"]):
        return "\n".join(["攻撃レビューです。", *[f"- {item}" for item in attack_review_lines[:4]]])

    if any(token in q for token in ["相手保持", "opponent possession", "相手はどう", "どう苦しめられた"]):
        return "\n".join(["相手保持レビューです。", *[f"- {item}" for item in opponent_possession_review_lines[:4]]])

    if any(token in q for token in ["構造", "structural", "なぜその結果", "why structurally", "要因分解"]):
        lines = ["構造的な要因分解です。"]
        lines.extend([f"- {item}" for item in control_room_lines[:4]])
        lines.extend([f"- {item}" for item in structural_summary_lines[:4]])
        if isinstance(structural_diagnosis_df, pd.DataFrame) and not structural_diagnosis_df.empty:
            for _, row in structural_diagnosis_df.head(3).iterrows():
                lines.append(f"- {row['Factor']}: {row['Signal']}")
        return "\n".join(lines)

    if any(token in q for token in ["型", "template", "cannon", "分析フォーマット", "分析の型"]):
        lines = ["この試合はこの型で読めます。"]
        for section in analysis_template_sections:
            metrics = section.get("metrics", [])
            first_signal = metrics[0] if metrics else "No signal"
            lines.append(f"- {section['section']}: {section['question']} / {first_signal}")
        return "\n".join(lines)

    if any(token in q for token in ["前半", "後半", "修正", "half", "adjustment"]):
        return "\n".join(["前後半の差です。", *[f"- {item}" for item in phase_comparison_notes[:4]]])

    if any(token in q for token in ["役割", "role", "progressor", "finisher", "connector"]):
        lines = ["役割評価です。"]
        if isinstance(role_profile_df, pd.DataFrame) and not role_profile_df.empty:
            for _, row in role_profile_df.head(5).iterrows():
                lines.append(f"- {row['Player']}: {row['Role']} ({row['Evidence']})")
        return "\n".join(lines)

    if any(token in q for token in ["次戦", "game plan", "plan", "どう準備", "preview"]):
        return "\n".join(["次戦プランです。", *[f"- {item}" for item in opponent_game_plan_lines[:5]]])

    if any(token in q for token in ["score state", "先制後", "ビハインド", "リード時", "同点時"]):
        if score_state_df.empty:
            return "スコア状態ごとのショットデータは十分にありません。"
        lines = ["スコア状態別の xG です。"]
        for _, row in score_state_df.iterrows():
            lines.append(f"- {row['State']} / {row['Team']}: {row['xG']:.2f} xG, {int(row['Shots'])} shots")
        return "\n".join(lines)

    if any(token in q for token in ["組み合わせ", "関係性", "pair", "combo", "誰と誰", "network"]):
        lines = ["選手間関係の強い組み合わせです。"]
        if not relationship_links_df.empty:
            for _, row in relationship_links_df.head(3).iterrows():
                lines.append(f"- {row['Pair']}: weight {row['Weight']:.2f}")
        if not relationship_hubs_df.empty:
            top_hub = relationship_hubs_df.iloc[0]
            lines.append(f"- 中心選手は {top_hub['Player']}。Hub score は {top_hub['Hub Score']:.2f}")
        return "\n".join(lines)

    if any(token in q for token in ["まとめ", "summary", "総括", "overall"]):
        return "\n".join(
            [
                f"{opponent} 戦の総括です。",
                f"- {match_how_line}",
                f"- {match_why_line}",
                f"- {match_missing_line}",
                f"- Arsenal xG {shot_profile['xg']:.2f} / Opponent xG {opp_shot_profile['xg']:.2f}",
            ]
        )

    if any(token in q for token in ["キープレイヤー", "key player", "誰が鍵", "mvp"]):
        lines = [f"この試合のキープレイヤー候補は {key_player_name} です。"]
        lines.extend([f"- {item}" for item in key_player_reasons[:3]])
        if not player_impact_df.empty and len(player_impact_df) > 1:
            lines.append(f"- impact ranking 2位は {player_impact_df.iloc[1]['Player']}")
        return "\n".join(lines)

    if any(token in q for token in ["足りない", "何が必要", "改善", "missing"]):
        return match_missing_line

    return "\n".join(
        [
            f"{opponent} 戦について深掘りできます。いま分かっている軸は次の通りです。",
            f"- xG: Arsenal {shot_profile['xg']:.2f} vs Opponent {opp_shot_profile['xg']:.2f}",
            f"- Central shots: {shot_profile['central_shots']} vs {opp_shot_profile['central_shots']}",
            f"- Final-third passes: {tactical_summary['final_third_passes']:.0f}",
            "- たとえば『なぜ勝てた？』『どの時間帯で優位？』『中央攻略はできていた？』のように聞くと深掘りできます。",
        ]
    )


def render_match_review(title: str, lines: list[str]) -> None:
    st.subheader(title)
    for line in lines:
        st.write(f"- {line}")


def build_player_focus_reasons(
    selected_player: str,
    key_player_name: str,
    key_player_reasons: list[str],
    player_deep_dive: dict[str, object],
    player_impact_df: pd.DataFrame,
) -> list[str]:
    if selected_player == key_player_name and key_player_reasons:
        return key_player_reasons

    reasons: list[str] = []
    if not player_impact_df.empty:
        impact_row = player_impact_df[player_impact_df["Player"] == selected_player]
        if not impact_row.empty:
            why = impact_row.iloc[0].get("Why")
            if why:
                reasons.append(str(why))

    final_third = int(player_deep_dive.get("final_third_passes", 0))
    touches = int(player_deep_dive.get("touches", 0))
    shots = int(player_deep_dive.get("shots", 0))
    xg = float(player_deep_dive.get("xg", 0.0))
    recoveries = int(player_deep_dive.get("recoveries", 0))
    hub_score = float(player_deep_dive.get("hub_score", 0.0))

    if final_third:
        reasons.append(f"Final-third passes {final_third} 本で、前進や敵陣侵入に関与しています。")
    if touches:
        reasons.append(f"Touches {touches} 回で、この試合の関与量を確認できます。")
    if shots or xg:
        reasons.append(f"Shots {shots} 本、xG {xg:.2f} でフィニッシュ局面への関与があります。")
    if recoveries:
        reasons.append(f"Recoveries {recoveries} 回で、非保持・トランジション面にも関与しています。")
    if hub_score:
        reasons.append(f"Hub Score {hub_score:.2f} で、パスネットワーク内の接続点としての重要度があります。")
    if not reasons:
        reasons.append("この選手の詳細スタッツは限定的ですが、下のPlayer Deep Diveで個別確認できます。")
    return reasons[:4]


def render_player_focus_card(
    selected_player: str,
    key_player_name: str,
    key_player_reasons: list[str],
    player_deep_dive: dict[str, object],
    player_impact_df: pd.DataFrame,
) -> None:
    st.metric("選択中の選手", selected_player)
    if selected_player != key_player_name:
        st.caption(f"モデル上のキープレイヤー: {key_player_name}。現在はクリックした選手の詳細に切り替えています。")
    metrics = st.columns(3)
    metrics[0].metric("評価点", player_deep_dive.get("rating") or "N/A")
    metrics[1].metric("タッチ数", player_deep_dive.get("touches", 0))
    metrics[2].metric("xG", f"{float(player_deep_dive.get('xg', 0.0)):.2f}")
    metrics = st.columns(3)
    metrics[0].metric("ファイナルサードへのパス", player_deep_dive.get("final_third_passes", 0))
    metrics[1].metric("回収", player_deep_dive.get("recoveries", 0))
    metrics[2].metric("ハブスコア", f"{float(player_deep_dive.get('hub_score', 0.0)):.2f}")
    for line in build_player_focus_reasons(
        selected_player,
        key_player_name,
        key_player_reasons,
        player_deep_dive,
        player_impact_df,
    ):
        st.write(f"- {line}")


def build_phase_split(shot_df: pd.DataFrame, team_label: str) -> pd.DataFrame:
    if shot_df.empty:
        return pd.DataFrame(columns=["Phase", "Team", "Shots", "xG"])
    phases = [("0-30", 0, 30), ("31-60", 31, 60), ("61-90+", 61, 130)]
    frame = shot_df.copy()
    frame["minute_num"] = frame["minute"].apply(lambda value: int(numeric_or_default(value)))
    frame["xg_num"] = frame["xg"].apply(numeric_or_default)
    rows = []
    for label, start, end in phases:
        phase_df = frame[frame["minute_num"].between(start, end)]
        rows.append({"Phase": label, "Team": team_label, "Shots": int(len(phase_df)), "xG": float(phase_df["xg_num"].sum())})
    return pd.DataFrame(rows)


def create_phase_split_chart(arsenal_phase_df: pd.DataFrame, opponent_phase_df: pd.DataFrame) -> go.Figure:
    combined = pd.concat([arsenal_phase_df, opponent_phase_df], ignore_index=True)
    fig = px.bar(
        combined,
        x="Phase",
        y="xG",
        color="Team",
        barmode="group",
        text_auto=".2f",
        color_discrete_map={"Arsenal": ARSENAL_RED, "Opponent": "#93C5FD"},
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="xG by phase", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_zone_profile(shot_df: pd.DataFrame) -> dict[str, int]:
    if shot_df.empty:
        return {"zone14_entries": 0, "left_half_space_shots": 0, "right_half_space_shots": 0, "central_box_shots": 0}
    zone14 = shot_df[(shot_df["x"].between(85, 100)) & (shot_df["y"].between(30, 50))]
    left_half = shot_df[(shot_df["x"].between(84, 110)) & (shot_df["y"].between(50, 68))]
    right_half = shot_df[(shot_df["x"].between(84, 110)) & (shot_df["y"].between(12, 30))]
    central_box = shot_df[(shot_df["x"] >= 102) & (shot_df["y"].between(24, 56))]
    return {
        "zone14_entries": int(len(zone14)),
        "left_half_space_shots": int(len(left_half)),
        "right_half_space_shots": int(len(right_half)),
        "central_box_shots": int(len(central_box)),
    }


def build_review_history(matches_df: pd.DataFrame) -> pd.DataFrame:
    completed = matches_df[matches_df["finished"]].copy().sort_values("date", ascending=False).head(8)
    if completed.empty:
        return pd.DataFrame(columns=["Date", "Competition", "Opponent", "Score", "Result"])
    return pd.DataFrame(
        {
            "Date": completed["date"].dt.strftime("%d %b %Y"),
            "Competition": completed["competition"],
            "Opponent": completed["opponent"],
            "Score": completed["score"],
            "Result": completed["result"],
        }
    )


def create_final_third_access_chart(player_df: pd.DataFrame) -> go.Figure:
    starters = player_df[player_df["role"] != "Unavailable"].copy()
    starters["passes_into_final_third_num"] = starters["passes_into_final_third"].apply(numeric_or_default)
    starters = starters.sort_values("passes_into_final_third_num", ascending=False).head(8)
    fig = px.bar(
        starters,
        x="player",
        y="passes_into_final_third_num",
        color="role",
        color_discrete_sequence=[ARSENAL_GOLD, "#94A3B8"],
    )
    fig = base_chart_layout(fig, height=300)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Final-third passes", gridcolor="rgba(159,176,196,0.14)")
    return fig


def build_pass_network_edges(starters: pd.DataFrame) -> list[tuple[pd.Series, pd.Series, float]]:
    edges: list[tuple[pd.Series, pd.Series, float]] = []
    if len(starters) < 2:
        return edges
    for left, right in combinations(starters.to_dict("records"), 2):
        dx = abs(left["pitch_x"] - right["pitch_x"])
        dy = abs(left["pitch_y"] - right["pitch_y"])
        same_band = abs(left["x"] - right["x"]) < 0.05
        if dx > 46 or dy > 28 or same_band:
            continue
        pass_volume = numeric_or_default(left.get("accurate_passes")) + numeric_or_default(right.get("accurate_passes"))
        final_third = numeric_or_default(left.get("passes_into_final_third")) + numeric_or_default(right.get("passes_into_final_third"))
        touches = numeric_or_default(left.get("touches")) + numeric_or_default(right.get("touches"))
        closeness = max(0.35, 1.0 - ((dx / 70) + (dy / 50)) / 2)
        weight = ((pass_volume / 18) + (final_third / 5.5) + (touches / 40)) * closeness
        if pd.isna(weight) or weight < 1.2:
            continue
        edges.append((pd.Series(left), pd.Series(right), min(weight, 7.0)))
    return edges


def create_pass_map(player_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=500,
    )
    add_pitch_shapes(fig)
    starters = build_pitch_positions(player_df[player_df["role"] == "Starter"])
    starters["accurate_passes_num"] = starters["accurate_passes"].apply(numeric_or_default)
    starters["passes_into_final_third_num"] = starters["passes_into_final_third"].apply(numeric_or_default)
    starters["touches_num"] = starters["touches"].apply(numeric_or_default)
    for left, right, weight in build_pass_network_edges(starters):
        fig.add_trace(
            go.Scatter(
                x=[left["pitch_x"], right["pitch_x"]],
                y=[left["pitch_y"], right["pitch_y"]],
                mode="lines",
                line=dict(color="rgba(245,196,81,0.42)", width=weight),
                hovertemplate=(
                    f"<b>{left['player']} ↔ {right['player']}</b><br>"
                    f"Estimated relation weight: {weight:.1f}<br>"
                    f"Accurate passes: {numeric_or_default(left.get('accurate_passes')) + numeric_or_default(right.get('accurate_passes')):.0f}<br>"
                    f"Final-third passes: {numeric_or_default(left.get('passes_into_final_third')) + numeric_or_default(right.get('passes_into_final_third')):.0f}"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )
    if not starters.empty:
        fig.add_trace(
            go.Scatter(
                x=starters["pitch_x"],
                y=starters["pitch_y"],
                mode="markers+text",
                text=starters["player"],
                textposition="middle center",
                marker=dict(
                    size=starters["accurate_passes_num"].clip(lower=12, upper=60) / 2 + 10,
                    color=starters["passes_into_final_third_num"],
                    colorscale=[[0, "#FFE8A3"], [1, ARSENAL_RED]],
                    line=dict(color="white", width=1.2),
                    colorbar=dict(title="Final-third passes", bgcolor=PANEL_BG),
                ),
                customdata=starters[["accurate_passes_num", "passes_into_final_third_num", "touches_num"]],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Accurate passes: %{customdata[0]}<br>"
                    "Passes into final third: %{customdata[1]}<br>"
                    "Touches: %{customdata[2]}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def build_zone_threat_df(player_df: pd.DataFrame, shot_df: pd.DataFrame) -> pd.DataFrame:
    zones = [
        ("Left build", 0, 80, 53.3, 80),
        ("Central build", 0, 80, 26.7, 53.3),
        ("Right build", 0, 80, 0, 26.7),
        ("Left half-space", 80, 105, 53.3, 80),
        ("Zone 14", 80, 105, 26.7, 53.3),
        ("Right half-space", 80, 105, 0, 26.7),
        ("Left box", 105, 120, 53.3, 80),
        ("Central box", 105, 120, 26.7, 53.3),
        ("Right box", 105, 120, 0, 26.7),
    ]
    rows = []
    shots = shot_df.copy()
    if not shots.empty:
        shots["xg_num"] = shots["xg"].apply(numeric_or_default)
    pitch_players = build_pitch_positions(player_df[player_df["role"] != "Unavailable"])
    if not pitch_players.empty:
        pitch_players["pass3_num"] = pitch_players["passes_into_final_third"].apply(numeric_or_default)
        pitch_players["touches_num"] = pitch_players["touches"].apply(numeric_or_default)

    for zone, x0, x1, y0, y1 in zones:
        zone_shots = shots[(shots["x"].between(x0, x1)) & (shots["y"].between(y0, y1))] if not shots.empty else pd.DataFrame()
        zone_players = (
            pitch_players[(pitch_players["pitch_x"].between(x0, x1)) & (pitch_players["pitch_y"].between(y0, y1))]
            if not pitch_players.empty
            else pd.DataFrame()
        )
        shot_threat = float(zone_shots["xg_num"].sum()) if not zone_shots.empty else 0.0
        progression_threat = float(zone_players["pass3_num"].sum() * 0.018 + zone_players["touches_num"].sum() * 0.004) if not zone_players.empty else 0.0
        total = shot_threat + progression_threat
        contributor_text = "No clear contributor"
        builder_text = "No builder"
        shooter_text = "No shooter"
        if not zone_players.empty:
            zone_players = zone_players.copy()
            zone_players["contribution_score"] = zone_players["pass3_num"] * 1.8 + zone_players["touches_num"] * 0.35
            top_builders = zone_players.sort_values("contribution_score", ascending=False).head(3)
            contributor_text = ", ".join(
                f"{row['player']} ({row['pass3_num']:.0f} FT passes, {row['touches_num']:.0f} touches)"
                for _, row in top_builders.iterrows()
            )
            builder_text = str(top_builders.iloc[0]["player"]) if not top_builders.empty else "No builder"
        if not zone_shots.empty:
            shooter_series = zone_shots.groupby("player", dropna=False)["xg_num"].sum().sort_values(ascending=False)
            shooter_text = f"{shooter_series.index[0]} ({float(shooter_series.iloc[0]):.2f} xG)"
        rows.append(
            {
                "Zone": zone,
                "x0": x0,
                "x1": x1,
                "y0": y0,
                "y1": y1,
                "cx": (x0 + x1) / 2,
                "cy": (y0 + y1) / 2,
                "Shot xG": round(shot_threat, 2),
                "Progression proxy": round(progression_threat, 2),
                "Threat": round(total, 2),
                "Shots": int(len(zone_shots)),
                "Top Contributors": contributor_text,
                "Primary Builder": builder_text,
                "Main Shooter": shooter_text,
            }
        )
    return pd.DataFrame(rows)


def create_zone_threat_map(zone_threat_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=470,
    )
    add_pitch_shapes(fig)
    if zone_threat_df.empty:
        fig.update_xaxes(range=[-2, 122], visible=False)
        fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
        return fig
    max_threat = max(float(zone_threat_df["Threat"].max()), 0.01)
    for _, row in zone_threat_df.iterrows():
        intensity = min(0.82, 0.12 + float(row["Threat"]) / max_threat * 0.68)
        fig.add_shape(
            type="rect",
            x0=row["x0"],
            y0=row["y0"],
            x1=row["x1"],
            y1=row["y1"],
            line=dict(color="rgba(255,255,255,0.18)", width=1),
            fillcolor=f"rgba(217,4,41,{intensity:.2f})",
        )
        fig.add_annotation(
            x=row["cx"],
            y=row["cy"],
            text=f"<b>{row['Zone']}</b><br>{row['Threat']:.2f}<br>{row.get('Primary Builder', '')}",
            showarrow=False,
            font=dict(size=11, color=TEXT_MAIN),
        )
    fig.add_trace(
        go.Scatter(
            x=zone_threat_df["cx"],
            y=zone_threat_df["cy"],
            mode="markers",
            marker=dict(size=1, color="rgba(255,255,255,0)"),
            customdata=zone_threat_df[["Threat", "Shot xG", "Progression proxy", "Top Contributors", "Main Shooter"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Threat: %{customdata[0]:.2f}<br>"
                "Shot xG: %{customdata[1]:.2f}<br>"
                "Progression proxy: %{customdata[2]:.2f}<br>"
                "Builders: %{customdata[3]}<br>"
                "Shooter: %{customdata[4]}<extra></extra>"
            ),
            text=zone_threat_df["Zone"],
            showlegend=False,
        )
    )
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def build_possession_wave_df(shot_df: pd.DataFrame) -> pd.DataFrame:
    columns = ["Wave", "Minutes", "Shots", "xG", "Main Player", "Signal"]
    if shot_df.empty:
        return pd.DataFrame(columns=columns)
    frame = shot_df.copy()
    frame["minute_num"] = frame["minute"].apply(lambda value: int(numeric_or_default(value)))
    frame["xg_num"] = frame["xg"].apply(numeric_or_default)
    frame = frame.sort_values(["minute_num", "xg_num"]).reset_index(drop=True)

    waves = []
    current = []
    last_minute = None
    for _, row in frame.iterrows():
        minute = int(row["minute_num"])
        if last_minute is None or minute - last_minute <= 8:
            current.append(row)
        else:
            waves.append(current)
            current = [row]
        last_minute = minute
    if current:
        waves.append(current)

    rows = []
    for idx, wave in enumerate(waves, start=1):
        wave_df = pd.DataFrame(wave)
        start = int(wave_df["minute_num"].min())
        end = int(wave_df["minute_num"].max())
        xg = float(wave_df["xg_num"].sum())
        top_player = wave_df.groupby("player", dropna=False)["xg_num"].sum().sort_values(ascending=False).index[0]
        if xg >= 0.6:
            signal = "Decisive wave"
        elif len(wave_df) >= 3:
            signal = "Sustained pressure"
        elif xg >= 0.25:
            signal = "High-quality chance"
        else:
            signal = "Isolated shot"
        rows.append(
            {
                "Wave": f"Wave {idx}",
                "Minutes": f"{start}'-{end}'" if start != end else f"{start}'",
                "Start": start,
                "End": end,
                "Shots": int(len(wave_df)),
                "xG": round(xg, 2),
                "Main Player": top_player or "Unknown",
                "Signal": signal,
            }
        )
    return pd.DataFrame(rows).sort_values(["xG", "Shots"], ascending=False).reset_index(drop=True)


def create_possession_wave_chart(wave_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    if wave_df.empty:
        return base_chart_layout(fig, height=300)
    plot_df = wave_df.sort_values("Start").copy()
    fig.add_trace(
        go.Bar(
            x=plot_df["Minutes"],
            y=plot_df["xG"],
            marker=dict(color=plot_df["xG"], colorscale=[[0, "#FFE8A3"], [1, ARSENAL_RED]], line=dict(color="white", width=0.6)),
            text=plot_df["Signal"],
            textposition="outside",
            customdata=plot_df[["Shots", "Main Player"]],
            hovertemplate="<b>%{x}</b><br>xG: %{y:.2f}<br>Shots: %{customdata[0]}<br>Main player: %{customdata[1]}<extra></extra>",
        )
    )
    fig = base_chart_layout(fig, height=310)
    fig.update_xaxes(title="Attacking wave")
    fig.update_yaxes(title="xG in wave", gridcolor="rgba(159,176,196,0.14)")
    fig.update_layout(showlegend=False)
    return fig


def build_pressing_profile(
    player_df: pd.DataFrame,
    opp_shot_profile: dict[str, float],
    opponent_zone_profile: dict[str, int],
    event_df: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]]:
    available = player_df[player_df["role"] != "Unavailable"].copy()
    if available.empty:
        return pd.DataFrame(columns=["Metric", "Score", "Signal"]), ["プレッシング評価に使える選手データがありません。"]
    available["recoveries_num"] = available["recoveries"].apply(numeric_or_default)
    available["x_num"] = available["x"].apply(numeric_or_default)
    high_unit_recoveries = float(available[available["x_num"] >= 0.55]["recoveries_num"].sum())
    total_recoveries = float(available["recoveries_num"].sum())
    cards_against = int(len(event_df[(event_df["team"] == "Arsenal") & (event_df["event_type"] == "Card")])) if not event_df.empty else 0

    high_recovery_score = min(100, high_unit_recoveries * 9)
    central_lock_score = max(0, 100 - opponent_zone_profile["zone14_entries"] * 22 - opp_shot_profile["central_shots"] * 12)
    counterpress_score = min(100, total_recoveries * 4 + max(0, 1.2 - opp_shot_profile["xg"]) * 20)
    discipline_score = max(0, 100 - cards_against * 18)
    rows = [
        {"Metric": "High Recoveries", "Score": round(high_recovery_score, 1), "Signal": f"{high_unit_recoveries:.0f} recoveries from advanced units"},
        {"Metric": "Central Lock", "Score": round(central_lock_score, 1), "Signal": f"Opp Zone 14 {opponent_zone_profile['zone14_entries']} / central shots {opp_shot_profile['central_shots']}"},
        {"Metric": "Counterpress Safety", "Score": round(counterpress_score, 1), "Signal": f"Total recoveries {total_recoveries:.0f}, opp xG {opp_shot_profile['xg']:.2f}"},
        {"Metric": "Discipline", "Score": round(discipline_score, 1), "Signal": f"{cards_against} Arsenal cards"},
    ]
    profile_df = pd.DataFrame(rows)
    lines = []
    average = float(profile_df["Score"].mean())
    if average >= 70:
        lines.append("前からの圧力と奪回後の安全性は良好で、相手の前進をかなり制限できています。")
    elif average >= 50:
        lines.append("プレッシングは機能した時間もありますが、中央封鎖か奪回位置に改善余地があります。")
    else:
        lines.append("プレッシング強度か背後管理が不足し、相手に前進の出口を与えた可能性があります。")
    top = profile_df.sort_values("Score", ascending=False).iloc[0]
    low = profile_df.sort_values("Score").iloc[0]
    lines.append(f"最も良い信号: {top['Metric']} ({top['Signal']})")
    lines.append(f"次に修正したい信号: {low['Metric']} ({low['Signal']})")
    return profile_df, lines


def create_pressing_profile_chart(pressing_df: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        pressing_df,
        x="Metric",
        y="Score",
        color="Score",
        color_continuous_scale=[[0, "#93C5FD"], [0.55, "#FFE8A3"], [1, ARSENAL_RED]],
        text_auto=".0f",
    )
    fig = base_chart_layout(fig, height=310)
    fig.update_xaxes(title=None)
    fig.update_yaxes(title="Pressing score", range=[0, 100], gridcolor="rgba(159,176,196,0.14)")
    fig.update_layout(coloraxis_showscale=False)
    return fig


def build_build_up_structure(player_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    starters = build_pitch_positions(player_df[player_df["role"] == "Starter"])
    columns = ["Player", "Line", "Lane", "x", "y", "Touches", "Final-third Passes"]
    if starters.empty:
        return pd.DataFrame(columns=columns), ["ビルドアップ構造に使えるスタメン位置データがありません。"]
    starters["touches_num"] = starters["touches"].apply(numeric_or_default)
    starters["pass3_num"] = starters["passes_into_final_third"].apply(numeric_or_default)

    def line_label(x_value: float) -> str:
        if x_value < 40:
            return "Rest defence"
        if x_value < 68:
            return "Build-up base"
        if x_value < 92:
            return "Between lines"
        return "Front line"

    def lane_label(y_value: float) -> str:
        if y_value < 18:
            return "Right wide"
        if y_value < 32:
            return "Right half-space"
        if y_value < 48:
            return "Central"
        if y_value < 62:
            return "Left half-space"
        return "Left wide"

    starters["Line"] = starters["pitch_x"].apply(line_label)
    starters["Lane"] = starters["pitch_y"].apply(lane_label)
    structure_df = pd.DataFrame(
        {
            "Player": starters["player"],
            "Line": starters["Line"],
            "Lane": starters["Lane"],
            "x": starters["pitch_x"],
            "y": starters["pitch_y"],
            "Touches": starters["touches_num"].astype(int),
            "Final-third Passes": starters["pass3_num"].astype(int),
        }
    )
    line_counts = structure_df["Line"].value_counts()
    lane_counts = structure_df["Lane"].value_counts()
    lines = []
    rest_count = int(line_counts.get("Rest defence", 0))
    between_count = int(line_counts.get("Between lines", 0))
    front_count = int(line_counts.get("Front line", 0))
    shape = f"{rest_count}-{int(line_counts.get('Build-up base', 0))}-{between_count}-{front_count}"
    lines.append(f"保持時の配置proxyは {shape}。後方に {rest_count} 枚、ライン間/前線に {between_count + front_count} 枚を置く構造です。")
    if not lane_counts.empty:
        dominant_lane = lane_counts.idxmax()
        lines.append(f"人数が最も集まったレーンは {dominant_lane}。過負荷を作った側として見ます。")
    top_progressor = structure_df.sort_values("Final-third Passes", ascending=False).iloc[0]
    lines.append(f"前進の起点は {top_progressor['Player']}。Final-third passes {top_progressor['Final-third Passes']} 本です。")
    return structure_df, lines


def create_build_up_structure_chart(structure_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PITCH_BG,
        font=dict(color=TEXT_MAIN),
        margin=dict(l=8, r=8, t=44, b=8),
        height=470,
    )
    add_pitch_shapes(fig)
    if structure_df.empty:
        fig.update_xaxes(range=[-2, 122], visible=False)
        fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
        return fig
    line_colors = {
        "Rest defence": "#93C5FD",
        "Build-up base": "#8DD3C7",
        "Between lines": ARSENAL_GOLD,
        "Front line": ARSENAL_RED,
    }
    for line_name, group in structure_df.groupby("Line"):
        fig.add_trace(
            go.Scatter(
                x=group["x"],
                y=group["y"],
                mode="markers+text",
                name=line_name,
                text=group["Player"],
                textposition="top center",
                marker=dict(
                    size=group["Touches"].clip(lower=18, upper=70) / 2 + 10,
                    color=line_colors.get(line_name, "#CBD5E1"),
                    line=dict(color="white", width=1.2),
                    opacity=0.95,
                ),
                customdata=group[["Lane", "Touches", "Final-third Passes"]],
                hovertemplate="<b>%{text}</b><br>%{fullData.name}<br>Lane: %{customdata[0]}<br>Touches: %{customdata[1]}<br>Final-third passes: %{customdata[2]}<extra></extra>",
            )
        )
    for x_value, label in [(40, "rest defence"), (68, "build"), (92, "between lines")]:
        fig.add_shape(type="line", x0=x_value, y0=0, x1=x_value, y1=80, line=dict(color="rgba(255,255,255,0.18)", dash="dot"))
        fig.add_annotation(x=x_value + 1, y=76, text=label, showarrow=False, font=dict(size=10, color=TEXT_MUTED))
    fig.update_xaxes(range=[-2, 122], visible=False)
    fig.update_yaxes(range=[-2, 82], visible=False, scaleanchor="x", scaleratio=1)
    return fig


def build_control_room_summary(
    zone_threat_df: pd.DataFrame,
    possession_wave_df: pd.DataFrame,
    pressing_lines: list[str],
    build_up_lines: list[str],
) -> list[str]:
    lines: list[str] = []
    if not zone_threat_df.empty:
        top_zone = zone_threat_df.sort_values("Threat", ascending=False).iloc[0]
        lines.append(f"どこで優位だったか: 最大脅威ゾーンは {top_zone['Zone']}、Threat {top_zone['Threat']:.2f}。")
    if not possession_wave_df.empty:
        top_wave = possession_wave_df.sort_values("xG", ascending=False).iloc[0]
        lines.append(f"どの局面が試合を動かしたか: {top_wave['Minutes']} の {top_wave['Signal']}、{top_wave['xG']:.2f} xG。")
    if build_up_lines:
        lines.append(f"なぜ前進できた/詰まったか: {build_up_lines[0]}")
    if pressing_lines:
        lines.append(f"なぜ守れた/苦しんだか: {pressing_lines[0]}")
    return lines[:4]


def build_team_summary(matches_df: pd.DataFrame) -> dict[str, int]:
    completed = matches_df[matches_df["finished"]].copy()
    if completed.empty:
        return {"wins": 0, "draws": 0, "losses": 0, "goals": 0, "conceded": 0, "points": 0}
    wins = int((completed["result"] == "Win").sum())
    draws = int((completed["result"] == "Draw").sum())
    losses = int((completed["result"] == "Loss").sum())
    goals = int(completed["arsenal_goals"].fillna(0).sum())
    conceded = int(completed["opponent_goals"].fillna(0).sum())
    return {
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "goals": goals,
        "conceded": conceded,
        "points": wins * 3 + draws,
    }


def build_match_label(row: pd.Series) -> str:
    date_label = row["date"].strftime("%d %b %Y") if pd.notna(row["date"]) else "TBD"
    stage = f" {row['stage']}" if row.get("stage") else ""
    venue = "H" if row["venue"] == "Home" else "A"
    return f"{date_label} | {row['opponent']} | {row['competition']}{stage} | {venue}"


payload = fetch_team_payload()
matches_df = build_matches_df(payload)
top_players_df = build_top_players_df(payload)
season_player_performance_df = build_season_player_performance_df(payload, top_players_df)
injury_df = build_injury_df(payload)
news_df = build_news_df(payload)
competition_options = get_competition_options(matches_df)

if "dashboard_mode" not in st.session_state:
    st.session_state["dashboard_mode"] = "Team Analytics"

with st.sidebar:
    st.header("コマンドセンター")
    refresh_options = {
        "Off": 0,
        "5 min": 5,
        "10 min": 10,
        "15 min": 15,
        "1 hour": 60,
        "1 day": 1440,
    }
    refresh_label = st.selectbox("自動更新", options=list(refresh_options.keys()), index=5)
    refresh_minutes = refresh_options[refresh_label]
    competition_filter = st.multiselect(
        "大会",
        options=competition_options,
        default=competition_options,
    )
    view_mode = st.radio(
        "モード",
        options=["Team Analytics", "Player Analytics"],
        horizontal=True,
        key="dashboard_mode",
        format_func=lambda value: {"Team Analytics": "チーム分析", "Player Analytics": "選手分析"}.get(value, value),
    )
    layout_mode = st.radio(
        "表示形式",
        options=["Guided Story", "Full Detail"],
        index=0,
        format_func=lambda value: {"Guided Story": "文脈順に読む", "Full Detail": "詳細をすべて見る"}.get(value, value),
        help="文脈順に読む画面、または全パネルを細かく見る画面を選べます。",
    )

inject_auto_refresh(refresh_minutes * 60)

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Live Arsenal Intelligence</div>
        <div class="hero-title">Arsenal Command Center</div>
        <div class="hero-subtitle">
            A live Streamlit dashboard built around Arsenal fixtures, squad status, current player output,
            news, and lineup-driven tactical visuals. The app refreshes automatically and supports every
            competition currently present in Arsenal's latest fixture feed.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if matches_df.empty:
    st.error("Live Arsenal match data is unavailable right now. Please try again shortly.")
    st.stop()

filtered_matches = matches_df[matches_df["competition"].isin(competition_filter)].copy()
if filtered_matches.empty:
    filtered_matches = matches_df.copy()

review_history_df = build_review_history(filtered_matches)
trend_summary_df = build_trend_summary(filtered_matches)
recent_benchmark_df, recent_benchmark_notes = build_recent_results_benchmark(filtered_matches)

default_match = filtered_matches[filtered_matches["finished"]].head(1)
default_match_id = default_match["match_id"].iloc[0] if not default_match.empty else filtered_matches["match_id"].iloc[0]
selected_match_id = st.selectbox(
    "対象試合",
    options=filtered_matches["match_id"],
    index=list(filtered_matches["match_id"]).index(default_match_id),
    format_func=lambda match_id: build_match_label(filtered_matches.loc[filtered_matches["match_id"] == match_id].iloc[0]),
)
selected_match = filtered_matches.loc[filtered_matches["match_id"] == selected_match_id].iloc[0]
match_page_props = fetch_match_page_props(selected_match["page_url"])
match_heatmap_payload = fetch_match_heatmap_payload(selected_match["page_url"])
match_player_df = build_match_player_df(match_page_props, TEAM_ID)
player_df = match_player_df if not match_player_df.empty else build_player_df(payload)
shot_df = build_match_shot_df(match_page_props, TEAM_ID)
all_shot_df = build_match_shot_df(match_page_props, None)
event_df = build_event_df(match_page_props, TEAM_ID)
period_stats_df = build_period_stats_df(match_page_props, TEAM_ID)
substitution_impact_df = build_substitution_impact_df(event_df, all_shot_df, TEAM_ID)
opp_shot_df = all_shot_df[all_shot_df["team_id"] != TEAM_ID].copy() if not all_shot_df.empty else pd.DataFrame()
shot_profile = build_shot_profile(shot_df)
opp_shot_profile = build_shot_profile(opp_shot_df)
tactical_summary = build_tactical_summary(player_df, shot_df)
xg_race_df = build_xg_race_df(all_shot_df, TEAM_ID)
arsenal_phase_df = build_phase_split(shot_df, "Arsenal")
opponent_phase_df = build_phase_split(opp_shot_df, "Opponent")
arsenal_zone_profile = build_zone_profile(shot_df)
opponent_zone_profile = build_zone_profile(opp_shot_df)
arsenal_edges, opponent_edges = build_result_drivers(
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    arsenal_zone_profile,
    opponent_zone_profile,
    xg_race_df,
)
match_swing_notes = build_match_swing_notes(xg_race_df)
key_moments_df = build_key_moments_df(all_shot_df, TEAM_ID)
control_profile = build_control_profile(
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    arsenal_zone_profile,
    opponent_zone_profile,
)
defensive_review_lines = build_defensive_review(
    opp_shot_profile,
    opponent_zone_profile,
    tactical_summary,
)
score_state_df = build_score_state_df(all_shot_df, TEAM_ID)
relationship_links_df, relationship_hubs_df = build_player_relationships(player_df)
attack_review_lines = build_attack_review(
    shot_profile,
    tactical_summary,
    arsenal_zone_profile,
    control_profile,
)
opponent_possession_review_lines = build_opponent_possession_review(
    opp_shot_profile,
    opponent_zone_profile,
    control_profile,
)
player_impact_df = build_player_impact_df(player_df)
structural_diagnosis_df, structural_summary_lines = build_structural_diagnosis(
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    arsenal_zone_profile,
    opponent_zone_profile,
    score_state_df,
    relationship_links_df,
    relationship_hubs_df,
)
phase_comparison_df, phase_comparison_notes = build_phase_comparison_summary(shot_df, opp_shot_df)
role_profile_df = build_role_profile_df(player_df, shot_df, relationship_hubs_df)
zone_threat_df = build_zone_threat_df(player_df, shot_df)
possession_wave_df = build_possession_wave_df(shot_df)
pressing_profile_df, pressing_profile_lines = build_pressing_profile(
    player_df,
    opp_shot_profile,
    opponent_zone_profile,
    event_df,
)
build_up_structure_df, build_up_structure_lines = build_build_up_structure(player_df)
control_room_lines = build_control_room_summary(
    zone_threat_df,
    possession_wave_df,
    pressing_profile_lines,
    build_up_structure_lines,
)
review_title, review_lines = build_match_review(
    match_page_props,
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    xg_race_df,
)
team_summary = build_team_summary(filtered_matches)
selected_record = f"{team_summary['wins']}-{team_summary['draws']}-{team_summary['losses']}"
recent_form_string, recent_form_matches = build_recent_form_summary(filtered_matches)
last_lineup = payload.get("overview", {}).get("lastLineupStats", {})
next_match = get_selected_next_match(matches_df, selected_match)
key_player_name, key_player_reasons = build_key_player_summary(
    match_page_props,
    player_df,
    shot_df,
    relationship_hubs_df,
)
match_how_line, match_why_line, match_missing_line = build_match_verdict(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    review_lines,
    defensive_review_lines,
    key_player_name,
)
coach_takeaways = build_coach_takeaways(
    selected_match,
    next_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    defensive_review_lines,
    attack_review_lines,
    key_player_name,
    player_impact_df,
)
opponent_game_plan_lines = build_opponent_game_plan(
    next_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    structural_diagnosis_df,
)
analysis_template_sections = build_analysis_template_sections(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    arsenal_zone_profile,
    opponent_zone_profile,
    match_swing_notes,
    structural_summary_lines,
    attack_review_lines,
    defensive_review_lines,
    opponent_possession_review_lines,
    role_profile_df,
    coach_takeaways,
    opponent_game_plan_lines,
)
full_match_report = build_full_match_report(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    arsenal_zone_profile,
    opponent_zone_profile,
    review_lines,
    attack_review_lines,
    defensive_review_lines,
    opponent_possession_review_lines,
    match_swing_notes,
    arsenal_edges,
    opponent_edges,
    key_player_name,
    key_player_reasons,
    player_impact_df,
    coach_takeaways,
    structural_summary_lines,
    phase_comparison_notes,
    opponent_game_plan_lines,
    analysis_template_sections,
)
x_post_pack = build_x_post_pack(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    control_profile,
    match_swing_notes,
    arsenal_edges,
    opponent_edges,
    key_player_name,
    match_how_line,
    match_why_line,
    match_missing_line,
    control_room_lines,
)
deep_dive_candidates = [name for name in [key_player_name] + player_impact_df["Player"].tolist() if name]
deep_dive_candidates = list(dict.fromkeys(deep_dive_candidates))
deep_dive_state_key = f"deep_dive_player_{selected_match_id}"
if deep_dive_state_key not in st.session_state or st.session_state[deep_dive_state_key] not in deep_dive_candidates:
    st.session_state[deep_dive_state_key] = key_player_name if key_player_name in deep_dive_candidates else (deep_dive_candidates[0] if deep_dive_candidates else None)
selected_deep_dive_player = st.session_state.get(deep_dive_state_key)
player_deep_dive = build_player_deep_dive(
    player_df,
    shot_df,
    relationship_hubs_df,
    selected_deep_dive_player,
) if selected_deep_dive_player else {}
player_heatmap_df = build_player_heatmap_points(
    match_heatmap_payload,
    match_page_props,
    selected_deep_dive_player,
) if selected_deep_dive_player else pd.DataFrame(columns=["x", "y"])
analyst_snapshot_lines = build_analyst_snapshot(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    arsenal_zone_profile,
    opponent_zone_profile,
)
match_context_bundle = build_match_context_bundle(
    selected_match,
    shot_profile,
    opp_shot_profile,
    tactical_summary,
    arsenal_zone_profile,
    opponent_zone_profile,
    arsenal_edges,
    opponent_edges,
    match_swing_notes,
    review_lines,
    control_profile,
    defensive_review_lines,
    score_state_df,
    relationship_links_df,
    relationship_hubs_df,
    attack_review_lines,
    opponent_possession_review_lines,
    player_impact_df,
    structural_diagnosis_df,
    structural_summary_lines,
    phase_comparison_notes,
    role_profile_df,
    opponent_game_plan_lines,
    analysis_template_sections,
    recent_form_string,
    selected_record,
    key_player_name,
    key_player_reasons,
    match_how_line,
    match_why_line,
    match_missing_line,
    zone_threat_df,
    possession_wave_df,
    pressing_profile_df,
    pressing_profile_lines,
    build_up_structure_df,
    build_up_structure_lines,
    control_room_lines,
)

top_metrics_row_one = st.columns(3)
top_metrics_row_one[0].metric("大会", selected_match["competition"])
top_metrics_row_one[1].metric("試合日", selected_match["date"].strftime("%d %b %Y") if pd.notna(selected_match["date"]) else "未定")
top_metrics_row_one[2].metric("対戦相手", selected_match["opponent"])
top_metrics_row_two = st.columns(3)
top_metrics_row_two[0].metric("スコア", selected_match["score"])
top_metrics_row_two[1].metric("直近フォーム", recent_form_string, help=f"選択中の大会における直近 {recent_form_matches} 試合の結果。W=勝利, D=引き分け, L=敗戦")
top_metrics_row_two[2].metric("選択範囲の成績", selected_record, help="現在の大会フィルターで選ばれている試合群の通算 W-D-L")

if layout_mode == "Guided Story":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("1. 試合の前提")
    st.caption("まず試合の前提と結論を押さえます。ここで結果、相手、会場、試合の読み筋を固定してから細部に入ります。")
    context_left, context_right = st.columns([0.95, 1.05])
    with context_left:
        context_metrics = st.columns(2)
        context_metrics[0].metric("会場", selected_match["venue"])
        context_metrics[1].metric("結果", selected_match["result"])
        context_metrics = st.columns(2)
        context_metrics[0].metric("得点", int(selected_match["arsenal_goals"]) if pd.notna(selected_match["arsenal_goals"]) else 0)
        context_metrics[1].metric("失点", int(selected_match["opponent_goals"]) if pd.notna(selected_match["opponent_goals"]) else 0)
        st.write(f"**Arsenal はどうだったか**  {match_how_line}")
        st.write(f"**なぜこの結果になったか**  {match_why_line}")
        st.write(f"**何が足りなかったか**  {match_missing_line}")
    with context_right:
        render_match_review(review_title, review_lines)
        with st.expander("直近成績のベンチマーク", expanded=True):
            for note in recent_benchmark_notes:
                st.write(f"- {note}")
            st.plotly_chart(
                create_recent_results_benchmark_chart(recent_benchmark_df),
                width="stretch",
                key=f"guided_recent_benchmark_{selected_match_id}",
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("2. 結果を動かした要因")
    st.caption("次に、勝敗を直接押した要素を確認します。xG、中央侵入、セットプレー、キープレイヤーを近くに置いて読めるようにしています。")
    driver_left, driver_right = st.columns([1.05, 0.95])
    with driver_left:
        signal_cols = st.columns(4)
        signal_cols[0].metric("Arsenal xG", f"{shot_profile['xg']:.2f}")
        signal_cols[1].metric("相手 xG", f"{opp_shot_profile['xg']:.2f}")
        signal_cols[2].metric("中央シュート", shot_profile["central_shots"])
        signal_cols[3].metric("ファイナルサードへのパス", f"{tactical_summary['final_third_passes']:.0f}")
        edge_cols = st.columns(2)
        with edge_cols[0]:
            st.write("**Arsenalの優位**")
            for line in arsenal_edges or ["明確な優位は限定的で、細部勝負の試合でした。"]:
                st.write(f"- {line}")
        with edge_cols[1]:
            st.write("**相手の脅威**")
            for line in opponent_edges or ["相手の脅威は大きくなく、Arsenal が主導権を持てた試合でした。"]:
                st.write(f"- {line}")
    with driver_right:
        render_player_focus_card(
            selected_deep_dive_player,
            key_player_name,
            key_player_reasons,
            player_deep_dive,
            player_impact_df,
        )
        if deep_dive_candidates:
            st.caption("選手をクリックすると、このカードと選手深掘りが切り替わります。")
            button_cols = st.columns(min(4, len(deep_dive_candidates)))
            for idx, player_name in enumerate(deep_dive_candidates[:4]):
                if button_cols[idx].button(player_name, key=f"guided_deep_dive_button_{selected_match_id}_{player_name}", use_container_width=True):
                    st.session_state[deep_dive_state_key] = player_name
                    st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    flow_left, flow_right = st.columns([1.05, 0.95])
    with flow_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("3. 試合の流れ")
        st.caption("どの時間帯で試合が傾いたかを見ます。xG Race、時間帯別xG、スコア状態をまとめて置いています。")
        flow_tabs = st.tabs(["xG推移", "時間帯別支配", "スコア状況別", "イベント"])
        with flow_tabs[0]:
            st.plotly_chart(create_xg_race_chart(xg_race_df), width="stretch", key=f"guided_xg_race_{selected_match_id}")
            for note in match_swing_notes:
                st.write(f"- {note}")
        with flow_tabs[1]:
            st.plotly_chart(create_phase_split_chart(arsenal_phase_df, opponent_phase_df), width="stretch", key=f"guided_phase_{selected_match_id}")
            for line in phase_comparison_notes:
                st.write(f"- {line}")
        with flow_tabs[2]:
            if score_state_df.empty:
                st.info("この試合ではスコア状況別データを利用できません。")
            else:
                st.plotly_chart(create_score_state_chart(score_state_df), width="stretch", key=f"guided_score_state_{selected_match_id}")
                st.dataframe(score_state_df, width="stretch", hide_index=True)
        with flow_tabs[3]:
            st.plotly_chart(create_event_timeline_chart(event_df), width="stretch", key=f"guided_event_{selected_match_id}")
            st.dataframe(key_moments_df, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with flow_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("4. チャンスと陣地")
        st.caption("流れの次に、どこまで前進でき、どれだけ良いチャンスに変換できたかを確認します。")
        chance_cols = st.columns(2)
        chance_cols[0].metric("オープンプレー xG", f"{shot_profile['open_play_xg']:.2f}")
        chance_cols[1].metric("セットプレー xG", f"{shot_profile['set_piece_xg']:.2f}")
        chance_cols = st.columns(2)
        chance_cols[0].metric("ボックス内シュート", shot_profile["box_shots"])
        chance_cols[1].metric("押し込み度 proxy", f"{control_profile['field_tilt_proxy']:.0f}%")
        st.plotly_chart(create_final_third_access_chart(player_df), width="stretch", key=f"guided_final_third_{selected_match_id}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("5. 戦術構造")
    st.caption("ここで構造を読みます。保持、脅威ゾーン、プレッシング、守備、選手関係性を同じ章にまとめています。")
    if control_room_lines:
        control_cols = st.columns(len(control_room_lines))
        for idx, line in enumerate(control_room_lines):
            label, _, value = line.partition(": ")
            control_cols[idx].markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-card-label">{label}</div>
                    <div class="insight-card-value">{value if value else line}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    structure_tabs = st.tabs(["脅威ゾーン", "ビルドアップ", "プレッシング", "構造診断", "マップ"])
    with structure_tabs[0]:
        tz_left, tz_right = st.columns([1.12, 0.88])
        with tz_left:
            st.plotly_chart(create_zone_threat_map(zone_threat_df), width="stretch", key=f"guided_zone_threat_{selected_match_id}")
        with tz_right:
            st.dataframe(
                zone_threat_df[
                    ["Zone", "Threat", "Primary Builder", "Top Contributors", "Main Shooter", "Shot xG", "Progression proxy", "Shots"]
                ].sort_values("Threat", ascending=False),
                width="stretch",
                hide_index=True,
            )
    with structure_tabs[1]:
        build_left, build_right = st.columns([1.12, 0.88])
        with build_left:
            st.plotly_chart(create_build_up_structure_chart(build_up_structure_df), width="stretch", key=f"guided_build_up_{selected_match_id}")
        with build_right:
            for line in build_up_structure_lines:
                st.write(f"- {line}")
            st.dataframe(build_up_structure_df[["Player", "Line", "Lane", "Touches", "Final-third Passes"]], width="stretch", hide_index=True)
    with structure_tabs[2]:
        press_left, press_right = st.columns([1.0, 1.0])
        with press_left:
            st.plotly_chart(create_pressing_profile_chart(pressing_profile_df), width="stretch", key=f"guided_pressing_{selected_match_id}")
        with press_right:
            for line in pressing_profile_lines:
                st.write(f"- {line}")
            st.dataframe(pressing_profile_df, width="stretch", hide_index=True)
    with structure_tabs[3]:
        diag_left, diag_right = st.columns([1.0, 1.0])
        with diag_left:
            st.plotly_chart(create_structural_diagnosis_chart(structural_diagnosis_df), width="stretch", key=f"guided_structural_{selected_match_id}")
        with diag_right:
            for line in structural_summary_lines:
                st.write(f"- {line}")
            st.write("**Attack**")
            for line in attack_review_lines[:3]:
                st.write(f"- {line}")
            st.write("**Opponent Possession**")
            for line in opponent_possession_review_lines[:3]:
                st.write(f"- {line}")
    with structure_tabs[4]:
        map_tabs = st.tabs(["シュートマップ", "パスネットワーク", "関係性"])
        with map_tabs[0]:
            st.plotly_chart(create_match_shot_map(shot_df) if not shot_df.empty else create_shot_threat_map(player_df), width="stretch", key=f"guided_shot_map_{selected_match_id}")
        with map_tabs[1]:
            st.plotly_chart(create_pass_map(player_df), width="stretch", key=f"guided_pass_map_{selected_match_id}")
        with map_tabs[2]:
            rel_left, rel_right = st.columns([1.0, 1.0])
            with rel_left:
                if relationship_hubs_df.empty:
                    st.info("この試合では関係性データを利用できません。")
                else:
                    st.plotly_chart(create_hub_chart(relationship_hubs_df), width="stretch", key=f"guided_hub_chart_{selected_match_id}")
            with rel_right:
                st.dataframe(relationship_links_df, width="stretch", hide_index=True)
                st.dataframe(relationship_hubs_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    player_left, player_right = st.columns([1.05, 0.95])
    with player_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("6. 選手レイヤー")
        st.caption("最後に選手へ降ります。試合単位の貢献とシーズン全体の評価を分けて見ます。")
        player_tabs = st.tabs(["試合への影響", "選手深掘り", "シーズン"])
        with player_tabs[0]:
            st.dataframe(player_impact_df, width="stretch", hide_index=True)
            st.dataframe(role_profile_df, width="stretch", hide_index=True)
        with player_tabs[1]:
            if selected_deep_dive_player:
                deep_left, deep_right = st.columns([0.95, 1.05])
                with deep_left:
                    st.plotly_chart(create_player_stat_bar(player_deep_dive), width="stretch", key=f"guided_player_bar_{selected_match_id}_{selected_deep_dive_player}")
                with deep_right:
                    if not player_heatmap_df.empty:
                        st.plotly_chart(create_player_heatmap(player_heatmap_df), width="stretch", key=f"guided_player_heatmap_{selected_match_id}_{selected_deep_dive_player}")
                    else:
                        player_shot_df = player_deep_dive.get("shot_df", pd.DataFrame())
                        if isinstance(player_shot_df, pd.DataFrame) and not player_shot_df.empty:
                            st.plotly_chart(create_match_shot_map(player_shot_df), width="stretch", key=f"guided_player_shots_{selected_match_id}_{selected_deep_dive_player}")
                        else:
                            st.info("この選手のヒートマップまたはシュートデータを利用できません。")
        with player_tabs[2]:
            if season_player_performance_df.empty:
                st.info("シーズン選手評価データを利用できません。")
            else:
                st.plotly_chart(create_season_performance_chart(season_player_performance_df), width="stretch", key="guided_season_performance")
                st.dataframe(season_player_performance_df, width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with player_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.subheader("7. 監督視点とアウトプット")
        st.caption("分析を次戦準備と共有用アウトプットに変換します。")
        output_tabs = st.tabs(["監督視点", "レポート", "ニュース・怪我"])
        with output_tabs[0]:
            st.write(coach_takeaways["staff_note"])
            for line in coach_takeaways["continue"]:
                st.write(f"- Continue: {line}")
            for line in coach_takeaways["change"]:
                st.write(f"- Change: {line}")
            for line in opponent_game_plan_lines:
                st.write(f"- Plan: {line}")
        with output_tabs[1]:
            st.download_button(
                "マッチレポートをダウンロード (.md)",
                data=full_match_report,
                file_name=f"arsenal-report-{selected_match['match_id']}.md",
                mime="text/markdown",
                use_container_width=True,
                key=f"guided_report_download_{selected_match_id}",
            )
            st.download_button(
                "X投稿パックをダウンロード (.txt)",
                data=x_post_pack,
                file_name=f"arsenal-x-post-{selected_match['match_id']}.txt",
                mime="text/plain",
                use_container_width=True,
                key=f"guided_x_post_download_{selected_match_id}",
            )
            with st.expander("X Post Preview"):
                st.text_area("X投稿 / スレッド案", value=x_post_pack, height=320, key=f"guided_x_post_preview_{selected_match_id}")
        with output_tabs[2]:
            st.write("**怪我・離脱**")
            st.dataframe(injury_df, width="stretch", hide_index=True)
            st.write("**ニュース**")
            if news_df.empty:
                st.info("ニュースを一時的に取得できません。")
            else:
                for item in news_df.to_dict("records")[:4]:
                    link = item.get("link", "")
                    title = item.get("title", "Untitled")
                    if link:
                        st.markdown(f'<div class="news-item"><a href="{link}">{title}</a></div>', unsafe_allow_html=True)
                    else:
                        st.write(title)
                    st.caption(item.get("source", "Source"))
        st.markdown("</div>", unsafe_allow_html=True)

    chat_key = f"analyst_chat_{selected_match_id}"
    active_chat_key = st.session_state.get("active_analyst_chat_key")
    if active_chat_key != chat_key:
        st.session_state["active_analyst_chat_key"] = chat_key
        st.session_state[chat_key] = [
            {
                "role": "assistant",
                "content": (
                    f"{selected_match['opponent']} 戦を見ながら深掘りできます。"
                    "『なぜ勝てた？』『どの時間帯で押し込んだ？』『誰がThreat Zoneを作った？』のように聞いてください。"
                ),
            }
        ]
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("8. Arsenal分析チャット")
    st.caption("最後に疑問を深掘りします。ここまでの章で見たデータを使って質問できます。")
    prompt_cols = st.columns(4)
    suggested_prompts = ["なぜ勝てた？", "どの時間帯で優位だった？", "誰がThreat Zoneを作った？", "次戦に活かすなら？"]
    for index, prompt in enumerate(suggested_prompts):
        if prompt_cols[index].button(prompt, use_container_width=True, key=f"guided_prompt_{index}_{selected_match_id}"):
            st.session_state[chat_key].append({"role": "user", "content": prompt})
            st.session_state[chat_key].append({"role": "assistant", "content": generate_analyst_answer(prompt, match_context_bundle)})
    for message in st.session_state[chat_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    user_question = st.chat_input("この試合の勝因・敗因・流れについて聞く", key=f"guided_chat_input_{selected_match_id}")
    if user_question:
        st.session_state[chat_key].append({"role": "user", "content": user_question})
        st.session_state[chat_key].append({"role": "assistant", "content": generate_analyst_answer(user_question, match_context_bundle)})
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader(f"現在のモード: {'選手分析' if view_mode == 'Player Analytics' else 'チーム分析'}")
render_section_benefit("Current Mode")
if view_mode == "Player Analytics":
    st.caption("選手分析が有効です。選手単位の試合影響度と深掘りを優先して表示します。")
else:
    st.caption("チーム分析が有効です。試合全体とチーム戦術の分析を優先して表示します。")
st.markdown("</div>", unsafe_allow_html=True)

if view_mode == "Player Analytics":
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("選手マッチボード")
    render_section_benefit("Player Matchboard")
    if deep_dive_candidates:
        top_player = st.selectbox(
            "注目選手",
            options=deep_dive_candidates,
            index=deep_dive_candidates.index(st.session_state[deep_dive_state_key]),
            key=f"top_player_focus_{selected_match_id}",
        )
        if top_player != st.session_state[deep_dive_state_key]:
            st.session_state[deep_dive_state_key] = top_player
            st.rerun()
        top_player_dive = build_player_deep_dive(
            player_df,
            shot_df,
            relationship_hubs_df,
            st.session_state[deep_dive_state_key],
        )
        top_left, top_right = st.columns([1.0, 1.0])
        with top_left:
            top_metrics = st.columns(4)
            top_metrics[0].metric("評価点", top_player_dive.get("rating") or "N/A")
            top_metrics[1].metric("タッチ数", top_player_dive.get("touches", 0))
            top_metrics[2].metric("ファイナルサードへのパス", top_player_dive.get("final_third_passes", 0))
            top_metrics[3].metric("xG", f"{top_player_dive.get('xg', 0.0):.2f}")
            st.plotly_chart(
                create_player_stat_bar(top_player_dive),
                width="stretch",
                key=f"top_player_stat_bar_{selected_match_id}_{st.session_state[deep_dive_state_key]}",
            )
        with top_right:
            top_player_shots = top_player_dive.get("shot_df", pd.DataFrame())
            if isinstance(top_player_shots, pd.DataFrame) and not top_player_shots.empty:
                st.plotly_chart(
                    create_match_shot_map(top_player_shots),
                    width="stretch",
                    key=f"top_player_shot_map_{selected_match_id}_{st.session_state[deep_dive_state_key]}",
                )
            else:
                st.info("この選手のシュート記録はありません。")
    else:
        st.info("この試合の選手データを利用できません。")
    st.markdown("</div>", unsafe_allow_html=True)

summary_col, trend_col = st.columns([1.05, 1.35])

with summary_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("試合センター")
    render_section_benefit("Match Center")
    detail_left, detail_right = st.columns(2)
    detail_left.metric("会場", selected_match["venue"])
    detail_left.metric("結果", selected_match["result"])
    detail_left.metric("得点", int(selected_match["arsenal_goals"]) if pd.notna(selected_match["arsenal_goals"]) else 0)
    detail_right.metric("失点", int(selected_match["opponent_goals"]) if pd.notna(selected_match["opponent_goals"]) else 0)
    detail_right.metric("状態", selected_match["status"])
    detail_right.metric("直近フォーメーション", last_lineup.get("formation", "不明"))
    if next_match:
        st.write(
            f"次戦: {next_match['opponent']['name']} / {normalize_competition(next_match['tournament']['name'])} / "
            f"{parse_dt(next_match['status']['utcTime']).strftime('%d %b %Y %H:%M UTC')}"
        )
    st.caption(
        "Scott Willis的な観点: チャンス品質、中央ボックス侵入、ファイナルサードへの前進、レーンの偏り。"
    )
    st.caption("直近フォームは直近試合の並び、選択範囲の成績は現在の絞り込み範囲での通算成績です。")
    st.markdown("</div>", unsafe_allow_html=True)

with trend_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("直近成績")
    render_section_benefit("Recent Results")
    completed = filtered_matches[filtered_matches["finished"]].sort_values("date")
    result_fig = go.Figure()
    result_fig.add_trace(
        go.Scatter(
            x=completed["date"],
            y=completed["arsenal_goals"],
            mode="lines+markers",
            name="Arsenal Goals",
            line=dict(color=ARSENAL_GOLD, width=3),
            marker=dict(size=9),
        )
    )
    result_fig.add_trace(
        go.Scatter(
            x=completed["date"],
            y=completed["opponent_goals"],
            mode="lines+markers",
            name="Goals Conceded",
            line=dict(color=ARSENAL_RED, width=3),
            marker=dict(size=9),
        )
    )
    result_fig = base_chart_layout(result_fig, height=300)
    result_fig.update_xaxes(showgrid=False)
    result_fig.update_yaxes(gridcolor="rgba(159,176,196,0.14)", zeroline=False, title=None)
    st.plotly_chart(result_fig, width="stretch")
    st.caption("下の比較は、直近成績が選択中コンペ範囲の平均や目標ラインに対して良いのか悪いのかを見るためのベンチマークです。")
    st.plotly_chart(
        create_recent_results_benchmark_chart(recent_benchmark_df),
        width="stretch",
        key=f"recent_results_benchmark_{selected_match_id}",
    )
    for note in recent_benchmark_notes:
        st.write(f"- {note}")
    if not trend_summary_df.empty:
        st.dataframe(trend_summary_df, width="stretch", hide_index=True)
    if not recent_benchmark_df.empty:
        st.dataframe(
            recent_benchmark_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="medium"),
                "Recent": st.column_config.NumberColumn("Recent", format="%.2f"),
                "Season Avg": st.column_config.NumberColumn("Selected Avg", format="%.2f"),
                "Target": st.column_config.NumberColumn("Good Line", format="%.2f"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Delta vs Avg": st.column_config.NumberColumn("Delta vs Avg", format="%+.2f"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)

review_col, notes_col = st.columns([1.1, 0.9])

with review_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    render_match_review(review_title, review_lines)
    st.markdown("</div>", unsafe_allow_html=True)

with notes_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("試合の主要シグナル")
    render_section_benefit("Key Match Signals")
    key_metrics = st.columns(2)
    key_metrics[0].metric("オープンプレー xG", f"{shot_profile['open_play_xg']:.2f}")
    key_metrics[1].metric("セットプレー xG", f"{shot_profile['set_piece_xg']:.2f}")
    key_metrics = st.columns(2)
    key_metrics[0].metric("中央シュート", shot_profile["central_shots"])
    key_metrics[1].metric("ファイナルサードへのパス", f"{tactical_summary['final_third_passes']:.0f}")
    st.markdown("</div>", unsafe_allow_html=True)

verdict_col, player_col = st.columns([1.15, 0.85])

with verdict_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("この試合が示すこと")
    render_section_benefit("What This Match Says")
    st.write(f"**Arsenal はどうだったか**  {match_how_line}")
    st.write(f"**なぜこの結果になったか**  {match_why_line}")
    st.write(f"**何が足りなかったか**  {match_missing_line}")
    st.markdown("</div>", unsafe_allow_html=True)

with player_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("キープレイヤー診断")
    render_section_benefit("Key Player Verdict")
    render_player_focus_card(
        selected_deep_dive_player,
        key_player_name,
        key_player_reasons,
        player_deep_dive,
        player_impact_df,
    )
    if deep_dive_candidates:
        st.caption("クリックすると、このカードと選手深掘りセクションが切り替わります。")
        button_cols = st.columns(min(4, len(deep_dive_candidates)))
        for idx, player_name in enumerate(deep_dive_candidates[:4]):
            if button_cols[idx].button(player_name, key=f"deep_dive_button_{selected_match_id}_{player_name}", use_container_width=True):
                st.session_state[deep_dive_state_key] = player_name
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("試合コントロールルーム")
render_section_benefit("Match Control Room")
st.caption("試合を直感的に読むための4層です。xT/pressing/possession は公開FotMobデータから作るproxyなので、映像分析の入り口として使います。")
if control_room_lines:
    control_cols = st.columns(len(control_room_lines))
    for idx, line in enumerate(control_room_lines):
        label, _, value = line.partition(": ")
        control_cols[idx].markdown(
            f"""
            <div class="insight-card">
                <div class="insight-card-label">{label}</div>
                <div class="insight-card-value">{value if value else line}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
control_tabs = st.tabs(["脅威ゾーン", "攻撃の波", "ビルドアップ構造", "プレッシング"])
with control_tabs[0]:
    render_section_benefit("Threat Zones")
    threat_left, threat_right = st.columns([1.15, 0.85])
    with threat_left:
        st.plotly_chart(
            create_zone_threat_map(zone_threat_df),
            width="stretch",
            key=f"zone_threat_map_{selected_match_id}",
        )
    with threat_right:
        st.write("赤が濃いほど、シュートxGと前進proxyが集まったゾーンです。ゾーン内の主なビルドアップ関与者も併記します。")
        st.dataframe(
            zone_threat_df[
                ["Zone", "Threat", "Primary Builder", "Top Contributors", "Main Shooter", "Shot xG", "Progression proxy", "Shots"]
            ].sort_values("Threat", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Zone": st.column_config.TextColumn("Zone", width="medium"),
                "Threat": st.column_config.NumberColumn("Threat", format="%.2f"),
                "Primary Builder": st.column_config.TextColumn("主なビルドアップ関与者", width="medium"),
                "Top Contributors": st.column_config.TextColumn("上位関与者", width="large"),
                "Main Shooter": st.column_config.TextColumn("主なシューター", width="medium"),
                "Shot xG": st.column_config.NumberColumn("シュートxG", format="%.2f"),
                "Progression proxy": st.column_config.NumberColumn("前進proxy", format="%.2f"),
                "Shots": st.column_config.NumberColumn("シュート数"),
            },
        )
with control_tabs[1]:
    render_section_benefit("Attacking Waves")
    wave_left, wave_right = st.columns([1.15, 0.85])
    with wave_left:
        st.plotly_chart(
            create_possession_wave_chart(possession_wave_df),
            width="stretch",
            key=f"possession_wave_chart_{selected_match_id}",
        )
    with wave_right:
        st.write("短い時間に連続したシュートを「攻撃の波」としてまとめ、どの局面で試合が傾いたかを見ます。")
        st.dataframe(
            possession_wave_df[["Wave", "Minutes", "Shots", "xG", "Main Player", "Signal"]],
            width="stretch",
            hide_index=True,
        )
with control_tabs[2]:
    render_section_benefit("Build-up Shape")
    build_left, build_right = st.columns([1.15, 0.85])
    with build_left:
        st.plotly_chart(
            create_build_up_structure_chart(build_up_structure_df),
            width="stretch",
            key=f"build_up_structure_{selected_match_id}",
        )
    with build_right:
        for line in build_up_structure_lines:
            st.write(f"- {line}")
        st.dataframe(
            build_up_structure_df[["Player", "Line", "Lane", "Touches", "Final-third Passes"]],
            width="stretch",
            hide_index=True,
            column_config={
                "Player": st.column_config.TextColumn("Player", width="medium"),
                "Line": st.column_config.TextColumn("Line", width="medium"),
                "Lane": st.column_config.TextColumn("Lane", width="medium"),
            },
        )
with control_tabs[3]:
    render_section_benefit("Pressing Lens")
    press_left, press_right = st.columns([1.0, 1.0])
    with press_left:
        st.plotly_chart(
            create_pressing_profile_chart(pressing_profile_df),
            width="stretch",
            key=f"pressing_profile_{selected_match_id}",
        )
    with press_right:
        for line in pressing_profile_lines:
            st.write(f"- {line}")
        st.dataframe(
            pressing_profile_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Metric": st.column_config.TextColumn("Metric", width="medium"),
                "Score": st.column_config.NumberColumn("Score", format="%.1f"),
                "Signal": st.column_config.TextColumn("Signal", width="large"),
            },
        )
st.markdown("</div>", unsafe_allow_html=True)

coach_col, prep_col = st.columns([1.0, 1.0])

with coach_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("監督向け示唆")
    render_section_benefit("Coach Takeaways")
    st.write(coach_takeaways["staff_note"])
    for line in coach_takeaways["continue"]:
        st.write(f"- 継続: {line}")
    for line in coach_takeaways["change"]:
        st.write(f"- 修正: {line}")
    st.markdown("</div>", unsafe_allow_html=True)

with prep_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("次戦への準備")
    render_section_benefit("Next Match Prep")
    st.write(coach_takeaways["next_up"])
    for line in coach_takeaways["selection"]:
        st.write(f"- 起用: {line}")
    for line in opponent_game_plan_lines:
        st.write(f"- プラン: {line}")
    if next_match:
        st.write("監督目線では、この試合で機能した構造をベースに、修正ポイントだけを次戦用に最適化するのが自然です。")
    st.markdown("</div>", unsafe_allow_html=True)

structure_left, structure_right = st.columns([1.1, 0.9])

with structure_left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("構造診断")
    render_section_benefit("Structural Diagnosis")
    st.plotly_chart(
        create_structural_diagnosis_chart(structural_diagnosis_df),
        width="stretch",
        key=f"structural_diagnosis_chart_{selected_match_id}",
    )
    st.markdown("</div>", unsafe_allow_html=True)

with structure_right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("構造的に見た理由")
    render_section_benefit("Why Structurally")
    for line in structural_summary_lines:
        st.write(f"- {line}")
    if not structural_diagnosis_df.empty:
        st.dataframe(
            structural_diagnosis_df[["Factor", "Signal", "Why"]],
            width="stretch",
            hide_index=True,
            column_config={
                "Factor": st.column_config.TextColumn("Factor", width="medium"),
                "Signal": st.column_config.TextColumn("Signal", width="large"),
                "Why": st.column_config.TextColumn("なぜ重要か", width="large"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)

attack_col, opp_pos_col = st.columns([1.0, 1.0])

with attack_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("攻撃レビュー")
    render_section_benefit("Attack Review")
    for line in attack_review_lines:
        st.write(f"- {line}")
    st.markdown("</div>", unsafe_allow_html=True)

with opp_pos_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("相手保持レビュー")
    render_section_benefit("Opponent Possession Review")
    for line in opponent_possession_review_lines:
        st.write(f"- {line}")
    st.markdown("</div>", unsafe_allow_html=True)

half_col, role_col = st.columns([1.0, 1.0])

with half_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("前後半の変化")
    render_section_benefit("Half-by-Half Adjustments")
    st.plotly_chart(
        create_phase_comparison_chart(phase_comparison_df),
        width="stretch",
        key=f"phase_comparison_chart_{selected_match_id}",
    )
    for line in phase_comparison_notes:
        st.write(f"- {line}")
    st.markdown("</div>", unsafe_allow_html=True)

with role_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("役割評価")
    render_section_benefit("Role Evaluation")
    st.dataframe(
        role_profile_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Role": st.column_config.TextColumn("Role", width="small"),
            "Evidence": st.column_config.TextColumn("Evidence", width="large"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)

phase_col, zone_col = st.columns([1.05, 0.95])

with phase_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("時間帯別の支配")
    render_section_benefit("Phase Control")
    st.caption("どの時間帯で優位だったかを xG ベースで分解。")
    st.plotly_chart(create_phase_split_chart(arsenal_phase_df, opponent_phase_df), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

with zone_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("ゾーン別プロフィール")
    render_section_benefit("Zone Profile")
    zone_metrics = st.columns(2)
    zone_metrics[0].metric("Zone 14 Shots", arsenal_zone_profile["zone14_entries"])
    zone_metrics[1].metric("Central Box Shots", arsenal_zone_profile["central_box_shots"])
    zone_metrics = st.columns(2)
    zone_metrics[0].metric("Left Half-space", arsenal_zone_profile["left_half_space_shots"])
    zone_metrics[1].metric("Right Half-space", arsenal_zone_profile["right_half_space_shots"])
    st.caption(
        f"Opponent: Zone 14 {opponent_zone_profile['zone14_entries']} | "
        f"Central box {opponent_zone_profile['central_box_shots']} | "
        f"LHS {opponent_zone_profile['left_half_space_shots']} | "
        f"RHS {opponent_zone_profile['right_half_space_shots']}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

driver_col, threat_col = st.columns([1.0, 1.0])

with driver_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Arsenalの優位")
    render_section_benefit("Arsenal Edge")
    if arsenal_edges:
        for line in arsenal_edges:
            st.write(f"- {line}")
    else:
        st.write("- 明確な優位は限定的で、細部勝負の試合でした。")
    st.caption("勝因になり得た要素を、xG・中央侵入・前進量・時間帯支配で抽出。")
    st.markdown("</div>", unsafe_allow_html=True)

with threat_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("相手の脅威")
    render_section_benefit("Opponent Threat")
    if opponent_edges:
        for line in opponent_edges:
            st.write(f"- {line}")
    else:
        st.write("- 相手の脅威は大きくなく、Arsenal が主導権を持てた試合でした。")
    st.caption("敗因や危険局面に直結した、相手側の優位ポイント。")
    st.markdown("</div>", unsafe_allow_html=True)

left_col, right_col = st.columns([1.05, 0.95])

with left_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader(view_mode)
    render_section_benefit(view_mode)
    if view_mode == "Team Analytics":
        summary_cards = st.columns(4)
        summary_cards[0].metric("勝利", team_summary["wins"])
        summary_cards[1].metric("引き分け", team_summary["draws"])
        summary_cards[2].metric("敗戦", team_summary["losses"])
        summary_cards[3].metric("得失点差", team_summary["goals"] - team_summary["conceded"])

        matchup_table = filtered_matches[
            ["date", "competition", "stage", "venue", "opponent", "score", "result"]
        ].copy()
        matchup_table["date"] = matchup_table["date"].dt.strftime("%d %b %Y")
        st.dataframe(
            matchup_table,
            width="stretch",
            hide_index=True,
            column_config={
                "date": st.column_config.TextColumn("Date", width="medium"),
                "competition": st.column_config.TextColumn("Competition", width="large"),
                "stage": st.column_config.TextColumn("Stage", width="medium"),
                "venue": st.column_config.TextColumn("Venue", width="small"),
                "opponent": st.column_config.TextColumn("Opponent", width="large"),
                "score": st.column_config.TextColumn("Score", width="small"),
                "result": st.column_config.TextColumn("Result", width="small"),
            },
        )
    else:
        if player_df.empty:
            st.info("Player analytics are temporarily unavailable.")
        else:
            player_focus = st.selectbox("注目選手", options=player_df[player_df["role"] != "Unavailable"]["player"].tolist())
            focus_row = player_df.loc[player_df["player"] == player_focus].iloc[0]
            player_metrics = st.columns(5)
            player_metrics[0].metric("直近試合の評価", focus_row["rating_last_match"] or "N/A")
            player_metrics[1].metric("シーズン得点", int(focus_row["season_goals"] or 0))
            player_metrics[2].metric("シーズンアシスト", int(focus_row["season_assists"] or 0))
            player_metrics[3].metric("シーズン評価", focus_row["season_rating"] or "N/A")
            player_metrics[4].metric("市場価値", format_money(focus_row["market_value"]))

            player_chart = px.bar(
                player_df[player_df["role"] != "Unavailable"],
                x="player",
                y=["season_goals", "season_assists", "season_rating"],
                barmode="group",
                color_discrete_sequence=[ARSENAL_RED, ARSENAL_GOLD, "#8DD3C7"],
            )
            player_chart = base_chart_layout(player_chart, height=340)
            player_chart.update_xaxes(title=None)
            player_chart.update_yaxes(title=None, gridcolor="rgba(159,176,196,0.14)")
            st.plotly_chart(player_chart, width="stretch")

            player_table = player_df.rename(
                columns={
                    "player": "Player",
                    "role": "役割",
                    "status": "状態",
                    "rating_last_match": "直近試合の評価",
                    "season_goals": "シーズン得点",
                    "season_assists": "シーズンアシスト",
                    "season_rating": "シーズン評価",
                    "market_value": "市場価値",
                }
            )[
                ["Player", "役割", "状態", "直近試合の評価", "シーズン得点", "シーズンアシスト", "シーズン評価", "市場価値"]
            ].copy()
            player_table["市場価値"] = player_table["市場価値"].apply(format_money)
            st.dataframe(
                player_table,
                width="stretch",
                hide_index=True,
                column_config={
                    "Player": st.column_config.TextColumn("選手", width="large"),
                    "役割": st.column_config.TextColumn("役割", width="small"),
                    "状態": st.column_config.TextColumn("状態", width="medium"),
                    "直近試合の評価": st.column_config.TextColumn("直近試合の評価", width="medium"),
                    "シーズン得点": st.column_config.TextColumn("シーズン得点", width="small"),
                    "シーズンアシスト": st.column_config.TextColumn("シーズンアシスト", width="small"),
                    "シーズン評価": st.column_config.TextColumn("シーズン評価", width="small"),
                    "市場価値": st.column_config.TextColumn("市場価値", width="medium"),
                },
            )
    st.markdown("</div>", unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("シーズン上位パフォーマー")
    render_section_benefit("Top Arsenal Performers")
    if top_players_df.empty:
        st.info("上位選手データを利用できません。")
    else:
        top_chart = px.bar(
            top_players_df,
            x="Player",
            y="Value",
            color="Category",
            barmode="group",
            color_discrete_sequence=[ARSENAL_GOLD, ARSENAL_RED, "#7DD3FC"],
        )
        top_chart = base_chart_layout(top_chart, height=340)
        top_chart.update_xaxes(title=None)
        top_chart.update_yaxes(title=None, gridcolor="rgba(159,176,196,0.14)")
        st.plotly_chart(top_chart, width="stretch")
        for item in top_players_df.to_dict("records"):
            st.markdown(
                f"**{item['Category']}**: {item['Player']}  |  Value: {item['Value']}  |  Rank: {item['Rank']}"
            )
    if not player_impact_df.empty:
        st.caption("試合影響度ランキング")
        st.dataframe(player_impact_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

analysis_col, access_col = st.columns([1.05, 0.95])

with analysis_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("チャンス品質プロフィール")
    render_section_benefit("Chance Quality Profile")
    chance_metrics = st.columns(4)
    chance_metrics[0].metric("シュート数", shot_profile["shots"])
    chance_metrics[1].metric("xG", f"{shot_profile['xg']:.2f}")
    chance_metrics[2].metric("決定機", shot_profile["big_chances"])
    chance_metrics[3].metric("中央シュート", shot_profile["central_shots"])
    split_metrics = st.columns(3)
    split_metrics[0].metric("ボックス内シュート", shot_profile["box_shots"])
    split_metrics[1].metric("オープンプレー xG", f"{shot_profile['open_play_xg']:.2f}")
    split_metrics[2].metric("セットプレー xG", f"{shot_profile['set_piece_xg']:.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

with access_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("陣地と侵入")
    render_section_benefit("Territory & Access")
    territory_metrics = st.columns(4)
    territory_metrics[0].metric("ファイナルサードへのパス", f"{tactical_summary['final_third_passes']:.0f}")
    territory_metrics[1].metric("攻撃時の平均高さ", f"{tactical_summary['mean_attack_height']:.0f}")
    territory_metrics[2].metric("後方保持人数", f"{tactical_summary['rest_defence_count']:.0f}")
    territory_metrics[3].metric("右レーン偏重", f"{tactical_summary['right_lane_bias']:.0f}%")
    proxy_metrics = st.columns(3)
    proxy_metrics[0].metric("押し込み度 proxy", f"{control_profile['field_tilt_proxy']:.0f}%")
    proxy_metrics[1].metric("ボックス侵入 proxy", f"{control_profile['box_entry_proxy']:.0f}")
    proxy_metrics[2].metric("ボックスタッチ proxy", f"{control_profile['box_touch_proxy']:.1f}")
    st.plotly_chart(create_final_third_access_chart(player_df), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

xg_col, map_col = st.columns([0.95, 1.05])

with xg_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("xG推移")
    render_section_benefit("xG Race")
    st.caption("Arsenalと相手の累積xGをシュートごとに追い、どの時間帯で流れが傾いたかを見ます。")
    st.plotly_chart(create_xg_race_chart(xg_race_df), width="stretch")
    for note in match_swing_notes:
        st.write(f"- {note}")
    st.markdown("</div>", unsafe_allow_html=True)

defence_col, state_col = st.columns([1.0, 1.0])

with defence_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("守備レビュー")
    render_section_benefit("Defensive Review")
    defence_metrics = st.columns(3)
    defence_metrics[0].metric("相手 xG", f"{opp_shot_profile['xg']:.2f}")
    defence_metrics[1].metric("相手中央シュート", opp_shot_profile["central_shots"])
    defence_metrics[2].metric("相手ボックスタッチ proxy", f"{control_profile['opponent_box_touch_proxy']:.1f}")
    for line in defensive_review_lines:
        st.write(f"- {line}")
    st.markdown("</div>", unsafe_allow_html=True)

with state_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("スコア状況別分析")
    render_section_benefit("Score State Analysis")
    if score_state_df.empty:
        st.info("この試合ではスコア状況別データを利用できません。")
    else:
        st.plotly_chart(create_score_state_chart(score_state_df), width="stretch")
        state_table = score_state_df.copy()
        state_table["xG"] = state_table["xG"].map(lambda value: f"{value:.2f}")
        st.dataframe(state_table, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

event_left, event_right = st.columns([1.0, 1.0])

with event_left:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("イベントタイムライン")
    render_section_benefit("Event Timeline")
    st.plotly_chart(
        create_event_timeline_chart(event_df),
        width="stretch",
        key=f"event_timeline_{selected_match_id}",
    )
    if not event_df.empty:
        timeline_table = event_df[["minute", "team", "event_type", "player", "score"]].copy()
        timeline_table["minute"] = timeline_table["minute"].map(lambda value: f"{int(numeric_or_default(value))}'")
        st.dataframe(timeline_table, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with event_right:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    tab_periods, tab_subs = st.tabs(["時間帯スタッツ", "交代の影響"])
    with tab_periods:
        if period_stats_df.empty:
            st.info("この試合では時間帯スタッツを利用できません。")
        else:
            st.dataframe(period_stats_df.astype(str), width="stretch", hide_index=True)
    with tab_subs:
        if substitution_impact_df.empty:
            st.info("この試合では交代影響データを利用できません。")
        else:
            st.dataframe(substitution_impact_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

map_col, side_col = st.columns([1.05, 0.95])

with map_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("シュートマップ")
    render_section_benefit("Match Shot Map")
    st.caption("選択したArsenalの試合におけるFotMobの実シュート位置です。円の大きさはxGを表します。")
    if shot_df.empty:
        st.plotly_chart(create_shot_threat_map(player_df), width="stretch")
    else:
        st.plotly_chart(create_match_shot_map(shot_df), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("パスネットワーク")
    render_section_benefit("Pass Network")
    st.caption("FotMobのラインアップ、パス関連指標、関係性の重みから作成しています。")
    st.plotly_chart(create_pass_map(player_df), width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("選手間の関係性")
    render_section_benefit("Player Relationships")
    rel_left, rel_right = st.columns([1.05, 0.95])
    with rel_left:
        if relationship_hubs_df.empty:
            st.info("この試合では関係性データを利用できません。")
        else:
            st.plotly_chart(create_hub_chart(relationship_hubs_df), width="stretch")
    with rel_right:
        tab_links, tab_hubs = st.tabs(["主な接続", "ハブ選手"])
        with tab_links:
            st.dataframe(relationship_links_df, width="stretch", hide_index=True)
        with tab_hubs:
            st.dataframe(relationship_hubs_df, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

with side_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("怪我・離脱状況")
    render_section_benefit("Injury Tracker")
    if injury_df.empty:
        st.success("最新のチームフィードでは離脱中のArsenal選手は返されていません。")
    else:
        st.dataframe(
            injury_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Player": st.column_config.TextColumn("Player", width="large"),
                "Status": st.column_config.TextColumn("Status", width="medium"),
                "Expected Return": st.column_config.TextColumn("Expected Return", width="large"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("Arsenalニュース")
    render_section_benefit("Arsenal News")
    if news_df.empty:
        st.info("ニュースを一時的に取得できません。")
    else:
        for item in news_df.to_dict("records")[:6]:
            link = item.get("link", "")
            title = item.get("title", "Untitled")
            source = item.get("source", "Source")
            summary = item.get("summary", "")
            if link:
                st.markdown(f'<div class="news-item"><a href="{link}">{title}</a></div>', unsafe_allow_html=True)
            else:
                st.write(title)
            if summary:
                st.write(summary)
            st.caption(source)
    st.markdown(
        '<div class="small-note">Live data is cached briefly for stability and refreshed automatically on the interval selected in the sidebar.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

chat_key = f"analyst_chat_{selected_match_id}"
active_chat_key = st.session_state.get("active_analyst_chat_key")
if active_chat_key != chat_key:
    st.session_state["active_analyst_chat_key"] = chat_key
    st.session_state[chat_key] = [
        {
            "role": "assistant",
            "content": (
                f"{selected_match['opponent']} 戦を見ながら深掘りできます。"
                "『なぜ勝てた？』『どの時間帯で押し込んだ？』『相手はどこで危険だった？』のように聞いてください。"
            ),
        }
    ]
if chat_key not in st.session_state:
    st.session_state[chat_key] = []

history_col, snapshot_col = st.columns([1.0, 1.0])

with history_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    tab_history, tab_moments = st.tabs(["レビュー履歴", "重要局面"])
    with tab_history:
        st.dataframe(
            review_history_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="medium"),
                "Competition": st.column_config.TextColumn("Competition", width="large"),
                "Opponent": st.column_config.TextColumn("Opponent", width="large"),
                "Score": st.column_config.TextColumn("Score", width="small"),
                "Result": st.column_config.TextColumn("Result", width="small"),
            },
        )
    with tab_moments:
        st.dataframe(
            key_moments_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Minute": st.column_config.TextColumn("Minute", width="small"),
                "Team": st.column_config.TextColumn("Team", width="small"),
                "Player": st.column_config.TextColumn("Player", width="large"),
                "xG": st.column_config.TextColumn("xG", width="small"),
                "Outcome": st.column_config.TextColumn("Outcome", width="medium"),
                "Situation": st.column_config.TextColumn("Situation", width="medium"),
            },
        )
    st.markdown("</div>", unsafe_allow_html=True)

with snapshot_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("分析スナップショット")
    render_section_benefit("Analyst Snapshot")
    for line in analyst_snapshot_lines:
        st.write(line)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("Cannon型 分析テンプレート")
render_section_benefit("Cannon-Style Analysis Template")
template_tabs = st.tabs([section["section"].split(". ", 1)[1] for section in analysis_template_sections])
for tab, section in zip(template_tabs, analysis_template_sections):
    with tab:
        st.write(f"**問い**  {section['question']}")
        st.write(f"**見るべきビジュアル**  {section['visual']}")
        st.write(f"**解釈**  {section['interpretation']}")
        st.write(f"**監督向けアクション**  {section['action']}")
        metric_rows = pd.DataFrame({"Signal": section.get("metrics", [])})
        if not metric_rows.empty:
            st.dataframe(metric_rows, width="stretch", hide_index=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("フルマッチレポート")
render_section_benefit("Full Match Report")
report_top_left, report_top_right = st.columns([1.15, 0.85])
with report_top_left:
    st.plotly_chart(
        create_match_report_comparison_chart(
            shot_profile,
            opp_shot_profile,
            tactical_summary,
            control_profile,
            arsenal_zone_profile,
            opponent_zone_profile,
        ),
        width="stretch",
    )
with report_top_right:
    report_cards = st.columns(2)
    report_cards[0].metric("Arsenal xG", f"{shot_profile['xg']:.2f}")
    report_cards[1].metric("相手 xG", f"{opp_shot_profile['xg']:.2f}")
    report_cards = st.columns(2)
    report_cards[0].metric("押し込み度 proxy", f"{control_profile['field_tilt_proxy']:.0f}%")
    report_cards[1].metric("キープレイヤー", key_player_name)
    report_cards = st.columns(2)
    report_cards[0].metric("中央シュート", shot_profile["central_shots"])
    report_cards[1].metric("相手中央シュート", opp_shot_profile["central_shots"])

report_summary_left, report_summary_right = st.columns([1.0, 1.0])
with report_summary_left:
    st.write(f"**Arsenal はどうだったか**  {match_how_line}")
    st.write(f"**なぜこの結果になったか**  {match_why_line}")
with report_summary_right:
    st.write(f"**何が足りなかったか**  {match_missing_line}")
    st.write(f"**キープレイヤー**  {key_player_name}")

st.download_button(
    "マッチレポートをダウンロード (.md)",
    data=full_match_report,
    file_name=f"arsenal-report-{selected_match['match_id']}.md",
    mime="text/markdown",
    use_container_width=True,
)
st.download_button(
    "X投稿パックをダウンロード (.txt)",
    data=x_post_pack,
    file_name=f"arsenal-x-post-{selected_match['match_id']}.txt",
    mime="text/plain",
    use_container_width=True,
)
with st.expander("X投稿プレビュー"):
    st.text_area(
        "X投稿 / スレッド案",
        value=x_post_pack,
        height=360,
        key=f"x_post_pack_preview_{selected_match_id}",
    )
with st.expander("テキストレポートを開く"):
    st.markdown(full_match_report)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("シーズン選手パフォーマンス分析")
render_section_benefit("Season Player Performance Lab")
st.caption("1試合ではなく、シーズン全体で誰が良いパフォーマンスを出しているかを見る補助モジュールです。FotMob公開フィードの season rating、G/A、直近評価、Top-player recognition、availability を合成しています。")
if season_player_performance_df.empty:
    st.info("シーズン選手評価データを利用できません。")
else:
    with st.expander("シーズン選手分析を開く", expanded=False):
        season_left, season_right = st.columns([1.15, 0.85])
        with season_left:
            st.plotly_chart(
                create_season_performance_chart(season_player_performance_df),
                width="stretch",
                key="season_performance_scatter",
            )
        with season_right:
            season_focus = st.selectbox(
                "注目選手",
                options=season_player_performance_df["Player"].tolist(),
                key="season_player_focus",
            )
            focus_season = season_player_performance_df[season_player_performance_df["Player"] == season_focus].iloc[0]
            season_metrics = st.columns(2)
            season_metrics[0].metric("パフォーマンススコア", f"{focus_season['Performance Score']:.1f}")
            season_metrics[1].metric("プロフィール", focus_season["Profile"])
            season_metrics = st.columns(2)
            season_metrics[0].metric("シーズン評価", f"{focus_season['Season Rating']:.2f}")
            season_metrics[1].metric("G+A", int(focus_season["Goal Contributions"]))
            st.plotly_chart(
                create_player_score_breakdown(season_player_performance_df, season_focus),
                width="stretch",
                key=f"season_score_breakdown_{season_focus}",
            )
            st.write(f"**評価**  {focus_season['Verdict']}")
        st.dataframe(
            season_player_performance_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Player": st.column_config.TextColumn("Player", width="medium"),
                "Role": st.column_config.TextColumn("Role", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Profile": st.column_config.TextColumn("Profile", width="medium"),
                "Verdict": st.column_config.TextColumn("Verdict", width="large"),
                "Performance Score": st.column_config.NumberColumn("Performance Score", format="%.1f"),
                "Season Rating": st.column_config.NumberColumn("Season Rating", format="%.2f"),
                "Last Match Rating": st.column_config.NumberColumn("Last Match Rating", format="%.2f"),
            },
        )
        st.caption("注意: minutes、progressive carries、pressures などの完全なシーズンイベント指標は公開フィードにないため、この評価は多角proxyです。")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("選手深掘り")
render_section_benefit("Player Deep Dive")
if deep_dive_candidates:
    selected_deep_dive_player = st.selectbox(
        "確認する選手",
        options=deep_dive_candidates,
        index=deep_dive_candidates.index(st.session_state[deep_dive_state_key]),
    )
    if selected_deep_dive_player != st.session_state[deep_dive_state_key]:
        st.session_state[deep_dive_state_key] = selected_deep_dive_player
        st.rerun()
    player_deep_dive = build_player_deep_dive(
        player_df,
        shot_df,
        relationship_hubs_df,
        selected_deep_dive_player,
    )
    deep_left, deep_right = st.columns([1.0, 1.0])
    with deep_left:
        deep_metrics = st.columns(3)
        deep_metrics[0].metric("評価点", player_deep_dive.get("rating") or "N/A")
        deep_metrics[1].metric("シュート数", player_deep_dive.get("shots", 0))
        deep_metrics[2].metric("xG", f"{player_deep_dive.get('xg', 0.0):.2f}")
        deep_metrics = st.columns(3)
        deep_metrics[0].metric("成功パス", player_deep_dive.get("accurate_passes", 0))
        deep_metrics[1].metric("ファイナルサードへのパス", player_deep_dive.get("final_third_passes", 0))
        deep_metrics[2].metric("タッチ数", player_deep_dive.get("touches", 0))
        deep_metrics = st.columns(3)
        deep_metrics[0].metric("回収", player_deep_dive.get("recoveries", 0))
        deep_metrics[1].metric("走行距離", f"{player_deep_dive.get('distance_covered', 0.0):.1f}")
        deep_metrics[2].metric("ハブスコア", f"{player_deep_dive.get('hub_score', 0.0):.2f}")
        st.plotly_chart(
            create_player_stat_bar(player_deep_dive),
            width="stretch",
            key=f"deep_dive_stat_bar_{selected_match_id}_{selected_deep_dive_player}",
        )
    with deep_right:
        player_shot_df = player_deep_dive.get("shot_df", pd.DataFrame())
        heatmap_tab, shotmap_tab = st.tabs(["ヒートマップ", "シュートマップ"])
        with heatmap_tab:
            if not player_heatmap_df.empty:
                st.plotly_chart(
                    create_player_heatmap(player_heatmap_df),
                    width="stretch",
                    key=f"deep_dive_heatmap_{selected_match_id}_{selected_deep_dive_player}",
                )
            else:
                st.info("この選手のヒートマップデータを利用できません。")
        with shotmap_tab:
            if isinstance(player_shot_df, pd.DataFrame) and not player_shot_df.empty:
                st.plotly_chart(
                    create_match_shot_map(player_shot_df),
                    width="stretch",
                    key=f"deep_dive_shot_map_{selected_match_id}_{selected_deep_dive_player}",
                )
            else:
                st.info("この選手のシュート記録はありません。")
        st.dataframe(
            pd.DataFrame(
                {
                    "Metric": [
                        "Rating",
                        "Accurate Passes",
                        "Final-third Passes",
                        "Touches",
                        "Recoveries",
                        "Shots",
                        "xG",
                    ],
                    "Value": [
                        str(player_deep_dive.get("rating") or "N/A"),
                        str(player_deep_dive.get("accurate_passes", 0)),
                        str(player_deep_dive.get("final_third_passes", 0)),
                        str(player_deep_dive.get("touches", 0)),
                        str(player_deep_dive.get("recoveries", 0)),
                        str(player_deep_dive.get("shots", 0)),
                        f"{player_deep_dive.get('xg', 0.0):.2f}",
                    ],
                }
            ),
            width="stretch",
            hide_index=True,
        )
else:
    st.info("この試合では選手深掘りデータを利用できません。")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.subheader("Arsenal分析チャット")
render_section_benefit("Arsenal Analyst Chat")
prompt_cols = st.columns(4)
suggested_prompts = [
    "なぜ勝てた？",
    "どの時間帯で優位だった？",
    "相手はどこで危険だった？",
    "この試合を3行でまとめて",
]
for index, prompt in enumerate(suggested_prompts):
    if prompt_cols[index].button(prompt, use_container_width=True):
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        st.session_state[chat_key].append(
            {"role": "assistant", "content": generate_analyst_answer(prompt, match_context_bundle)}
        )

for message in st.session_state[chat_key]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_question = st.chat_input("この試合の勝因・敗因・流れについて聞く")
if user_question:
    st.session_state[chat_key].append({"role": "user", "content": user_question})
    st.session_state[chat_key].append(
        {"role": "assistant", "content": generate_analyst_answer(user_question, match_context_bundle)}
    )
    st.rerun()
st.markdown("</div>", unsafe_allow_html=True)
