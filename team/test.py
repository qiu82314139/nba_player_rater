import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from math import pi
from nba_api.stats.endpoints import leaguedashplayerstats, leaguehustlestatsplayer

# ==========================================
# 0. 全局配置与字体修复 (Global Config)
# ==========================================

st.set_page_config(page_title="NBA数据深度视界 Pro", layout="wide", page_icon="🏀")

# --- 解决中文乱码核心设置 ---
# 优先尝试加载系统中的常见中文字体
mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Heiti TC', 'PingFang HK', 'Arial Unicode MS',
                                   'sans-serif']
mpl.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# 设置暗黑风格背景
plt.style.use('dark_background')

# 球队配色字典
TEAM_COLORS = {
    'GSW': '#FFC72C', 'LAL': '#552583', 'BOS': '#007A33', 'MIA': '#98002E',
    'DEN': '#FEC524', 'MIL': '#00471B', 'PHI': '#006BB6', 'PHX': '#E56020',
    'DAL': '#00538C', 'LAC': '#C8102E', 'BKN': '#FFFFFF', 'NYK': '#F58426',
    'OKC': '#007AC1', 'MIN': '#236192', 'SAC': '#5A2D81', 'IND': '#FDBB30',
    'DEFAULT': '#00FF00'
}

# 核心分析指标映射 (雷达图用)
METRICS_MAP = {
    'PTS': '得分产量 (PTS)',
    'rTS%': '真实效率 (rTS%)',
    'AST_PCT': '组织占比 (AST%)',
    'USG_PCT': '球权消耗 (USG%)',
    'DEFLECTIONS': '防守侵略 (Deflections)',
    'CONTESTED_SHOTS': '干扰投篮 (Contest)'
}


# ==========================================
# 1. 数据引擎 (Data Engine)
# ==========================================

@st.cache_data(ttl=3600)
def load_and_process_data(season='2024-25'):
    """
    全量获取数据：Base + Advanced + Hustle
    """
    with st.spinner(f'正在构建数据军火库 ({season})...这需要请求3次NBA官网接口...'):
        try:
            # 1. Base Stats
            base = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, per_mode_detailed='PerGame', measure_type_detailed_defense='Base'
            ).get_data_frames()[0]

            # 2. Advanced Stats
            adv = leaguedashplayerstats.LeagueDashPlayerStats(
                season=season, per_mode_detailed='PerGame', measure_type_detailed_defense='Advanced'
            ).get_data_frames()[0]

            # 3. Hustle Stats
            hustle = leaguehustlestatsplayer.LeagueHustleStatsPlayer(
                season=season, per_mode_time='PerGame'
            ).get_data_frames()[0]

            # --- 合并逻辑 ---
            # Base + Adv
            df = pd.merge(base, adv[['PLAYER_ID', 'AST_PCT', 'USG_PCT', 'TS_PCT']], on='PLAYER_ID', how='inner')

            # + Hustle (注意：Hustle数据可能缺失，用left join并填充0)
            hustle_cols = ['PLAYER_ID', 'DEFLECTIONS', 'CONTESTED_SHOTS', 'SCREEN_ASSISTS', 'LOOSE_BALLS_RECOVERED',
                           'BOX_OUTS']
            # 检查接口返回的列名是否存在，防止报错
            available_hustle_cols = [col for col in hustle_cols if col in hustle.columns]

            df = pd.merge(df, hustle[available_hustle_cols], on='PLAYER_ID', how='left')
            df[available_hustle_cols] = df[available_hustle_cols].fillna(0)

            # --- 清洗 ---
            df = df[(df['GP'] > 5) & (df['MIN'] > 12)].copy()  # 至少打5场，场均12分钟

            # --- 计算高阶指标 ---
            league_avg_ts = df['TS_PCT'].mean()
            df['rTS%'] = (df['TS_PCT'] - league_avg_ts) * 100

            # 计算综合拼搏分 (Hustle Score) = 截断 + 干扰 + 掩护助攻 + 救球 + 卡位
            # 如果某些列不存在则忽略
            hustle_factors = ['DEFLECTIONS', 'CONTESTED_SHOTS', 'SCREEN_ASSISTS', 'LOOSE_BALLS_RECOVERED', 'BOX_OUTS']
            valid_factors = [c for c in hustle_factors if c in df.columns]
            df['HUSTLE_SCORE'] = df[valid_factors].sum(axis=1)

            # 计算百分位排名
            rank_cols = ['PTS', 'rTS%', 'AST_PCT', 'USG_PCT', 'DEFLECTIONS', 'CONTESTED_SHOTS', 'HUSTLE_SCORE']
            for col in rank_cols:
                if col in df.columns:
                    df[f'{col}_RANK'] = df[col].rank(pct=True) * 100

            return df, league_avg_ts

        except Exception as e:
            st.error(f"数据获取失败: {e}")
            return pd.DataFrame(), 0


