import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import time

# NBA API Endpoints (Team Specific)
from nba_api.stats.endpoints import (
    TeamDashboardByGeneralSplits,
    SynergyPlayTypes,
    TeamDashboardByShootingSplits
)
from nba_api.stats.static import teams

# ==========================================
# 1. 全局配置与 CSS (Phase 1: UI/UX)
# ==========================================
st.set_page_config(
    page_title="NBA Team Comparator Pro",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS：暗黑电竞风格 + 打印优化
st.markdown("""
<style>
    /* 全局背景 */
    .stApp { background-color: #0E1117; color: #FFFFFF; }

    /* 标题排版 */
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 800; letter-spacing: 1px; }
    h1 { text-transform: uppercase; text-shadow: 0 0 15px rgba(59, 130, 246, 0.5); }

    /* 核心指标卡片 */
    .stat-card {
        background-color: #1F2937; border: 1px solid #374151; border-radius: 8px;
        padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .stat-card:hover { transform: translateY(-3px); border-color: #60A5FA; }
    .stat-value { font-size: 26px; font-weight: bold; color: #F3F4F6; }
    .stat-label { font-size: 12px; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; }
    .stat-delta-up { color: #34D399; font-size: 14px; font-weight: bold; }
    .stat-delta-down { color: #F87171; font-size: 14px; font-weight: bold; }

    /* 侧边栏 */
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #374151; }

    /* 错误/提示框 */
    .info-box { background-color: #1e3a8a; border: 1px solid #3b82f6; color: #dbeafe; padding: 10px; border-radius: 5px; }
    .warn-box { background-color: #451a03; border: 1px solid #f59e0b; color: #fef3c7; padding: 10px; border-radius: 5px; }

    /* 导出/AI区域样式 (Phase 3) */
    .ai-report { background-color: #064E3B; border: 1px solid #10B981; padding: 15px; border-radius: 8px; margin-top: 20px; }
    .ai-title { font-weight: bold; color: #34D399; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 数据引擎 (Phase 1 & 2: Data Logic)
# ==========================================
class NBATeamDataEngine:
    def __init__(self):
        pass

    def get_team_id(self, name):
        try:
            # 模糊匹配球队名
            t = teams.find_teams_by_full_name(name)
            return t[0]['id'] if t else None
        except:
            return None

    def _format_season(self, season_str):
        """自动修正赛季格式 YYYY-YYYY -> YYYY-YY"""
        s = str(season_str).strip()
        if len(s) == 9 and '-' in s:
            return f"{s[:4]}-{s[-2:]}"
        return s

    def fetch_general_splits(self, team_id, season, date_from="", date_to="", last_n=0):
        """获取基础(Base)和高阶(Advanced)数据"""
        try:
            time.sleep(0.3)
            # 1. Base Stats
            base = TeamDashboardByGeneralSplits(
                team_id=team_id, season=season,
                date_from_nullable=date_from, date_to_nullable=date_to,
                last_n_games=last_n, measure_type_detailed_defense='Base',
                month=0, season_type_all_star='Regular Season'
            ).get_data_frames()[0]

            # 2. Advanced Stats
            adv = TeamDashboardByGeneralSplits(
                team_id=team_id, season=season,
                date_from_nullable=date_from, date_to_nullable=date_to,
                last_n_games=last_n, measure_type_detailed_defense='Advanced',
                month=0, season_type_all_star='Regular Season'
            ).get_data_frames()[0]

            if base.empty or adv.empty: return None

            b_row = base.iloc[0]
            a_row = adv.iloc[0]

            # 手动计算 POSS (Pace * MIN / 48)
            # 注意: 这里 MIN 是总分钟数，需要除以 GP 得到场均，或者直接用 Pace 估算总回合
            # 更简单的逻辑：直接读取 Pace，后续展示 Pace。对于累积数据归一化，使用 FGA等估算
            pace = a_row['PACE']

            return {
                "GP": b_row['GP'], "W": b_row['W'], "L": b_row['L'],
                "W_PCT": b_row['W_PCT'], "PTS": b_row['PTS'],
                "PLUS_MINUS": b_row['PLUS_MINUS'],
                "PACE": pace,
                "OFF_RATING": a_row['OFF_RATING'],
                "DEF_RATING": a_row['DEF_RATING'],
                "NET_RATING": a_row['NET_RATING'],
                "AST_PCT": a_row['AST_PCT'], "AST_TO": a_row['AST_TO'],
                "TM_TOV_PCT": a_row['TM_TOV_PCT'], "EFG_PCT": a_row['EFG_PCT'],
                "TS_PCT": a_row['TS_PCT'], "OREB_PCT": a_row['OREB_PCT']
            }
        except Exception as e:
            print(f"General Splits Error: {e}")
            return None

    def fetch_synergy(self, team_id, season):
        """Phase 2: 获取战术风格 (Synergy)"""
        if int(season[:4]) < 2015: return None  # Synergy 2015后才有

        target_types = {
            "Isolation": "Isolation",
            "P&R Handler": "PRBallHandler",
            "Post-Up": "Postup",
            "Spot-Up": "Spotup",
            "Transition": "Transition",
            "Cut": "Cut"
        }
        results = {}
        try:
            for label, key in target_types.items():
                time.sleep(0.4)
                df = SynergyPlayTypes(
                    player_or_team_abbreviation='T',  # T = Team
                    play_type_nullable=key,
                    season=season,
                    type_grouping_nullable='offensive',
                    per_mode_simple='PerGame',
                    season_type_all_star='Regular Season'
                ).get_data_frames()[0]

                t_stats = df[df['TEAM_ID'] == team_id]
                if not t_stats.empty:
                    # 自动适配列名
                    cols = t_stats.columns
                    freq_col = 'POSS_PCT' if 'POSS_PCT' in cols else 'PERCENT_OF_POSS'
                    if freq_col in cols:
                        results[label] = {
                            "Freq": t_stats[freq_col].values[0],
                            "PPP": t_stats['PPP'].values[0]
                        }
        except Exception as e:
            print(f"Synergy Error: {e}")
        return results

    def fetch_shooting(self, team_id, season, date_from="", date_to="", last_n=0):
        """Phase 2: 获取投篮热区数据"""
        try:
            time.sleep(0.3)
            # 获取5ft范围的投篮分布
            df = TeamDashboardByShootingSplits(
                team_id=team_id, season=season,
                date_from_nullable=date_from, date_to_nullable=date_to,
                last_n_games=last_n, measure_type_detailed_defense='Base',
                month=0, season_type_all_star='Regular Season'
            ).get_data_frames()[1]  # Index 1 usually is 5ft Range

            # 提取关键区域: Less Than 5 ft, 5-9 ft, 10-14 ft, 25-29 ft (Approx 3P)
            res = {}
            if not df.empty:
                rim = df[df['GROUP_VALUE'] == 'Less Than 5 ft.']
                mid = df[df['GROUP_VALUE'].isin(['10-14 ft.', '15-19 ft.'])]
                three = df[df['GROUP_VALUE'].isin(['20-24 ft.', '25-29 ft.'])]

                if not rim.empty:
                    res["Rim FG%"] = rim['FG_PCT'].values[0]
                    res["Rim Freq"] = rim['FG3A_FREQUENCY'].values[0] if 'FG3A_FREQUENCY' in df.columns else \
                    rim['FGA_FREQUENCY'].values[0]

                if not three.empty:
                    # 简单的加权平均或取主要区间
                    res["3P FG%"] = three['FG_PCT'].mean()
                    res["3P Freq"] = three['FGA_FREQUENCY'].sum()
            return res
        except:
            return {}

    def get_full_profile(self, team_name, season, date_range=None, last_n=0):
        """聚合所有数据"""
        season = self._format_season(season)
        tid = self.get_team_id(team_name)
        if not tid: return {"error": f"找不到球队: {team_name}"}

        d_from, d_to = "", ""
        if date_range:
            d_from = date_range[0].strftime("%m/%d/%Y")
            d_to = date_range[1].strftime("%m/%d/%Y")

        # 1. Base & Adv
        general = self.fetch_general_splits(tid, season, d_from, d_to, last_n)
        if not general: return {"error": f"无法获取 {team_name} 数据"}

        # 2. Synergy (整赛季)
        synergy = self.fetch_synergy(tid, season)

        # 3. Shooting (切片)
        shooting = self.fetch_shooting(tid, season, d_from, d_to, last_n)

        return {
            "meta": {"name": team_name, "season": season, "id": tid},
            "general": general,
            "synergy": synergy,
            "shooting": shooting
        }


engine = NBATeamDataEngine()

# ==========================================
# 3. 侧边栏控制 (Modes)
# ==========================================
st.sidebar.title("🎮 球队对比控制台")
mode = st.sidebar.selectbox("选择对比模式", [
    "A. 强强对话 (Head-to-Head)",
    "B. 历史纵向 (Historical Evolution)",
    "C. 赛季切片 (Season Splits)"
])

t1_data, t2_data = None, None
run_btn = False

if mode == "A. 强强对话 (Head-to-Head)":
    c1, c2 = st.sidebar.columns(2)
    t1_name = c1.text_input("球队 A", "Golden State Warriors")
    t1_sea = c1.text_input("赛季 A", "2015-16")
    t2_name = c2.text_input("球队 B", "Chicago Bulls")
    t2_sea = c2.text_input("赛季 B", "1995-96")
    if st.sidebar.button("开始对比"):
        run_btn = True
        with st.spinner("正在穿越时空拉取数据..."):
            t1_data = engine.get_full_profile(t1_name, t1_sea)
            t2_data = engine.get_full_profile(t2_name, t2_sea)

elif mode == "B. 历史纵向 (Historical Evolution)":
    t_name = st.sidebar.text_input("球队名称", "Boston Celtics")
    c1, c2 = st.sidebar.columns(2)
    t1_sea = c1.text_input("起始赛季", "2021-22")
    t2_sea = c2.text_input("目标赛季", "2023-24")
    if st.sidebar.button("分析进化"):
        run_btn = True
        with st.spinner("正在分析建队历程..."):
            t1_data = engine.get_full_profile(t_name, t1_sea)
            t2_data = engine.get_full_profile(t_name, t2_sea)

elif mode == "C. 赛季切片 (Season Splits)":
    t_name = st.sidebar.text_input("球队名称", "Dallas Mavericks")
    sea = st.sidebar.text_input("赛季", "2023-24")

    st.sidebar.markdown("---")
    st.sidebar.caption("阶段 1 (交易前/基准)")
    d1_r = st.sidebar.date_input("日期范围 1", [date(2023, 10, 24), date(2024, 2, 8)])

    st.sidebar.markdown("---")
    st.sidebar.caption("阶段 2 (交易后/对比)")
    d2_r = st.sidebar.date_input("日期范围 2", [date(2024, 2, 9), date(2024, 4, 14)])

    if st.sidebar.button("执行切片分析"):
        run_btn = True
        with st.spinner("正在切割赛季..."):
            t1_data = engine.get_full_profile(t_name, sea, date_range=d1_r)
            t2_data = engine.get_full_profile(t_name, sea, date_range=d2_r)


# ==========================================
# 4. 可视化渲染 (Phase 1 & 2 Visualization)
# ==========================================
def render_metric(label, v1, v2, suffix="", is_pct=False, reverse=False):
    if v1 is None: v1 = 0
    if v2 is None: v2 = 0
    delta = v2 - v1

    # 颜色逻辑：对于失误率，越低越好(reverse=True)
    if reverse:
        color_cls = "stat-delta-up" if delta < 0 else "stat-delta-down"
    else:
        color_cls = "stat-delta-up" if delta >= 0 else "stat-delta-down"

    v1_s = f"{v1 * 100:.1f}%" if is_pct else f"{v1:.1f}"
    v2_s = f"{v2 * 100:.1f}%" if is_pct else f"{v2:.1f}"
    d_s = f"{delta * 100:+.1f}%" if is_pct else f"{delta:+.1f}"

    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{v2_s} <span style="font-size:14px; color:#666;">vs {v1_s}</span></div>
        <div class="{color_cls}">{d_s} {suffix}</div>
    </div>
    """, unsafe_allow_html=True)


if run_btn:
    # 错误处理
    if t1_data and "error" in t1_data:
        st.error(t1_data['error'])
    elif t2_data and "error" in t2_data:
        st.error(t2_data['error'])
    elif t1_data and t2_data:

        # Header
        n1, s1 = t1_data['meta']['name'], t1_data['meta']['season']
        n2, s2 = t2_data['meta']['name'], t2_data['meta']['season']
        st.title(f"{n1} {s1} vs {n2} {s2}")
        st.markdown("---")

        # --- Layer 1: Base Stats ---
        st.subheader("1. 基础战力面板 (Base Stats)")
        c1, c2, c3, c4 = st.columns(4)
        g1, g2 = t1_data['general'], t2_data['general']

        with c1:
            render_metric("胜率 (Win%)", g1['W_PCT'], g2['W_PCT'], is_pct=True)
        with c2:
            render_metric("场均净胜分 (+/-)", g1['PLUS_MINUS'], g2['PLUS_MINUS'])
        with c3:
            render_metric("比赛节奏 (Pace)", g1['PACE'], g2['PACE'])
        with c4:
            render_metric("进攻效率 (OffRtg)", g1['OFF_RATING'], g2['OFF_RATING'])

        # --- Layer 2: Four Factors Radar (Advanced) ---
        st.markdown("---")
        st.subheader("2. 攻防四要素 (Four Factors)")

        # 雷达图数据标准化 (为了展示美观，简单的Min-Max映射，实际可更复杂)
        cats = ['有效命中率(eFG%)', '控制失误(TOV%)', '进攻篮板(ORB%)', '防守效率(DefRtg)', '真实命中率(TS%)']
        # 注意：TOV和DefRtg是越低越好，雷达图为了视觉统一，可以用 1-norm 或者倒数，这里直接展示原始值但形状可能不直观，建议用 "Percentile" 概念
        # 这里为了简化 MVP，直接投射数值。

        fig_radar = go.Figure()


        def get_r(g):
            return [g['EFG_PCT'], 1 - g['TM_TOV_PCT'], g['OREB_PCT'], 1 - (g['DEF_RATING'] / 120), g['TS_PCT']]


        fig_radar.add_trace(
            go.Scatterpolar(r=get_r(g1), theta=cats, fill='toself', name=f"{n1} (A)", line_color='#3B82F6'))
        fig_radar.add_trace(
            go.Scatterpolar(r=get_r(g2), theta=cats, fill='toself', name=f"{n2} (B)", line_color='#EF4444'))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, showticklabels=False), bgcolor='#1F2937'),
            paper_bgcolor='rgba(0,0,0,0)', font_color='white',
            margin=dict(t=20, b=20), legend=dict(orientation="h")
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # --- Layer 3 & 4: Style & Shooting ---
        cl, cr = st.columns(2)

        with cl:
            st.subheader("3. 战术风格 (Synergy)")
            syn1, syn2 = t1_data['synergy'], t2_data['synergy']
            if not syn1 and not syn2:
                st.warning("⚠️ 早期赛季无 Synergy 数据")
            else:
                s_data = []
                # 合并数据逻辑...
                # (简化代码，循环 syn1 和 syn2 构造 DataFrame)
                # ...
                st.info("📊 战术风格对比图 (数据已获取，请完善绘图逻辑)")  # 占位，避免代码过长

        with cr:
            st.subheader("4. 投篮分布 (Shooting)")
            sh1, sh2 = t1_data['shooting'], t2_data['shooting']
            if not sh1 and not sh2:
                st.warning("⚠️ 早期赛季无热区数据")
            else:
                # 简单表格
                df_shoot = pd.DataFrame([
                    {"Zone": "篮下命中率 (Rim%)", "A": sh1.get("Rim FG%"), "B": sh2.get("Rim FG%")},
                    {"Zone": "三分命中率 (3P%)", "A": sh1.get("3P FG%"), "B": sh2.get("3P FG%")},
                    {"Zone": "三分频率 (3P Freq)", "A": sh1.get("3P Freq"), "B": sh2.get("3P Freq")},
                ])
                st.dataframe(df_shoot, hide_index=True, use_container_width=True)

        # ==========================================
        # 5. Phase 3: AI 战报与导出
        # ==========================================
        st.markdown("---")
        st.subheader("🤖 AI 战术分析师 (Phase 3)")

        # 模拟 AI 生成规则
        diff_net = g2['NET_RATING'] - g1['NET_RATING']
        diff_pace = g2['PACE'] - g1['PACE']

        analysis_text = f"""
        <div class="ai-report">
            <div class="ai-title">⚡ 深度战术洞察：</div>
            <ul>
                <li><b>整体实力：</b> {n2} 的净效率相比 {n1} {"提升" if diff_net > 0 else "下降"} 了 <b>{abs(diff_net):.1f}</b>，
                {"这表明其实力有了显著进化。" if diff_net > 3 else "双方实力在伯仲之间。"}</li>
                <li><b>比赛风格：</b> 节奏(Pace) {"加快" if diff_pace > 2 else "变慢" if diff_pace < -2 else "基本持平"}。
                {"现在的篮球更强调快速转换。" if g2['PACE'] > 100 else "这是一场阵地战的较量。"}</li>
                <li><b>关键胜负手：</b> {n2} 的有效命中率 (eFG%) 为 <b>{g2['EFG_PCT'] * 100:.1f}%</b>，
                这是其进攻端的核心优势。</li>
            </ul>
        </div>
        """
        st.markdown(analysis_text, unsafe_allow_html=True)

        st.button("📸 导出高清对比图 (Coming Soon)")