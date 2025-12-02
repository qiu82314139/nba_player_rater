import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import time
import numpy as np

# NBA API Imports
from nba_api.stats.endpoints import (
    leaguedashplayerstats,
    leaguedashptdefend,
    leaguehustlestatsplayer
)
from nba_api.stats.static import teams

# ==========================================
# 配置区
# ==========================================
FALLBACK_HEADSHOT_URL = "https://i.imgur.com/WxNkK7J.png"

# ==========================================
# 1. 全局配置与视觉设计
# ==========================================
st.set_page_config(
    page_title="NBA Two-Way Power Ranking Pro",
    page_icon="👑",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全局深色背景 */
    .stApp { background-color: #0B0E11; color: #E5E7EB; }

    /* 标题样式 */
    h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 900; letter-spacing: -1px; 
         background: -webkit-linear-gradient(45deg, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    h2, h3 { color: #FFFFFF; font-weight: 800; }

    /* 卡片容器 */
    .card-container {
        border-radius: 12px; padding: 15px; margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4); transition: transform 0.2s;
        border: 1px solid rgba(255,255,255,0.1); position: relative; overflow: hidden;
    }
    .card-container:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.6); }

    /* 卡片配色 */
    .purple-card { background: linear-gradient(135deg, #2e1065, #4c1d95); border-left: 6px solid #a855f7; }
    .purple-rank { color: #d8b4fe; font-size: 28px; font-weight: 900; font-style: italic; text-shadow: 0 0 10px rgba(168, 85, 247, 0.5); }

    .red-card { background: linear-gradient(135deg, #450a0a, #7f1d1d); border-left: 6px solid #ef4444; }
    .red-rank { color: #fca5a5; font-size: 24px; font-weight: 900; font-style: italic; }

    .blue-card { background: linear-gradient(135deg, #172554, #1e3a8a); border-left: 6px solid #3b82f6; }
    .blue-rank { color: #93c5fd; font-size: 24px; font-weight: 900; font-style: italic; }

    /* 数据排版 */
    .stat-row { display: flex; justify-content: space-between; margin-top: 12px; }
    .stat-item { text-align: center; }
    .stat-val { font-weight: bold; color: #fff; font-size: 18px; }
    .stat-lbl { color: #9ca3af; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }

    /* 头像与名字 */
    .player-header { display: flex; align-items: center; }
    .player-headshot { width: 60px; height: 44px; border-radius: 6px; margin-right: 12px; object-fit: cover; background-color: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); }
    .team-badge { font-size: 12px; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: #ccc; margin-left: auto; }

    /* 总分徽章 */
    .total-score { position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.1); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; color: #fff; border: 1px solid rgba(255,255,255,0.2); }

    section[data-testid="stSidebar"] { background-color: #0f1115; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 核心算法引擎 (Power Engine V5.4 - 修复版)
# ==========================================
class PowerRankingEngine:
    def __init__(self):
        # 自动判断赛季
        today = datetime.now()
        if today.month >= 10:
            start_year = today.year
            end_year = (today.year + 1) % 100
        else:
            start_year = today.year - 1
            end_year = today.year % 100
        self.current_season = f"{start_year}-{end_year:02d}"

    @st.cache_data(ttl=3600)
    def fetch_data(_self, season, date_from=None, date_to=None):
        try:
            time.sleep(0.2)
            # 1. Base Stats
            base = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, date_from_nullable=date_from, date_to_nullable=date_to,
                measure_type_detailed_defense='Base', per_mode_detailed='PerGame'
            ).get_data_frames()[0]

            # 2. Advanced Stats
            adv = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, date_from_nullable=date_from, date_to_nullable=date_to,
                measure_type_detailed_defense='Advanced', per_mode_detailed='PerGame'
            ).get_data_frames()[0]

            if base.empty: return pd.DataFrame()

            # --- 3. Defense (关键修复) ---
            defense = pd.DataFrame()
            try:
                # 尝试拉取赛季平均防守数据
                time.sleep(0.3)
                defense = leaguedashptdefend.LeagueDashPtDefend(
                    season=season,
                    defense_category='Overall',
                    per_mode_simple='PerGame',
                    season_type_all_star='Regular Season'
                ).get_data_frames()[0]

                # 【核心修复点】列名标准化
                if not defense.empty:
                    defense.columns = [c.upper() for c in defense.columns]

                    # 1. 修复 ID 列名
                    if 'CLOSE_DEF_PERSON_ID' in defense.columns:
                        defense = defense.rename(columns={'CLOSE_DEF_PERSON_ID': 'PLAYER_ID'})

                    # 2. 修复干扰投篮列名 (D_FGA -> CONTESTED_SHOTS)
                    # 如果 API 返回的是 D_FGA，我们就把它改名为 CONTESTED_SHOTS，这样后面的代码就能识别了
                    if 'D_FGA' in defense.columns:
                        defense = defense.rename(columns={'D_FGA': 'CONTESTED_SHOTS'})

                    # 3. 顺便保留降准率 (Diff%)，以后可能有用
                    if 'PCT_PLUSMINUS' not in defense.columns:
                        defense['PCT_PLUSMINUS'] = 0.0
            except:
                pass

            # --- 4. Hustle ---
            hustle = pd.DataFrame()
            try:
                time.sleep(0.3)
                hustle = leaguehustlestatsplayer.LeagueHustleStatsPlayer(
                    season=season, per_mode_time='PerGame', season_type_all_star='Regular Season'
                ).get_data_frames()[0]
                if not hustle.empty: hustle.columns = [c.upper() for c in hustle.columns]
            except:
                pass

            # --- Merge ---
            # 统一列名大写
            base.columns = [c.upper() for c in base.columns]
            adv.columns = [c.upper() for c in adv.columns]

            # 移除 BLK_PCT 等不稳定列，只取最稳的
            cols_adv = ['PLAYER_ID', 'DEF_RATING', 'OFF_RATING', 'TS_PCT', 'USG_PCT',
                        'PACE', 'PIE', 'AST_PCT', 'AST_TO', 'DREB_PCT']
            cols_adv = [c for c in cols_adv if c in adv.columns]  # 双重保险

            merged = pd.merge(base, adv[cols_adv], on='PLAYER_ID', suffixes=('', '_ADV'))

            # Merge Defense (此时 defense 里面已经有 CONTESTED_SHOTS 了)
            if not defense.empty and 'PLAYER_ID' in defense.columns:
                # 再次确认列是否存在
                col_to_merge = 'CONTESTED_SHOTS' if 'CONTESTED_SHOTS' in defense.columns else None

                if col_to_merge:
                    merged = pd.merge(merged, defense[['PLAYER_ID', col_to_merge]], on='PLAYER_ID', how='left')
                else:
                    merged['CONTESTED_SHOTS'] = 0
            else:
                merged['CONTESTED_SHOTS'] = 0

            # Merge Hustle
            if not hustle.empty and 'PLAYER_ID' in hustle.columns:
                h_cols = ['PLAYER_ID']
                if 'DEFLECTIONS' in hustle.columns: h_cols.append('DEFLECTIONS')
                if 'CHARGES_DRAWN' in hustle.columns: h_cols.append('CHARGES_DRAWN')
                merged = pd.merge(merged, hustle[h_cols], on='PLAYER_ID', how='left')
            else:
                merged['DEFLECTIONS'] = 0
                merged['CHARGES_DRAWN'] = 0

            return merged.fillna(0)

        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            # 打印错误堆栈，方便你在终端看到具体哪里错了
            import traceback
            print(traceback.format_exc())
            return pd.DataFrame()
    def calculate_scores(self, df, min_gp=1, min_min=0, off_weight=0.6):
        if df.empty: return df, 0

        # 1. Filter
        df = df[df['GP'] >= min_gp]
        df = df[df['MIN'] >= min_min]
        if df.empty: return df, 0

        # 2. Base Calc
        # 修复 AST/TO
        if 'AST_TO' in df.columns:
            df['AST_TO'] = df['AST_TO'].replace([np.inf, -np.inf], 5.0).fillna(0)
        else:
            df['AST_TO'] = 0

        total_pts = (df['PTS'] * df['GP']).sum()
        total_fga = (df['FGA'] * df['GP']).sum()
        total_fta = (df['FTA'] * df['GP']).sum()

        league_avg_ts = 0.58
        if total_fga > 0: league_avg_ts = total_pts / (2 * (total_fga + 0.44 * total_fta))

        # 3. Advanced Metrics
        df['TSA'] = df['FGA'] + 0.44 * df['FTA']
        df['TS_ADD'] = df['PTS'] - (2 * df['TSA'] * league_avg_ts)
        df['GmSc'] = (df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM']) +
                      0.7 * df['OREB'] + 0.3 * df['DREB'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK'] -
                      0.4 * df['PF'] - df['TOV'])

        def normalize(series):
            min_val = series.min()
            max_val = series.max()
            if max_val == min_val: return 0.5
            return (series - min_val) / (max_val - min_val)

        # 4. 防守算法 (Plan B 修复版)
        has_contest = df['CONTESTED_SHOTS'].max() > 0

        if has_contest:
            # Plan A: 完美模式 (有干扰数据)
            s_contest = normalize(df['CONTESTED_SHOTS'])
            s_blk = normalize(df['BLK'])
            # 拼抢兼容
            if df['DEFLECTIONS'].max() > 0:
                s_hustle = normalize(df['DEFLECTIONS'] + df['CHARGES_DRAWN'] * 2)
                s_box = normalize(df['STL'] + df['DREB'] * 0.5)
                df['Def_Score_Raw'] = (s_contest * 0.40 + s_hustle * 0.20 + s_blk * 0.20 + s_box * 0.20)
            else:
                s_box = normalize(df['STL'] + df['DREB'] * 0.5)
                df['Def_Score_Raw'] = (s_contest * 0.50 + s_blk * 0.25 + s_box * 0.25)
        else:
            # Plan B: 替代方案 (无 Tracking 数据)
            # 【修复点】直接使用基础数据 BLK/STL 替代 BLK_PCT/STL_PCT，效果一样且稳定
            s_blk = normalize(df['BLK'])  # 护框
            s_stl = normalize(df['STL'])  # 侵略性

            # 防守篮板率 (如果 DREB_PCT 不存在，用 DREB 代替)
            if 'DREB_PCT' in df.columns:
                s_dreb = normalize(df['DREB_PCT'])
            else:
                s_dreb = normalize(df['DREB'])

            # 防守效率 (越低越好)
            clean_def_rtg = df['DEF_RATING'].replace(0, df['DEF_RATING'].mean())
            min_rtg = clean_def_rtg.min()
            max_rtg = clean_def_rtg.max()
            s_def_rtg = (max_rtg - clean_def_rtg) / (max_rtg - min_rtg)

            # 权重: 盖帽30% + 抢断20% + 篮板20% + 效率30%
            df['Def_Score_Raw'] = (s_blk * 0.30 + s_stl * 0.20 + s_dreb * 0.20 + s_def_rtg * 0.30)

            if not st.session_state.get('def_warned', False):
                st.toast("⚠️ 干扰投篮数据不可用，已启用【高阶效率】替代模型", icon="🛡️")
                st.session_state['def_warned'] = True

        df['Def_Score'] = df['Def_Score_Raw'] * 100

        # 5. 进攻算法
        score_scoring = (normalize(df['PTS']) * 0.6 + normalize(df['GmSc']) * 0.4)

        # AST_PCT/OFF_RATING 兼容性检查
        s_ast = normalize(df['AST_PCT']) if 'AST_PCT' in df.columns else normalize(df['AST'])
        s_ortg = normalize(df['OFF_RATING']) if 'OFF_RATING' in df.columns else 0.5

        score_lift = (s_ast * 0.4 + normalize(df['AST_TO']) * 0.3 + s_ortg * 0.3)
        score_efficiency = normalize(df['TS_ADD'])

        df['Off_Score_Raw'] = (score_scoring * 0.50 + score_lift * 0.30 + score_efficiency * 0.20)
        df['Off_Score'] = df['Off_Score_Raw'] * 100

        # 6. 总分
        def_weight = 1.0 - off_weight
        df['Total_Score'] = (normalize(df['Off_Score']) * off_weight +
                             normalize(df['Def_Score']) * def_weight) * 100

        # Meta
        df['HEADSHOT_URL'] = df['PLAYER_ID'].apply(
            lambda x: f"https://cdn.nba.com/headshots/nba/latest/260x190/{x}.png")
        df['Rank_Total'] = df['Total_Score'].rank(ascending=False, method='min')
        df['Rank_Off'] = df['Off_Score'].rank(ascending=False, method='min')
        df['Rank_Def'] = df['Def_Score'].rank(ascending=False, method='min')

        return df, league_avg_ts

engine = PowerRankingEngine()

# ==========================================
# 3. 侧边栏
# ==========================================
st.sidebar.header(f"🎛️ 实力榜控制台 ({engine.current_season})")

# Time
time_opt = st.sidebar.selectbox("📅 时间范围", ["本赛季至今", "最近7天", "最近15天", "最近30天", "自定义"])
date_to = datetime.now()
date_from = date(2025, 10, 22)

if time_opt == "最近7天":
    date_from = date_to - timedelta(days=7)
elif time_opt == "最近15天":
    date_from = date_to - timedelta(days=15)
elif time_opt == "最近30天":
    date_from = date_to - timedelta(days=30)
elif time_opt == "自定义":
    c1, c2 = st.sidebar.columns(2)
    date_from = c1.date_input("开始", date_to - timedelta(days=7))
    date_to = c2.date_input("结束", date_to)

d_str_from = date_from.strftime("%m/%d/%Y")
d_str_to = date_to.strftime("%m/%d/%Y")

# Filters
st.sidebar.markdown("---")
st.sidebar.caption("🔓 样本筛选")
f_gp = st.sidebar.number_input("最少场次", 0, 82, 1)
f_min = st.sidebar.slider("场均时间 (MIN) >=", 0, 48, 15)
f_usg = st.sidebar.slider("球权使用率 (USG%) >=", 0, 40, 15)

# Weights
st.sidebar.markdown("---")
with st.sidebar.expander("⚖️ 算法权重"):
    off_w = st.slider("进攻权重", 0.0, 1.0, 0.6, 0.1)

# Team
f_team = st.sidebar.selectbox("球队", ["全联盟"] + [t['full_name'] for t in teams.get_teams()])

btn_run = st.sidebar.button("计算实力榜 🚀", type="primary")

# ==========================================
# 4. 主界面
# ==========================================
if btn_run:
    with st.spinner("正在提取数据..."):
        raw_df = engine.fetch_data(engine.current_season, d_str_from, d_str_to)

        if not raw_df.empty:
            if f_team != "全联盟":
                found = [t for t in teams.get_teams() if t['full_name'] == f_team]
                if found:
                    raw_df = raw_df[raw_df['TEAM_ABBREVIATION'] == found[0]['abbreviation']]

            df, avg_ts = engine.calculate_scores(raw_df, f_gp, f_min, off_w)
            df = df[df['USG_PCT'] * 100 >= f_usg]

            if df.empty:
                st.warning("筛选后无数据。")
                st.stop()

            st.title(f"🏆 NBA 攻防一体实力榜")
            st.markdown(f"**周期：** {d_str_from} - {d_str_to} | **样本：** {len(df)} 名球员")

            tab1, tab2, tab3 = st.tabs(["🟣 攻防一体榜 (MVP)", "🔴 进攻统治榜", "🔵 防守铁闸榜"])


            def plot_scatter(data, x_col, y_col, size_col, color_col, x_lbl, y_lbl, top_n=30):
                top_p = data.head(top_n)
                fig = px.scatter(
                    data, x=x_col, y=y_col, size=size_col, color=color_col,
                    hover_name="PLAYER_NAME", color_continuous_scale="RdBu_r", opacity=0.3, size_max=18
                )
                imgs = []
                x_range = data[x_col].max() - data[x_col].min()
                y_range = data[y_col].max() - data[y_col].min()
                if y_range == 0: y_range = 1
                if x_range == 0: x_range = 1

                for _, row in top_p.iterrows():
                    imgs.append(dict(
                        source=row['HEADSHOT_URL'], xref="x", yref="y",
                        x=row[x_col], y=row[y_col], sizex=x_range * 0.06, sizey=y_range * 0.08,
                        xanchor="center", yanchor="middle", layer="above", opacity=1.0
                    ))
                fig.update_layout(
                    plot_bgcolor='#1F2937', paper_bgcolor='#0B0E11', font=dict(color='white'),
                    height=650, images=imgs, showlegend=False, xaxis_title=x_lbl, yaxis_title=y_lbl,
                    coloraxis_showscale=False
                )
                return fig


            with tab1:
                c_chart, c_list = st.columns([2, 1])
                df_total = df.sort_values(by='Total_Score', ascending=False)
                with c_chart:
                    st.subheader("攻防象限")
                    fig1 = plot_scatter(df_total, "Def_Score", "Off_Score", "Total_Score", "Total_Score", "防守评分",
                                        "进攻评分")
                    fig1.add_hline(y=50, line_dash="dot", line_color="#555");
                    fig1.add_vline(x=50, line_dash="dot", line_color="#555")
                    st.plotly_chart(fig1, use_container_width=True)
                with c_list:
                    st.subheader("Top 20")
                    for i, r in df_total.head(20).iterrows():
                        st.markdown(f"""
                        <div class="card-container purple-card">
                            <div class="total-score">{r['Total_Score']:.0f}</div>
                            <div class="player-header">
                                <img src="{r['HEADSHOT_URL']}" onerror="this.src='{FALLBACK_HEADSHOT_URL}'" class="player-headshot">
                                <div><div class="purple-rank">#{int(r['Rank_Total'])} {r['PLAYER_NAME']}</div><div class="team-badge">{r['TEAM_ABBREVIATION']}</div></div>
                            </div>
                            <div class="stat-row">
                                <div class="stat-item"><div class="stat-val">{r['PTS']:.1f}</div><div class="stat-lbl">PTS</div></div>
                                <div class="stat-item"><div class="stat-val">{r['Off_Score']:.0f}</div><div class="stat-lbl">OFF</div></div>
                                <div class="stat-item"><div class="stat-val">{r['Def_Score']:.0f}</div><div class="stat-lbl">DEF</div></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

            with tab2:
                c_chart, c_list = st.columns([2, 1])
                df_off = df.sort_values(by='Off_Score', ascending=False)
                with c_chart:
                    st.subheader("进攻矩阵")
                    fig2 = plot_scatter(df_off, "USG_PCT", "TS_PCT", "PTS", "Off_Score", "球权 (USG%)",
                                        "真实命中率 (TS%)")
                    st.plotly_chart(fig2, use_container_width=True)
                with c_list:
                    st.subheader("进攻 Top 20")
                    for i, r in df_off.head(20).iterrows():
                        st.markdown(f"""
                        <div class="card-container red-card">
                            <div class="player-header">
                                <img src="{r['HEADSHOT_URL']}" onerror="this.src='{FALLBACK_HEADSHOT_URL}'" class="player-headshot">
                                <div><div class="red-rank">#{int(r['Rank_Off'])} {r['PLAYER_NAME']}</div></div>
                            </div>
                            <div class="stat-row">
                                <div class="stat-item"><div class="stat-val">{r['PTS']:.1f}</div><div class="stat-lbl">PTS</div></div>
                                <div class="stat-item"><div class="stat-val">{r['TS_PCT'] * 100:.1f}%</div><div class="stat-lbl">TS%</div></div>
                                <div class="stat-item"><div class="stat-val">{r['AST_PCT'] * 100:.1f}%</div><div class="stat-lbl">AST%</div></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

            with tab3:
                c_chart, c_list = st.columns([2, 1])
                df_def = df.sort_values(by='Def_Score', ascending=False)
                with c_chart:
                    st.subheader("防守破坏力")
                    df_def['Hustle'] = df_def['DEFLECTIONS'] + df_def['CHARGES_DRAWN']
                    fig3 = plot_scatter(df_def, "CONTESTED_SHOTS", "Hustle", "BLK", "Def_Score", "干扰投篮", "积极拼抢")
                    st.plotly_chart(fig3, use_container_width=True)
                with c_list:
                    st.subheader("防守 Top 20")
                    for i, r in df_def.head(20).iterrows():
                        st.markdown(f"""
                        <div class="card-container blue-card">
                            <div class="player-header">
                                <img src="{r['HEADSHOT_URL']}" onerror="this.src='{FALLBACK_HEADSHOT_URL}'" class="player-headshot">
                                <div><div class="blue-rank">#{int(r['Rank_Def'])} {r['PLAYER_NAME']}</div></div>
                            </div>
                            <div class="stat-row">
                                <div class="stat-item"><div class="stat-val">{r['CONTESTED_SHOTS']:.1f}</div><div class="stat-lbl">干扰</div></div>
                                <div class="stat-item"><div class="stat-val">{r['DEFLECTIONS']:.1f}</div><div class="stat-lbl">截断</div></div>
                                <div class="stat-item"><div class="stat-val">{r['BLK']:.1f}</div><div class="stat-lbl">冒</div></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

            # --- 全量数据表 ---
            st.markdown("---")
            with st.expander("📊 查看/下载 完整数据表 (支持排序)"):
                col_map = {
                    'PLAYER_NAME': '球员姓名', 'TEAM_ABBREVIATION': '球队', 'GP': '场次', 'MIN': '时间',
                    'Total_Score': '💎综合分', 'Off_Score': '🔴进攻分', 'Def_Score': '🔵防守分',
                    'PTS': '得分', 'TS_PCT': '真实命中率%', 'USG_PCT': '球权%', 'AST_PCT': '助攻率%',
                    'TS_ADD': 'TS增益', 'CONTESTED_SHOTS': '干扰投篮', 'DEFLECTIONS': '截断',
                    'STL': '抢断', 'BLK': '盖帽', 'DEF_RATING': '防守效率'
                }
                display_cols = list(col_map.keys())
                valid_cols = [c for c in display_cols if c in df.columns]
                df_show = df[valid_cols].rename(columns=col_map).copy()

                for col in ['真实命中率%', '球权%', '助攻率%']:
                    if col in df_show.columns: df_show[col] = (df_show[col] * 100).round(1)
                for col in ['💎综合分', '🔴进攻分', '🔵防守分', 'TS增益']:
                    if col in df_show.columns: df_show[col] = df_show[col].round(1)

                st.dataframe(df_show.sort_values(by='💎综合分', ascending=False), use_container_width=True, height=600)

        else:
            st.warning("无数据返回。")