# ==========================================
# 2. 图表绘制模块 (Visualization Core)
# ==========================================

def plot_radar(player_data, player_name, team_abv):
    """模块A：雷达图"""
    labels = list(METRICS_MAP.values())
    stats = [player_data[f'{k}_RANK'] for k in METRICS_MAP.keys()]
    stats += stats[:1]
    angles = [n / float(len(labels)) * 2 * pi for n in range(len(labels))]
    angles += angles[:1]

    color = TEAM_COLORS.get(team_abv, '#00FF00')

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    ax.plot(angles, stats, color=color, linewidth=2, linestyle='solid')
    ax.fill(angles, stats, color=color, alpha=0.4)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=10, color='#E0E0E0')
    ax.set_yticks([25, 50, 75, 100])
    ax.set_yticklabels(["", "", "", ""], color="#666666")  # 隐藏内部刻度文字
    ax.set_ylim(0, 100)
    ax.spines['polar'].set_visible(False)
    ax.grid(color='#444444', linestyle='--', linewidth=0.5)

    plt.title(f"{player_name}", size=14, color='white', y=1.1)
    return fig


def plot_butterfly(p1_data, p2_data, p1_name, p2_name):
    """模块C：蝴蝶对比图"""
    metrics = list(METRICS_MAP.keys())
    labels = list(METRICS_MAP.values())

    # 获取Rank数据
    p1_vals = [p1_data[f'{m}_RANK'] for m in metrics]
    p2_vals = [p2_data[f'{m}_RANK'] for m in metrics]

    y = np.arange(len(metrics))

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    # 绘制条形 (左边取负实现对称)
    bar_height = 0.6
    ax.barh(y, [-v for v in p1_vals], height=bar_height, color='#00BFFF', label=p1_name, alpha=0.8)
    ax.barh(y, p2_vals, height=bar_height, color='#FF4500', label=p2_name, alpha=0.8)

    # 中轴线
    ax.axvline(0, color='white', linewidth=1)

    # 添加数值标签
    for i, (v1, v2) in enumerate(zip(p1_vals, p2_vals)):
        ax.text(-v1 - 5, i, f"{int(v1)}", ha='center', va='center', color='#00BFFF', fontsize=10, fontweight='bold')
        ax.text(v2 + 5, i, f"{int(v2)}", ha='center', va='center', color='#FF4500', fontsize=10, fontweight='bold')
        # 中间显示指标名
        ax.text(0, i + 0.4, labels[i], ha='center', va='center', color='white', fontsize=9)

    ax.set_yticks([])  # 隐藏Y轴刻度
    ax.set_xticks([])  # 隐藏X轴刻度

    # 图例和标题
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.05), ncol=2, frameon=False, labelcolor='white')
    plt.title("球员能力维度对比 (Percentile Rank)", color='white', pad=20)

    # 去除边框
    for spine in ax.spines.values():
        spine.set_visible(False)

    return fig


def plot_hustle_leaderboard(df):
    """模块B：拼搏榜单 (水平条形图)"""
    # 筛选: 场均得分 < 20 (寻找角色球员)
    mask = (df['PTS'] < 20)
    # 取前10名
    top_hustle = df[mask].nlargest(10, 'HUSTLE_SCORE').sort_values('HUSTLE_SCORE', ascending=True)

    names = top_hustle['PLAYER_NAME']
    scores = top_hustle['HUSTLE_SCORE']
    teams = top_hustle['TEAM_ABBREVIATION']

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor('#121212')
    ax.set_facecolor('#121212')

    bars = ax.barh(names, scores, color='#FFC72C')

    # 在条形图末尾添加数值
    for bar, score, team in zip(bars, scores, teams):
        width = bar.get_width()
        ax.text(width + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{score:.1f} ({team})",
                ha='left', va='center', color='white', fontsize=10)

    ax.set_xlabel("综合拼搏指数 (截断+干扰+掩护+救球+卡位)", color='gray')
    ax.tick_params(axis='y', colors='white')
    ax.tick_params(axis='x', colors='gray')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.spines['left'].set_visible(False)

    plt.title("蓝领英雄榜 (PTS < 20)", color='white', size=14)
    return fig


