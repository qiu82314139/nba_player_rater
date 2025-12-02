import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import time

# NBA API Endpoints
from nba_api.stats.endpoints import (
    PlayerDashboardByGeneralSplits,
    SynergyPlayTypes,
    PlayerDashPtShots
)
from nba_api.stats.static import players

# ==========================================
# 1. 页面配置与 CSS (Visual Design)
# ==========================================
st.set_page_config(
    page_title="NBA Player Comparator Pro (Real Data)",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入自定义 CSS：暗黑电竞风格
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    h1, h2, h3 { color: #FFFFFF; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }

    /* 数据卡片 */
    .stat-card {
        background-color: #1F2937; border: 1px solid #374151; border-radius: 8px;
        padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px;
    }
    .stat-value { font-size: 24px; font-weight: bold; color: #60A5FA; }
    .stat-label { font-size: 13px; color: #9CA3AF; text-transform: uppercase; }
    .stat-delta-up { color: #34D399; font-size: 14px; font-weight: bold; }
    .stat-delta-down { color: #F87171; font-size: 14px; font-weight: bold; }

    /* 侧边栏 */
    section[data-testid="stSidebar"] { background-color: #111827; border-right: 1px solid #374151; }

    /* 错误提示 */
    .error-box {
        padding: 1rem; background-color: #7f1d1d; border: 1px solid #f87171; 
        color: #fca5a5; border-radius: 0.5rem; margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 真实数据引擎 (Real Data Engine)
# ==========================================
class NBADataEngine:
    def __init__(self):
        pass

    def get_player_id(self, name):
        try:
            p = players.find_players_by_full_name(name)
            return p[0]['id'] if p else None
        except:
            return None

    def _normalize_per_100(self, stats_dict):
        """将基础数据转换为每100回合数据"""
        if not stats_dict: return {}
        try:
            # 优先使用 API 返回的 POSS (回合数)
            poss = stats_dict.get('POSS', 0)
            # 如果 API 没返回 POSS，手动估算: FGA + 0.44*FTA + TOV
            if poss == 0:
                poss = stats_dict.get('FGA', 0) + 0.44 * stats_dict.get('FTA', 0) + stats_dict.get('TOV', 0)

            if poss == 0: return stats_dict  # 避免除以零

            normalized = stats_dict.copy()
            # 需要转换的关键基础数据
            targets = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FGA', 'FG3A']
            for key in targets:
                if key in stats_dict:
                    normalized[f"{key}_100"] = (stats_dict[key] / poss) * 100

            normalized['POSS_EST'] = poss  # 记录使用的回合数
            return normalized
        except Exception as e:
            print(f"归一化计算出错: {e}")
            return stats_dict

    def fetch_base_advanced_stats(self, player_id, season, date_from="", date_to="", last_n=0):
        """
        调用 PlayerDashboardByGeneralSplits 获取最精准的切片数据
        [修复1] 参数名 measure_type_detailed
        [修复2] 参数名 season_type_playoffs (对应报错 season_type_all_star)
        """
        try:
            time.sleep(0.3)  # 防止 API 限制

            # 1. 获取基础数据 (Base)
            dash_base = PlayerDashboardByGeneralSplits(
                player_id=player_id,
                season=season,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                last_n_games=last_n,
                measure_type_detailed='Base',
                month=0,
                # --- 修正点：改为 season_type_playoffs ---
                season_type_playoffs='Regular Season'
            )
            df_base = dash_base.get_data_frames()[0]  # Overall Player Dashboard

            # 2. 获取高阶数据 (Advanced)
            dash_adv = PlayerDashboardByGeneralSplits(
                player_id=player_id,
                season=season,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                last_n_games=last_n,
                measure_type_detailed='Advanced',
                month=0,
                # --- 修正点：改为 season_type_playoffs ---
                season_type_playoffs='Regular Season'
            )
            df_adv = dash_adv.get_data_frames()[0]

            if df_base.empty or df_adv.empty:
                return None

            # 提取数据 (只取第一行，即总计)
            base_row = df_base.iloc[0]
            adv_row = df_adv.iloc[0]

            # 合并结果
            result = {
                "GP": base_row['GP'],
                "PTS": base_row['PTS'],
                "REB": base_row['REB'],
                "AST": base_row['AST'],
                "STL": base_row['STL'],
                "BLK": base_row['BLK'],
                "TOV": base_row['TOV'],
                "FGA": base_row['FGA'],
                "FTA": base_row['FTA'],
                "FG3A": base_row['FG3A'],
                "FG_PCT": base_row['FG_PCT'],
                "FG3_PCT": base_row['FG3_PCT'],
                "TS_PCT": adv_row['TS_PCT'],
                "USG_PCT": adv_row['USG_PCT'],
                "AST_PCT": adv_row['AST_PCT'],
                "PIE": adv_row['PIE'],
                "POSS": adv_row.get('POSS', 0)  # 尝试获取官方回合数
            }
            return result

        except Exception as e:
            print(f"API Fetch Error (Base/Adv): {e}")
            return None
    def fetch_synergy(self, player_id, season):
        """获取战术风格 (Season Level only)"""
        # 注意：Synergy 不支持 DateFrom/To，只能按赛季查
        target_play_types = {
            "P&R Handler": "PRBallHandler",
            "Isolation": "Isolation",
            "Spot-up": "Spotup",
            "Off Screen": "OffScreen"
        }
        results = {}
        try:
            for label, pt_key in target_play_types.items():
                time.sleep(0.4)
                synergy = SynergyPlayTypes(
                    player_or_team_abbreviation='P',
                    play_type_nullable=pt_key,
                    season=season,
                    type_grouping_nullable='offensive',
                    per_mode_simple='PerGame',
                    season_type_all_star='Regular Season'
                )
                df = synergy.get_data_frames()[0]
                player_stats = df[df['PLAYER_ID'] == player_id]

                if not player_stats.empty:
                    # 智能列名匹配 (POSS_PCT vs PERCENT_OF_POSS)
                    cols = player_stats.columns
                    freq_col = 'POSS_PCT' if 'POSS_PCT' in cols else 'PERCENT_OF_POSS'

                    if freq_col in cols:
                        results[label] = {
                            "Freq": player_stats[freq_col].values[0],
                            "PPP": player_stats['PPP'].values[0]
                        }
        except Exception as e:
            print(f"Synergy Error: {e}")

        return results

    def fetch_tracking(self, player_id, season, date_from="", date_to="", last_n=0):
        """获取投篮机制 (支持切片)"""
        try:
            dash = PlayerDashPtShots(
                player_id=player_id,
                season=season,
                date_from_nullable=date_from,
                date_to_nullable=date_to,
                last_n_games=last_n,
                team_id=0, month=0, season_type_all_star="Regular Season",
                opponent_team_id=0, period=0,
                outcome_nullable="", location_nullable="", season_segment_nullable="",
                vs_conference_nullable="", vs_division_nullable="", game_segment_nullable=""
            )
            df = dash.get_data_frames()[1]  # GeneralShooting

            res = {}
            if not df.empty:
                # C&S
                cs = df[df['SHOT_TYPE'] == 'Catch and Shoot']
                if not cs.empty:
                    res["C&S 3P%"] = cs['FG3_PCT'].values[0]
                    res["C&S Freq"] = cs['FG3A_FREQUENCY'].values[0]

                # Pull-up
                pu = df[df['SHOT_TYPE'] == 'Pull Ups']
                if not pu.empty:
                    res["Pull-up 3P%"] = pu['FG3_PCT'].values[0]
                    res["Pull-up Freq"] = pu['FG3A_FREQUENCY'].values[0]
            return res
        except:
            return {}

    def _format_season(self, season_str):
        """
        自动修正赛季格式：
        将 '2023-2024' 修正为 '2023-24'
        将 '2023-24' 保持不变
        """
        season_str = str(season_str).strip()
        # 如果是 YYYY-YYYY 格式 (例如 2023-2024)
        if len(season_str) == 9 and '-' in season_str:
            start_year = season_str[:4]
            end_year = season_str[-2:]  # 取最后两位
            return f"{start_year}-{end_year}"
        return season_str

    def get_full_profile(self, player_name, season, date_range=None, last_n=0):
        """主入口：聚合所有数据"""
        # --- 修复点 1：自动格式化赛季字符串 ---
        season = self._format_season(season)

        pid = self.get_player_id(player_name)
        if not pid:
            return {"error": f"找不到球员: {player_name}"}

        # 解析日期
        d_from, d_to = "", ""
        if date_range:
            d_from = date_range[0].strftime("%m/%d/%Y")
            d_to = date_range[1].strftime("%m/%d/%Y")

        # 1. Base & Advanced (支持切片)
        base_adv = self.fetch_base_advanced_stats(pid, season, d_from, d_to, last_n)
        if not base_adv:
            return {"error": f"无法获取 {player_name} 在 {season} 的数据 (可能未出场或赛季错误)"}

        # 归一化
        base_adv = self._normalize_per_100(base_adv)

        # 2. Synergy (不支持切片，仅赛季)
        synergy = {}
        # --- 修复点 2：转换赛季年份用于判断 ---
        # "2023-24" -> 取前4位 "2023" 转 int
        start_year = int(season[:4])

        if start_year >= 2015:
            synergy = self.fetch_synergy(pid, season)

        # 3. Tracking (支持切片)
        tracking = {}
        if start_year >= 2013:
            tracking = self.fetch_tracking(pid, season, d_from, d_to, last_n)

        return {
            "meta": {"name": player_name, "season": season, "id": pid},
            "base": base_adv,
            "synergy": synergy,
            "tracking": tracking
        }

# 初始化引擎
engine = NBADataEngine()

# ==========================================
# 3. 侧边栏：控制面板
# ==========================================
st.sidebar.title("⚙️ 数据对比配置")
mode = st.sidebar.selectbox("选择模式",
                            ["横向对比 (Player A vs B)", "纵向进化 (Year X vs Y)", "赛季切片 (Date/Game Split)"])

p1_data = None
p2_data = None
run_analysis = False

# --- 模式 A: 横向对比 ---
if mode == "横向对比 (Player A vs B)":
    c1, c2 = st.sidebar.columns(2)
    p1_name = c1.text_input("球员 A", "Klay Thompson")
    p1_season = c1.text_input("赛季 A", "2015-16")

    p2_name = c2.text_input("球员 B", "Kon Knueppel")
    p2_season = c2.text_input("赛季 B", "2025-26")

    if st.sidebar.button("开始对比 🚀"):
        run_analysis = True
        with st.spinner("正在从 NBA API 拉取真实数据..."):
            p1_data = engine.get_full_profile(p1_name, p1_season)
            p2_data = engine.get_full_profile(p2_name, p2_season)

# --- 模式 B: 纵向进化 ---
elif mode == "纵向进化 (Year X vs Y)":
    p_name = st.sidebar.text_input("球员姓名", "Shai Gilgeous-Alexander")
    c1, c2 = st.sidebar.columns(2)
    p1_season = c1.text_input("起始赛季", "2018-19")
    p2_season = c2.text_input("目标赛季", "2023-24")

    if st.sidebar.button("分析进化 📈"):
        run_analysis = True
        with st.spinner("正在分析进化路径..."):
            p1_data = engine.get_full_profile(p_name, p1_season)
            p2_data = engine.get_full_profile(p_name, p2_season)

# --- 模式 C: 赛季切片 ---
elif mode == "赛季切片 (Date/Game Split)":
    p_name = st.sidebar.text_input("球员姓名", "James Harden")
    season = st.sidebar.text_input("赛季", "2020-21")

    st.sidebar.markdown("---")
    st.sidebar.caption("阶段 1 (基准)")
    s1_type = st.sidebar.radio("切片1类型", ["全赛季", "日期范围"], horizontal=True)
    d1_range = None
    if s1_type == "日期范围":
        d1_range = st.sidebar.date_input("日期范围 1", [date(2020, 12, 22), date(2021, 1, 13)])

    st.sidebar.markdown("---")
    st.sidebar.caption("阶段 2 (对比)")
    s2_type = st.sidebar.radio("切片2类型", ["最近N场", "日期范围"], horizontal=True)
    d2_range = None
    last_n = 0
    if s2_type == "日期范围":
        d2_range = st.sidebar.date_input("日期范围 2", [date(2021, 1, 14), date(2021, 3, 1)])
    else:
        last_n = st.sidebar.number_input("最近 N 场", 1, 82, 10)

    if st.sidebar.button("执行切片 ✂️"):
        run_analysis = True
        with st.spinner("正在切割赛季数据..."):
            p1_data = engine.get_full_profile(p_name, season, date_range=d1_range)
            # 切片2：可能是日期，可能是Last N
            p2_data = engine.get_full_profile(p_name, season, date_range=d2_range, last_n=last_n)


# ==========================================
# 4. 可视化渲染 (Visualization)
# ==========================================
def check_error(data):
    if data and "error" in data:
        st.markdown(f"""<div class="error-box">❌ {data['error']}</div>""", unsafe_allow_html=True)
        return True
    return False


def render_metric_card(label, v1, v2, suffix="", is_pct=False):
    """渲染高颜值对比卡片"""
    if v1 is None: v1 = 0
    if v2 is None: v2 = 0

    delta = v2 - v1
    delta_cls = "stat-delta-up" if delta >= 0 else "stat-delta-down"

    if is_pct:
        v1_s = f"{v1 * 100:.1f}%"
        v2_s = f"{v2 * 100:.1f}%"
        d_s = f"{delta * 100:+.1f}%"
    else:
        v1_s = f"{v1:.1f}"
        v2_s = f"{v2:.1f}"
        d_s = f"{delta:+.1f}"

    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-label">{label}</div>
        <div class="stat-value">{v2_s} <span style="font-size:14px; color:#666;">vs {v1_s}</span></div>
        <div class="{delta_cls}">{d_s} {suffix}</div>
    </div>
    """, unsafe_allow_html=True)


if run_analysis:
    # 错误检查
    err1 = check_error(p1_data)
    err2 = check_error(p2_data)

    if not err1 and not err2 and p1_data and p2_data:
        # 头部标题
        st.title("📊 PLAYER COMPARISON REPORT")
        name1, sea1 = p1_data['meta']['name'], p1_data['meta']['season']
        name2, sea2 = p2_data['meta']['name'], p2_data['meta']['season']
        st.markdown(f"**{name1} ({sea1})** <span style='color:#666; margin:0 10px'>vs</span> **{name2} ({sea2})**",
                    unsafe_allow_html=True)

        st.markdown("---")

        # --- 1. 核心数据 (Per 100) ---
        st.subheader("1. 核心战力 (Per 100 Possessions)")
        col1, col2, col3, col4 = st.columns(4)
        b1, b2 = p1_data['base'], p2_data['base']

        with col1:
            render_metric_card("得分 (PTS/100)", b1.get('PTS_100'), b2.get('PTS_100'))
        with col2:
            render_metric_card("真实命中率 (TS%)", b1.get('TS_PCT'), b2.get('TS_PCT'), is_pct=True)
        with col3:
            render_metric_card("助攻 (AST/100)", b1.get('AST_100'), b2.get('AST_100'))
        with col4:
            render_metric_card("球权使用率 (USG%)", b1.get('USG_PCT'), b2.get('USG_PCT'), is_pct=True)

        # --- 2. 雷达图 ---
        st.subheader("2. 综合能力雷达")
        categories = ['得分(PTS)', '组织(AST)', '篮板(REB)', '防守(STL+BLK)', '效率(TS%)', '球权(USG%)']


        def norm(val, limit):
            return min((val or 0) / limit, 1.0)


        def get_radar_data(base):
            return [
                norm(base.get('PTS_100'), 45),
                norm(base.get('AST_100'), 15),
                norm(base.get('REB_100'), 18),
                norm((base.get('STL_100', 0) + base.get('BLK_100', 0)), 5),
                norm(base.get('TS_PCT'), 0.70),
                norm(base.get('USG_PCT'), 0.40)
            ]


        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=get_radar_data(b1), theta=categories, fill='toself', name=f"{name1} (A)",
                                      line_color='#3B82F6'))
        fig.add_trace(go.Scatterpolar(r=get_radar_data(b2), theta=categories, fill='toself', name=f"{name2} (B)",
                                      line_color='#EF4444'))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1], showticklabels=False), bgcolor='#1F2937'),
            paper_bgcolor='rgba(0,0,0,0)', font_color='white',
            margin=dict(t=20, b=20), legend=dict(orientation="h")
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- 3. 风格与机制 ---
        c_left, c_right = st.columns(2)

        with c_left:
            st.subheader("3. 战术风格 (Synergy)")
            if not p1_data['synergy'] and not p2_data['synergy']:
                st.info("⚠️ 无 Synergy 数据 (仅支持 2015-16 后)")
            else:
                s_data = []
                for k in p1_data['synergy']:
                    s_data.append({"Type": k, "Freq": p1_data['synergy'][k]['Freq'], "Player": "A"})
                for k in p2_data['synergy']:
                    s_data.append({"Type": k, "Freq": p2_data['synergy'][k]['Freq'], "Player": "B"})

                if s_data:
                    sdf = pd.DataFrame(s_data)
                    fig_s = px.bar(sdf, x="Freq", y="Type", color="Player", barmode="group", orientation='h',
                                   color_discrete_map={"A": "#3B82F6", "B": "#EF4444"})
                    fig_s.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig_s, use_container_width=True)
                else:
                    st.warning("数据不完整")

        with c_right:
            st.subheader("4. 投篮机制 (Tracking)")
            if not p1_data['tracking'] and not p2_data['tracking']:
                st.info("⚠️ 无 Tracking 数据 (仅支持 2013-14 后)")
            else:
                # 简单表格展示
                t1, t2 = p1_data['tracking'], p2_data['tracking']
                metrics = [
                    ("运球投三分 (Pull-up 3P%)", "Pull-up 3P%"),
                    ("接球投三分 (C&S 3P%)", "C&S 3P%"),
                    ("运球投频率 (Pull-up Freq)", "Pull-up Freq"),
                    ("接球投频率 (C&S Freq)", "C&S Freq")
                ]

                rows = []
                for label, key in metrics:
                    val1 = t1.get(key)
                    val2 = t2.get(key)
                    rows.append({
                        "指标": label,
                        f"{name1} (A)": f"{val1 * 100:.1f}%" if val1 is not None else "-",
                        f"{name2} (B)": f"{val2 * 100:.1f}%" if val2 is not None else "-"
                    })

                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)