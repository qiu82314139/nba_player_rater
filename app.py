import streamlit as st
from typing import Dict
from config.settings import ARCHETYPES, THEME_COLORS
from data.fetcher import fetch_data_pipeline
from logic.calculator import calculate_sub_scores, calculate_ovr, get_tier_badge
from logic.visualizer import draw_radar_chart
from data.database import init_db, save_rating, get_player_history
import pandas as pd

st.set_page_config(page_title="NBA Player Rater", page_icon="🏀", layout="wide")
init_db()

st.sidebar.title("NBA Player Rater")
player_name = st.sidebar.text_input("球员姓名")
archetype = st.sidebar.selectbox("赛道", ARCHETYPES, index=0)
isolation = st.sidebar.slider("硬解能力", 0, 99, 75)
def_eye = st.sidebar.slider("防守观感", 0, 99, 75)
clutch = st.sidebar.slider("关键属性", 0, 99, 75)
run = st.sidebar.button("生成/更新评级")

tab_main, tab_history = st.tabs(["评级", "历史趋势"]) 

with tab_main:
    if run and player_name.strip():
        data = fetch_data_pipeline(player_name.strip())
        stats = data["stats"]
        source = data["source"]
        if source == "mock":
            msg = data.get("reason") or "已切换至模拟数据模式"
            st.warning(msg)
        sliders = {"isolation": isolation, "def_eye_test": def_eye, "clutch": clutch}
        subs = calculate_sub_scores(stats, archetype, sliders)
        ovr = calculate_ovr(subs, archetype)
        tier = get_tier_badge(ovr)
        color = THEME_COLORS[archetype]
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown(f"<div style='background:#0E1117;border:1px solid {color};padding:24px;border-radius:12px'>" 
                        f"<div style='font-size:24px;color:white'>{stats.get('PLAYER_NAME','')}</div>" 
                        f"<div style='font-size:72px;color:{color};line-height:1'>{ovr}</div>" 
                        f"<div style='font-size:18px;color:white'>徽章 {tier}</div>" 
                        f"</div>", unsafe_allow_html=True)
            kdf = pd.DataFrame({
                "指标": ["PTS", "TS%", "AST_PCT", "REB_PCT"],
                "数值": [round(stats.get("PTS", 0.0), 2), round(stats.get("TS_PCT", 0.0), 3), round(stats.get("AST_PCT", 0.0), 3), round(stats.get("REB_PCT", 0.0), 3)]
            })
            st.dataframe(kdf, hide_index=True)
        with c2:
            fig = draw_radar_chart(subs, color)
            st.pyplot(fig, transparent=True)
        save_rating(player_name.strip(), archetype, ovr, subs)

with tab_history:
    if player_name.strip():
        rows = get_player_history(player_name.strip(), limit=15)
        if rows:
            hist_df = pd.DataFrame(rows, columns=["OVR", "时间"])
            hist_df = hist_df.sort_values("时间")
            st.line_chart(hist_df.set_index("时间"))
        else:
            st.info("暂无历史记录")