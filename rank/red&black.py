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
    leaguehustlestatsplayer,
    synergyplaytypes
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
    .stApp { background-color: #0B0E11; color: #E5E7EB; }
    h1 { font-family: 'Helvetica Neue', sans-serif; font-weight: 900; letter-spacing: -1px; 
         background: -webkit-linear-gradient(45deg, #a855f7, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    h2, h3 { color: #FFFFFF; font-weight: 800; }
    .card-container {
        border-radius: 12px; padding: 15px; margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4); transition: transform 0.2s;
        border: 1px solid rgba(255,255,255,0.1); position: relative; overflow: hidden;
    }
    .card-container:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.6); }
    .purple-card { background: linear-gradient(135deg, #2e1065, #4c1d95); border-left: 6px solid #a855f7; }
    .purple-rank { color: #d8b4fe; font-size: 28px; font-weight: 900; font-style: italic; text-shadow: 0 0 10px rgba(168, 85, 247, 0.5); }
    .red-card { background: linear-gradient(135deg, #450a0a, #7f1d1d); border-left: 6px solid #ef4444; }
    .red-rank { color: #fca5a5; font-size: 24px; font-weight: 900; font-style: italic; }
    .blue-card { background: linear-gradient(135deg, #172554, #1e3a8a); border-left: 6px solid #3b82f6; }
    .blue-rank { color: #93c5fd; font-size: 24px; font-weight: 900; font-style: italic; }
    .stat-row { display: flex; justify-content: space-between; margin-top: 12px; }
    .stat-item { text-align: center; }
    .stat-val { font-weight: bold; color: #fff; font-size: 18px; }
    .stat-lbl { color: #9ca3af; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
    .player-header { display: flex; align-items: center; }
    .player-headshot { width: 60px; height: 44px; border-radius: 6px; margin-right: 12px; object-fit: cover; background-color: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); }
    .team-badge { font-size: 12px; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: #ccc; margin-left: auto; }
    .total-score { position: absolute; top: 10px; right: 10px; background: rgba(255,255,255,0.1); border-radius: 50%; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; color: #fff; border: 1px solid rgba(255,255,255,0.2); }
    section[data-testid="stSidebar"] { background-color: #0f1115; }
    .status-ok { color: #4ade80; font-size: 12px; }
    .status-err { color: #f87171; font-size: 12px; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. 核心算法引擎 (Power Engine V6.3)
# ==========================================
class PowerRankingEngine:
    def __init__(self):
        today = datetime.now()
        if today.month >= 10:
            start_year = today.year
            end_year = (today.year + 1) % 100
        else:
            start_year = today.year - 1
            end_year = today.year % 100
        self.current_season = f"{start_year}-{end_year:02d}"
        self.status = {"Base": False, "Defense": False, "Hustle": False, "Iso": False}

    @st.cache_data(ttl=3600)
    def fetch_data(_self, season, date_from=None, date_to=None):
        _self.status = {"Base": False, "Defense": False, "Hustle": False, "Iso": False}
        try:
            # 1. Base + Advanced Stats
            time.sleep(0.2)
            base = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, date_from_nullable=date_from, date_to_nullable=date_to,
                measure_type_detailed_defense='Base', per_mode_detailed='PerGame'
            ).get_data_frames()[0]

            time.sleep(0.2)
            adv = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, date_from_nullable=date_from, date_to_nullable=date_to,
                measure_type_detailed_defense='Advanced', per_mode_detailed='PerGame'
            ).get_data_frames()[0]

            if base.empty: return pd.DataFrame()
            _self.status["Base"] = True

            # 2. Defense (干扰投篮)
            defense = pd.DataFrame()
            try:
                # 尝试 A: 精确日期
                time.sleep(0.2)
                defense = leaguedashptdefend.LeagueDashPtDefend(
                    season=season, date_from_nullable=date_from, date_to_nullable=date_to,
                    defense_category='Overall', per_mode_simple='PerGame', season_type_all_star='Regular Season'
                ).get_data_frames()[0]
                if defense.empty: raise ValueError
            except:
                # 尝试 B: 赛季平均
                try:
                    time.sleep(0.2)
                    defense = leaguedashptdefend.LeagueDashPtDefend(
                        season=season, defense_category='Overall', per_mode_simple='PerGame',
                        season_type_all_star='Regular Season'
                    ).get_data_frames()[0]
                except:
                    pass

            if not defense.empty:
                defense.columns = [c.upper() for c in defense.columns]
                if 'CLOSE_DEF_PERSON_ID' in defense.columns: defense = defense.rename(
                    columns={'CLOSE_DEF_PERSON_ID': 'PLAYER_ID'})
                if 'D_FGA' in defense.columns: defense = defense.rename(columns={'D_FGA': 'CONTESTED_SHOTS'})
                _self.status["Defense"] = True

            # 3. Hustle (截断)
            hustle = pd.DataFrame()
            try:
                time.sleep(0.2)
                hustle = leaguehustlestatsplayer.LeagueHustleStatsPlayer(
                    season=season, per_mode_time='PerGame', season_type_all_star='Regular Season'
                ).get_data_frames()[0]
                if not hustle.empty:
                    hustle.columns = [c.upper() for c in hustle.columns]
                    _self.status["Hustle"] = True
            except:
                pass

            # 4. Synergy Isolation
            iso_def = pd.DataFrame()
            try:
                time.sleep(0.2)
                iso_data = synergyplaytypes.SynergyPlayTypes(
                    player_or_team_abbreviation='P', play_type_nullable='Isolation', season=season,
                    type_grouping_nullable='Defensive', per_mode_simple='PerGame', season_type_all_star='Regular Season'
                ).get_data_frames()[0]
                if not iso_data.empty:
                    iso_cols = [c for c in ['PLAYER_ID', 'PPP'] if c in iso_data.columns]
                    iso_def = iso_data[iso_cols].rename(columns={'PPP': 'ISO_PPP'})
                    _self.status["Iso"] = True
            except:
                pass

            # --- Merge Logic ---
            cols_adv = ['PLAYER_ID', 'DEF_RATING', 'OFF_RATING', 'TS_PCT', 'USG_PCT', 'PACE', 'PIE', 'AST_PCT',
                        'AST_TO']
            base.columns = [c.upper() for c in base.columns]
            adv.columns = [c.upper() for c in adv.columns]

            merged = pd.merge(base, adv[cols_adv], on='PLAYER_ID', suffixes=('', '_ADV'))

            # Merge Defense
            if not defense.empty and 'PLAYER_ID' in defense.columns:
                col = 'CONTESTED_SHOTS' if 'CONTESTED_SHOTS' in defense.columns else None
                if col:
                    merged = pd.merge(merged, defense[['PLAYER_ID', col]], on='PLAYER_ID', how='left')
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

            # Merge Iso
            if not iso_def.empty:
                merged = pd.merge(merged, iso_def, on='PLAYER_ID', how='left')
            else:
                merged['ISO_PPP'] = 0.95

            return merged.fillna(0)

        except Exception as e:
            st.error(f"Data Fetch Error: {e}")
            return pd.DataFrame()

    def calculate_scores(self, df, min_gp=1, min_min=0, off_weight=0.6):
        if df.empty: return df, 0

        df = df[df['GP'] >= min_gp]
        df = df[df['MIN'] >= min_min]
        if df.empty: return df, 0

        # Base Calc
        df['AST_TO'] = df['AST_TO'].replace([np.inf, -np.inf], 5.0).fillna(0)
        total_pts = (df['PTS'] * df['GP']).sum()
        total_fga = (df['FGA'] * df['GP']).sum()
        total_fta = (df['FTA'] * df['GP']).sum()
        league_avg_ts = 0.58
        if total_fga > 0: league_avg_ts = total_pts / (2 * (total_fga + 0.44 * total_fta))

        # Metrics
        df['TSA'] = df['FGA'] + 0.44 * df['FTA']
        df['TS_ADD'] = df['PTS'] - (2 * df['TSA'] * league_avg_ts)
        df['GmSc'] = (df['PTS'] + 0.4 * df['FGM'] - 0.7 * df['FGA'] - 0.4 * (df['FTA'] - df['FTM']) +
                      0.7 * df['OREB'] + 0.3 * df['DREB'] + df['STL'] + 0.7 * df['AST'] + 0.7 * df['BLK'] -
                      0.4 * df['PF'] - df['TOV'])

        # Stocks
        df['STOCKS'] = df['STL'] + df['BLK']

        def normalize(series):
            min_val = series.min();
            max_val = series.max()
            if max_val == min_val: return 0.5
            return (series - min_val) / (max_val - min_val)

        def normalize_inv(series):
            min_val = series.min();
            max_val = series.max()
            if max_val == min_val: return 0.5
            return (max_val - series) / (max_val - min_val)

        # ==========================================
        # 🛡️ 防守算法 V6.3 (权重调整)
        # ==========================================

        # 1. 干扰 (Contest): 权重降至 30%
        s_contest = normalize(df['CONTESTED_SHOTS'])

        # 2. 破坏力 (Disruption): 权重维持 35%
        # 包含：抢断、盖帽、截断、造犯规
        raw_disruption = (df['STL'] * 1.5) + (df['BLK'] * 1.5) + (df['DEFLECTIONS'] * 1.0) + (df['CHARGES_DRAWN'] * 2.0)
        s_disruption = normalize(raw_disruption)

        # 3. 防守质量 (Quality): 权重升至 35% (强调防守效果)
        # 包含：防守效率(DefRtg) + 单防能力(Iso PPP)
        if 'ISO_PPP' not in df.columns: df['ISO_PPP'] = 0.95
        clean_def_rtg = df['DEF_RATING'].replace(0, df['DEF_RATING'].mean())
        s_quality = (normalize_inv(clean_def_rtg) * 0.6 + normalize_inv(df['ISO_PPP']) * 0.4)

        # 合成防守分
        df['Def_Score_Raw'] = (s_contest * 0.30 + s_disruption * 0.35 + s_quality * 0.35)
        df['Def_Score'] = df['Def_Score_Raw'] * 100

        # ==========================================
        # 🏀 进攻算法 V5.0 (保持)
        # ==========================================
        score_scoring = (normalize(df['PTS']) * 0.6 + normalize(df['GmSc']) * 0.4)
        score_lift = (
                    normalize(df['AST_PCT']) * 0.4 + normalize(df['AST_TO']) * 0.3 + normalize(df['OFF_RATING']) * 0.3)
        score_efficiency = normalize(df['TS_ADD'])

        df['Off_Score_Raw'] = (score_scoring * 0.50 + score_lift * 0.30 + score_efficiency * 0.20)
        df['Off_Score'] = df['Off_Score_Raw'] * 100

        # 总分
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

st.sidebar.markdown("---")
st.sidebar.caption("🔓 样本筛选")
f_gp = st.sidebar.number_input("最少场次", 0, 82, 1)
f_min = st.sidebar.slider("场均时间 (MIN) >=", 0, 48, 15)
f_usg = st.sidebar.slider("球权使用率 (USG%) >=", 0, 40, 15)

st.sidebar.markdown("---")
with st.sidebar.expander("⚖️ 算法权重"):
    off_w = st.slider("进攻权重", 0.0, 1.0, 0.6, 0.1)

f_team = st.sidebar.selectbox("球队", ["全联盟"] + [t['full_name'] for t in teams.get_teams()])

# 状态指示器
st.sidebar.markdown("---")
status_container = st.sidebar.empty()

btn_run = st.sidebar.button("计算实力榜 🚀", type="primary")

# ==========================================
# 4. 主界面
# ==========================================
if btn_run:
    with st.spinner("正在提取数据..."):
        raw_df = engine.fetch_data(engine.current_season, d_str_from, d_str_to)

        # 状态灯
        s = engine.status
        status_html = "<div><small>数据源状态：</small><br>"
        status_html += f"<span class='{'status-ok' if s['Base'] else 'status-err'}'>● Base</span> "
        status_html += f"<span class='{'status-ok' if s['Defense'] else 'status-err'}'>● Defense</span> "
        status_html += f"<span class='{'status-ok' if s['Hustle'] else 'status-err'}'>● Hustle</span> "
        status_html += f"<span class='{'status-ok' if s['Iso'] else 'status-err'}'>● Iso</span>"
        status_html += "</div>"
        status_container.markdown(status_html, unsafe_allow_html=True)

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
            st.caption("🚀 算法 v6.3：防守质量(效率/单防)权重提升至35%，干扰统治力下调至30%。")

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
                    df_def['Disruption'] = df_def['STOCKS'] + df_def['DEFLECTIONS']
                    fig3 = plot_scatter(df_def, "CONTESTED_SHOTS", "Disruption", "BLK", "Def_Score",
                                        "干扰投篮 (Contested)", "破坏力 (Stocks+Deflections)")
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
                                <div class="stat-item"><div class="stat-val">{r['DEF_RATING']:.1f}</div><div class="stat-lbl">DefRtg</div></div>
                                <div class="stat-item"><div class="stat-val">{r.get('ISO_PPP', 0.95):.2f}</div><div class="stat-lbl">单防PPP</div></div>
                            </div>
                        </div>""", unsafe_allow_html=True)

            # --- 全量数据表 ---
            st.markdown("---")
            with st.expander("📊 查看/下载 完整数据表 (支持排序)"):
                col_map = {
                    'PLAYER_NAME': '姓名', 'TEAM_ABBREVIATION': '队', 'GP': '场', 'MIN': '时',
                    'Total_Score': '💎总分', 'Off_Score': '🔴攻分', 'Def_Score': '🔵防分',
                    'PTS': '分', 'TS_PCT': 'TS%', 'USG_PCT': '权%', 'AST_PCT': '助%',
                    'CONTESTED_SHOTS': '干扰', 'DEFLECTIONS': '截断', 'STOCKS': '断冒',
                    'DEF_RATING': '防效', 'ISO_PPP': '单防PPP'
                }
                display_cols = list(col_map.keys())
                valid_cols = [c for c in display_cols if c in df.columns]
                df_show = df[valid_cols].rename(columns=col_map).copy()

                for col in ['TS%', '权%', '助%']:
                    if col in df_show.columns: df_show[col] = (df_show[col] * 100).round(1)
                for col in ['💎总分', '🔴攻分', '🔵防分']:
                    if col in df_show.columns: df_show[col] = df_show[col].round(1)

                st.dataframe(df_show.sort_values(by='💎总分', ascending=False), use_container_width=True, height=600)

        else:
            st.warning("无数据返回。")