# ==========================================
# 3. 主程序逻辑 (App Layout)
# ==========================================

def main():
    # 侧边栏导航
    st.sidebar.title("🏀 NBA Data Vision")
    page = st.sidebar.radio("选择分析模块", ["1. 球员全息画像", "2. 巅峰对决 (PK)", "3. 蓝领拼搏榜"])

    # 加载数据
    season = st.sidebar.selectbox("赛季", ['2024-25', '2023-24'])
    df, avg_ts = load_and_process_data(season)

    if df.empty:
        st.warning("暂无数据，请检查网络或等待重试。")
        return

    # --- 页面 1: 球员全息画像 ---
    if page == "1. 球员全息画像":
        st.header(f"🕵️‍♂️ 球员全能雷达图 ({season})")
        col_sel, col_empty = st.columns([1, 2])
        with col_sel:
            # 智能搜索
            player_list = sorted(df['PLAYER_NAME'].unique())
            default_idx = player_list.index('Luka Doncic') if 'Luka Doncic' in player_list else 0
            selected_player = st.selectbox("搜索球员", player_list, index=default_idx)

        player_stats = df[df['PLAYER_NAME'] == selected_player].iloc[0]

        c1, c2 = st.columns([1, 1])
        with c1:
            fig = plot_radar(player_stats, selected_player, player_stats['TEAM_ABBREVIATION'])
            st.pyplot(fig)
        with c2:
            st.subheader("数据解读")
            st.markdown(f"""
            - **真实效率 (rTS%)**: `{player_stats['rTS%']:+.1f}%` (比联盟平均水平{'高' if player_stats['rTS%'] > 0 else '低'})
            - **防守侵略性**: `{player_stats['DEFLECTIONS']:.1f}` 次截断/场 (超过 {player_stats['DEFLECTIONS_RANK']:.0f}% 的球员)
            - **干扰投篮**: `{player_stats['CONTESTED_SHOTS']:.1f}` 次/场
            """)
            st.info(
                "💡 这是一个非常好的视频素材：截图左侧雷达图，配上右侧的数据分析，说明该球员是‘攻强守弱’还是‘全能战士’。")

    # --- 页面 2: 巅峰对决 ---
    elif page == "2. 巅峰对决 (PK)":
        st.header("⚔️ 球员对比系统 (Butterfly Chart)")
        player_list = sorted(df['PLAYER_NAME'].unique())

        c1, c2 = st.columns(2)
        with c1:
            p1_name = st.selectbox("选择球员 A (左 - 蓝色)", player_list, index=0)
        with c2:
            p2_name = st.selectbox("选择球员 B (右 - 红色)", player_list, index=1)

        if p1_name and p2_name:
            p1_data = df[df['PLAYER_NAME'] == p1_name].iloc[0]
            p2_data = df[df['PLAYER_NAME'] == p2_name].iloc[0]

            st.pyplot(plot_butterfly(p1_data, p2_data, p1_name, p2_name))

            st.success(
                f"📊 分析师视角：对比 {p1_name} 和 {p2_name} 在组织(AST%)和防守侵略性(Deflections)上的差异，是判断核心风格的关键。")

    # --- 页面 3: 蓝领拼搏榜 ---
    elif page == "3. 蓝领拼搏榜":
        st.header("🛡️ 寻找被低估的蓝领英雄")
        st.markdown("**筛选标准：** 场均得分 < 20分，但拼搏指数 (截断+干扰+掩护+救球) 极高的球员。")

        fig = plot_hustle_leaderboard(df)
        st.pyplot(fig)

        st.markdown("### 📝 视频选题推荐")
        top_guy = df[(df['PTS'] < 20)].nlargest(1, 'HUSTLE_SCORE').iloc[0]
        st.write(f"👉 **本赛季最大的防守遗珠：{top_guy['PLAYER_NAME']}**。他不占球权，但干了所有的脏活累活。")


if __name__ == "__main__":
    main()