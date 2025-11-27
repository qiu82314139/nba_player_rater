import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from nba_api.stats.endpoints import playergamelogs, commonallplayers, leaguedashplayerstats, playerindex
from datetime import datetime, timedelta
import os

# === 1. 页面配置 ===
st.set_page_config(
    page_title="篮球星图 - 2025 NBA 新秀观察",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === 2. 静态数据库：位置 & 中文名映射 (2025届) ===
# 字典的键顺序将被视为模拟选秀顺位
ROOKIE_POSITIONS = {
    # First Round
    'Cooper Flagg': 'PF/SF', 'Dylan Harper': 'PG/SG', 'VJ Edgecombe': 'SG', 'Kon Knueppel': 'SF/SG',
    'Ace Bailey': 'SF/PF', 'Tre Johnson': 'SG', 'Jeremiah Fears': 'PG', 'Egor Demin': 'PG/SF',
    'Collin Murray-Boyles': 'PF/C', 'Khaman Maluach': 'C', 'Cedric Coward': 'SF/PF', 'Noa Essengue': 'PF',
    'Derik Queen': 'C', 'Carter Bryant': 'SF/PF', 'Thomas Sorber': 'C', 'Yang Hansen': 'C',
    'Joan Beringer': 'C/PF', 'Walter Clayton Jr.': 'PG/SG', 'Nolan Traoré': 'PG', 'Kasparas Jakučionis': 'PG',
    'Will Riley': 'SF', 'Drake Powell': 'SF/SG', 'Asa Newell': 'PF', 'Nique Clifford': 'SG/SF',
    'Jase Richardson': 'PG/SG', 'Ben Saraf': 'PG/SG', 'Danny Wolf': 'C/PF', 'Hugo González': 'SF',
    'Liam McNeeley': 'SF', 'Yanic Konan Niederhauser': 'C',
    # Second Round
    'Rasheer Fleming': 'PF', 'Noah Penda': 'SF', 'Sion James': 'SG/SF', 'Ryan Kalkbrenner': 'C', 
    'Johni Broome': 'PF/C', 'Adou Thiero': 'SF/PF', 'Chaz Lanier': 'SG', 'Kam Jones': 'SG', 
    'Alijah Martin': 'SG', 'Micah Peavy': 'SF', 'Koby Brea': 'SG', 'Maxime Raynaud': 'C', 
    'Jamir Watkins': 'SF', 'Brooks Barnhizer': 'SF/SG', 'Rocco Zikarsky': 'C', 'Amari Williams': 'C', 
    'Bogoljub Marković': 'PF/C', 'Javon Small': 'PG', 'Tyrese Proctor': 'PG', 'Kobe Sanders': 'SG', 
    'Mohamed Diawara': 'SF/PF', 'Alex Toohey': 'SF', 'John Tonje': 'SF/SG', 'Taelon Peter': 'SG', 
    'Lachlan Olbrich': 'PF/C', 'Will Richard': 'SG', 'Max Shulga': 'SG', 'Saliou Niang': 'SF/PF', 
    'Jahmai Mashack': 'SG/SF'
}

# 自动生成顺位映射 (基于 ROOKIE_POSITIONS 的顺序)
ROOKIE_DRAFT_PICKS = {name: i+1 for i, name in enumerate(ROOKIE_POSITIONS.keys())}

ROOKIE_CN_NAMES = {
    'Cooper Flagg': '库珀·弗拉格', 'Dylan Harper': '迪伦·哈珀', 'VJ Edgecombe': 'VJ·埃吉康姆', 
    'Kon Knueppel': '康·克努佩尔', 'Ace Bailey': '艾斯·贝利', 'Tre Johnson': '特雷·约翰逊', 
    'Jeremiah Fears': '杰里米亚·费尔斯', 'Egor Dëmin': '埃戈尔·德明', 'Collin Murray-Boyles': '科林·默里-博伊尔斯', 
    'Khaman Maluach': '卡曼·马鲁阿奇', 'Cedric Coward': '塞德里克·考沃德', 'Noa Essengue': '诺亚·埃森格',
    'Derik Queen': '德里克·奎恩', 'Carter Bryant': '卡特·科比', 'Thomas Sorber': '托马斯·索伯', 
    'Yang Hansen': '杨瀚森', 'Joan Beringer': '琼·贝林格', 'Walter Clayton Jr.': '沃尔特·克莱顿', 
    'Nolan Traoré': '诺兰·特拉奥雷', 'Kasparas Jakučionis': '卡斯帕拉斯·雅库乔尼斯', 'Will Riley': '威尔·莱利', 
    'Drake Powell': '德雷克·鲍威尔', 'Asa Newell': '阿萨·纽维尔', 'Nique Clifford': '尼克·克利福德',
    'Jase Richardson': '杰斯·理查德森', 'Ben Saraf': '本·萨拉夫', 'Danny Wolf': '丹尼·沃尔夫', 
    'Hugo González': '雨果·冈萨雷斯', 'Liam McNeeley': '利亚姆·麦克尼利', 'Yanic Konan Niederhäuser': '亚尼克·科南·尼德豪瑟',
    'Rasheer Fleming': '拉希尔·弗莱明', 'Noah Penda': '诺亚·彭达', 'Sion James': '锡安·詹姆斯', 
    'Ryan Kalkbrenner': '瑞安·卡尔克布伦纳', 'Johni Broome': '乔尼·布鲁姆', 'Adou Thiero': '阿杜·铁罗', 
    'Chaz Lanier': '查兹·拉尼尔', 'Kam Jones': '卡姆·琼斯', 'Alijah Martin': '阿利亚·马丁',
    'Micah Peavy': '迈卡·皮维', 'Koby Brea': '科比·布雷亚', 'Maxime Raynaud': '马克西姆·雷诺', 
    'Jamir Watkins': '贾米尔·沃特金斯', 'Brooks Barnhizer': '布鲁克斯·巴恩希泽', 'Rocco Zikarsky': '罗科·齐卡尔斯基', 
    'Amari Williams': '阿玛里·威廉姆斯', 'Bogoljub Marković': '博戈柳布·马尔科维奇', 'Javon Small': '贾冯·斯莫尔', 
    'Tyrese Proctor': '泰雷斯·普罗克特', 'Kobe Sanders': '科比·桑德斯', 'Mohamed Diawara': '穆罕默德·迪亚瓦拉',
    'Alex Toohey': '亚历克斯·图希', 'John Tonje': '约翰·汤杰', 'Taelon Peter': '泰隆·彼得', 
    'Lachlan Olbrich': '拉赫兰·奥尔布里奇', 'Will Richard': '威尔·理查德', 'Max Shulga': '马克斯·舒尔加', 
    'Saliou Niang': '萨利乌·尼昂', 'Jahmai Mashack': '贾迈·马沙克'
}

# 赛季配置
CURRENT_SEASON = '2025-26' 
ROOKIE_YEAR_EXP = '2025'   

# === 3. 核心引擎 (Z-Score 版) ===
class RookieRankerEngine:
    def __init__(self, season=CURRENT_SEASON):
        self.season = season

    def map_info(self, player_name):
        pos = ROOKIE_POSITIONS.get(player_name, "N/A") 
        cn_name = ROOKIE_CN_NAMES.get(player_name, player_name)
        return pos, cn_name

    def simplify_position(self, pos_str):
        """位置归类：Guard/Forward/Center"""
        if not isinstance(pos_str, str): return 'Forward'
        pos_str = pos_str.upper()
        if 'C' in pos_str: return 'Center'
        if 'F' in pos_str: return 'Forward'
        if 'G' in pos_str: return 'Guard'
        return 'Forward'

    @st.cache_data(ttl=3600)
    def fetch_data(_self, date_from="", date_to=""):
        try:
            # 1. 基础数据 (Base)
            base_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                per_mode_detailed='PerGame', season=_self.season, season_type_all_star='Regular Season',
                date_from_nullable=date_from, date_to_nullable=date_to
            ).get_data_frames()[0]

            if base_stats.empty:
                return pd.DataFrame(), pd.DataFrame()

            # 2. 高阶数据 (Advanced)
            adv_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                per_mode_detailed='PerGame', measure_type_detailed_defense='Advanced', 
                season=_self.season, season_type_all_star='Regular Season',
                date_from_nullable=date_from, date_to_nullable=date_to
            ).get_data_frames()[0]

            # 3. 得分方式数据 (Scoring) - 获取 %Unassisted
            score_stats = leaguedashplayerstats.LeagueDashPlayerStats(
                per_mode_detailed='PerGame', measure_type_detailed_defense='Scoring', 
                season=_self.season, season_type_all_star='Regular Season',
                date_from_nullable=date_from, date_to_nullable=date_to
            ).get_data_frames()[0]

            # 4. 位置信息 (PlayerIndex)
            p_index = playerindex.PlayerIndex(season=_self.season, historical_nullable=0).get_data_frames()[0]
            p_pos_df = p_index[['PERSON_ID', 'POSITION']].rename(columns={'PERSON_ID': 'PLAYER_ID'})

            # 5. 合并数据
            cols_adv = ['PLAYER_ID', 'TS_PCT', 'USG_PCT', 'DEF_RATING', 'AST_TO', 'NET_RATING', 'PIE']
            league_df = pd.merge(base_stats, adv_stats[cols_adv], on='PLAYER_ID', how='left')
            
            cols_score = ['PLAYER_ID', 'PCT_UAST_FGM'] 
            league_df = pd.merge(league_df, score_stats[cols_score], on='PLAYER_ID', how='left')

            league_df = pd.merge(league_df, p_pos_df, on='PLAYER_ID', how='left')
            league_df['POSITION'] = league_df['POSITION'].fillna('F')

            # 6. 比赛日志
            try:
                logs = playergamelogs.PlayerGameLogs(
                    season_nullable=_self.season, 
                    date_from_nullable=date_from, 
                    date_to_nullable=date_to
                )
                logs_df = logs.get_data_frames()[0]
                logs_df['GAME_DATE'] = pd.to_datetime(logs_df['GAME_DATE'])
            except:
                logs_df = pd.DataFrame()

            return league_df, logs_df

        except Exception as e:
            st.error(f"NBA API 连接失败: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def calculate_consistency(self, logs_df):
        if logs_df.empty: 
            return pd.DataFrame(columns=['PLAYER_ID', 'GmSc_Std'])
        try:
            logs_df['GmSc'] = (logs_df['PTS'] + 0.4 * logs_df['FGM'] - 0.7 * logs_df['FGA'] - 0.4 * (logs_df['FTA'] - logs_df['FTM']) + 
                               0.7 * logs_df['OREB'] + 0.3 * logs_df['DREB'] + logs_df['STL'] + 0.7 * logs_df['AST'] + 
                               0.7 * logs_df['BLK'] - 0.4 * logs_df['PF'] - logs_df['TOV'])
            
            consistency = logs_df.groupby('PLAYER_ID')['GmSc'].std().reset_index()
            consistency.columns = ['PLAYER_ID', 'GmSc_Std']
            return consistency
        except KeyError:
            return pd.DataFrame(columns=['PLAYER_ID', 'GmSc_Std'])

    def normalize_score(self, series, scale_factor=1):
        score = 70 + (series * 10 / scale_factor)
        return score.clip(40, 100)

    def apply_ranking_model(self, league_df, consistency_df, weights):
        if league_df.empty: return pd.DataFrame()
        df = league_df.copy()

        df['Calc_Pos'] = df['POSITION'].apply(self.simplify_position)

        # 1. 难度系数
        df['Z_USG'] = df.groupby('Calc_Pos')['USG_PCT'].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
        if 'PCT_UAST_FGM' in df.columns:
            df['Z_UAST'] = df.groupby('Calc_Pos')['PCT_UAST_FGM'].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
        else:
            df['Z_UAST'] = 0
        
        df['Z_Difficulty'] = (df['Z_USG'] * 0.6) + (df['Z_UAST'] * 0.4)
        df['Difficulty_Coef'] = 1 + (df['Z_USG'] * 0.15) + (df['Z_UAST'] * 0.05)

        # === 维度 1：基础统治力 (Production) ===
        metrics_prod = ['PTS', 'REB', 'AST', 'STL', 'BLK']
        for col in metrics_prod:
            df[f'Z_{col}'] = 0.0
            
        for col in metrics_prod:
            if col in df.columns:
                try:
                    if col == 'BLK': 
                         df[f'Z_{col}'] = df.groupby('Calc_Pos')[col].transform(lambda x: (x - x.mean()) / (x.std() + 0.2)) 
                    else:
                         df[f'Z_{col}'] = df.groupby('Calc_Pos')[col].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
                except Exception:
                    df[f'Z_{col}'] = 0.0
            else:
                df[f'Z_{col}'] = 0.0
        
        raw_prod = (df['Z_PTS'] * 2.0) + (df['Z_REB'] * 0.8) + df['Z_AST'] 
        adjusted_prod = raw_prod * np.where(df['Difficulty_Coef'] > 1, df['Difficulty_Coef'], 0.95)
        df['Score_Prod'] = self.normalize_score(adjusted_prod, scale_factor=4.5)

        # === 维度 2：进攻效率 ===
        if 'FGA' in df.columns and 'FTA' in df.columns:
            df['TSA'] = df['FGA'] + 0.44 * df['FTA']
        else:
            df['TSA'] = 0.0

        df['Pos_Avg_TS'] = df.groupby('Calc_Pos')['TS_PCT'].transform('mean')
        rotation_mask = df['MIN'] >= 12.0
        if rotation_mask.any():
            pos_avg_map = df[rotation_mask].groupby('Calc_Pos')['TS_PCT'].mean()
            df['Pos_Avg_TS'] = df['Calc_Pos'].map(pos_avg_map)
            df['Pos_Avg_TS'] = df['Pos_Avg_TS'].fillna(df['TS_PCT'].mean())
        else:
            df['Pos_Avg_TS'] = df.groupby('Calc_Pos')['TS_PCT'].transform('mean')

        df['TS_Diff'] = (df['TS_PCT'] - df['Pos_Avg_TS']) * 100 
        raw_eff = df['TSA'] * 2 * (df['TS_PCT'] - df['Pos_Avg_TS'])
        raw_eff = np.where(raw_eff < 0, raw_eff * 0.5, raw_eff)
        raw_eff = np.sign(raw_eff) * np.log1p(np.abs(raw_eff))
        df['Score_Eff'] = self.normalize_score(raw_eff, scale_factor=1.5)

        # === 维度 3：防守贡献 ===
        df['Z_PF_Inv'] = df.groupby('Calc_Pos')['PF'].transform(lambda x: (x.mean() - x) / (x.std() + 1e-6))
        raw_def = (df['Z_STL'] * 1.2) + (df['Z_BLK'] * 1.2) + (df['Z_REB'] * 0.5) + (df['Z_PF_Inv'] * 0.5)
        df['Score_Def'] = self.normalize_score(raw_def, scale_factor=3.5)

        # === 维度 4：失误控制 ===
        if 'AST_TO' in df.columns:
            df['Z_AST_TO'] = df.groupby('Calc_Pos')['AST_TO'].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
        else:
            df['Z_AST_TO'] = 0
        adjusted_ast_to = df['Z_AST_TO'] + (df['Z_Difficulty'] * 0.5)
        df['Score_TO'] = self.normalize_score(adjusted_ast_to, scale_factor=2)

        # === 维度 5：球队贡献 ===
        if 'PIE' in df.columns:
            df['Z_PIE'] = df.groupby('Calc_Pos')['PIE'].transform(lambda x: (x - x.mean()) / (x.std() + 1e-6))
        else:
            df['Z_PIE'] = 0
        raw_team = df['Z_PIE']
        df['Score_Team'] = self.normalize_score(raw_team, scale_factor=1.5)

        # === 维度 6：出勤 (指数幂律模型) ===
        # 修改为指数(幂函数)增长模式，范围 0-100
        # Formula: 100 * (GP / Max_GP) ^ 2.5
        if not consistency_df.empty:
            df = pd.merge(df, consistency_df, on='PLAYER_ID', how='left')
            df['GmSc_Std'] = df['GmSc_Std'].fillna(10)
        else:
            df['GmSc_Std'] = 10

        max_gp = df['GP'].max()
        if pd.isna(max_gp) or max_gp == 0:
            max_gp = 1
        
        # 幂律计算：k=2.5
        # GP=1, Max=20 -> (0.05)^2.5 = 0.0005 -> 0.05分
        # GP=10, Max=20 -> (0.5)^2.5 = 0.176 -> 17.6分
        # GP=18, Max=20 -> (0.9)^2.5 = 0.768 -> 76.8分
        k_exponent = 2.5
        df['Score_GP_Exp'] = 100 * ((df['GP'] / max_gp) ** k_exponent)
        
        # 稳定性加成 (作为微调，最大加5分)
        df['Bonus_Consist'] = (10 - df['GmSc_Std']).clip(0, 10) / 2
        
        df['Score_Dura'] = df['Score_GP_Exp'] + df['Bonus_Consist']
        # 取消 40 分限制，改为 0-100
        df['Score_Dura'] = df['Score_Dura'].clip(0, 100)

        # === 总分计算 ===
        df['Final_Score'] = (
            df['Score_Prod'] * weights['prod'] +
            df['Score_Eff'] * weights['eff'] +
            df['Score_Def'] * weights['def'] +
            df['Score_TO'] * weights['to'] +
            df['Score_Team'] * weights['team'] +
            df['Score_Dura'] * weights['dura']
        )
        
        return df

# === 4. 侧边栏 ===
if os.path.exists("unnamed.jpg"):
    st.sidebar.image("unnamed.jpg", use_container_width=True)
else:
    st.sidebar.markdown("# 🏀 篮球星图")

st.sidebar.markdown("### HoopMap Rookie Watch")
st.sidebar.header("🎛️ 评分模型控制台")

# === 时间范围选择 ===
st.sidebar.subheader("📅 统计周期")
time_range_option = st.sidebar.selectbox(
    "选择时间范围", 
    ["赛季至今 (Season)", "最近 7 天", "最近 15 天", "最近 30 天", "自定义范围"]
)

date_from_str = ""
date_to_str = ""

if time_range_option == "最近 7 天":
    date_from_str = (datetime.now() - timedelta(days=7)).strftime('%m/%d/%Y')
    date_to_str = datetime.now().strftime('%m/%d/%Y')
elif time_range_option == "最近 15 天":
    date_from_str = (datetime.now() - timedelta(days=15)).strftime('%m/%d/%Y')
    date_to_str = datetime.now().strftime('%m/%d/%Y')
elif time_range_option == "最近 30 天":
    date_from_str = (datetime.now() - timedelta(days=30)).strftime('%m/%d/%Y')
    date_to_str = datetime.now().strftime('%m/%d/%Y')
elif time_range_option == "自定义范围":
    c1, c2 = st.sidebar.columns(2)
    d_from = c1.date_input("开始", datetime.now() - timedelta(days=30))
    d_to = c2.date_input("结束", datetime.now())
    date_from_str = d_from.strftime('%m/%d/%Y')
    date_to_str = d_to.strftime('%m/%d/%Y')

if time_range_option != "赛季至今 (Season)":
    st.sidebar.info(f"查询区间: {date_from_str} - {date_to_str}")
else:
    st.sidebar.info("查询区间: 全赛季")

st.sidebar.markdown("---")
st.sidebar.markdown("**模式：基石球员优先**")

w_prod = st.sidebar.slider("📊 基础统治力", 0.0, 1.0, 0.40, 0.05)
w_eff = st.sidebar.slider("🎯 进攻效率", 0.0, 1.0, 0.20, 0.05)
w_def = st.sidebar.slider("🛡️ 个人防守", 0.0, 1.0, 0.10, 0.05)
w_team = st.sidebar.slider("🏆 球队贡献", 0.0, 1.0, 0.10, 0.05)
w_dura = st.sidebar.slider("🔋 出勤/稳定", 0.0, 1.0, 0.10, 0.05)
w_to = st.sidebar.slider("🧠 失误控制", 0.0, 1.0, 0.10, 0.05)

total_w = w_prod + w_eff + w_def + w_to + w_team + w_dura
if total_w == 0: total_w = 1
weights = {
    'prod': w_prod/total_w, 'eff': w_eff/total_w, 'def': w_def/total_w, 
    'to': w_to/total_w, 'team': w_team/total_w, 'dura': w_dura/total_w
}

# === 5. 主界面 ===
st.title(f"🏀 篮球星图 | {CURRENT_SEASON} NBA 新秀观察")
if date_from_str:
    st.caption(f"当前数据范围: {date_from_str} 至 {date_to_str}")
else:
    st.caption("当前数据范围: 赛季至今")

ranker = RookieRankerEngine(season=CURRENT_SEASON)

full_ranked_df = pd.DataFrame()
logs_df = pd.DataFrame()

with st.spinner('正在从 NBA 官方数据库获取实时数据...'):
    league_df, logs_df = ranker.fetch_data(date_from=date_from_str, date_to=date_to_str)

consistency_df = ranker.calculate_consistency(logs_df)

if not league_df.empty:
    full_ranked_df = ranker.apply_ranking_model(league_df, consistency_df, weights)

# 3. 强制筛选 & 补零
all_targets = list(ROOKIE_POSITIONS.keys())
target_df = pd.DataFrame(all_targets, columns=['PLAYER_NAME'])

if not full_ranked_df.empty and 'PLAYER_NAME' in full_ranked_df.columns:
    season_ranked = pd.merge(target_df, full_ranked_df, on='PLAYER_NAME', how='left')
else:
    season_ranked = target_df.copy()

numeric_cols = season_ranked.select_dtypes(include=[np.number]).columns
season_ranked[numeric_cols] = season_ranked[numeric_cols].fillna(0)

if 'POSITION' in season_ranked.columns:
    season_ranked['POSITION'] = season_ranked['POSITION'].fillna('')

def get_static_pos(name):
    raw = ROOKIE_POSITIONS.get(name, 'F')
    return ranker.simplify_position(raw)

if 'Calc_Pos' not in season_ranked.columns:
    season_ranked['Calc_Pos'] = None

season_ranked['Calc_Pos'] = season_ranked.apply(
    lambda x: x['Calc_Pos'] if pd.notna(x['Calc_Pos']) and x['Calc_Pos'] != 0 else get_static_pos(x['PLAYER_NAME']), 
    axis=1
)

def process_display(row):
    pos, cn_name = ranker.map_info(row['PLAYER_NAME'])
    if pos == "N/A": 
        pos = row.get('POSITION', 'N/A')
    return pd.Series([pos, cn_name])

season_ranked[['Pos_Display', 'CN_Name']] = season_ranked.apply(process_display, axis=1)
season_ranked['Display_Name'] = season_ranked.apply(lambda row: f"{row['CN_Name']} ({row['PLAYER_NAME']})" if row['CN_Name'] != row['PLAYER_NAME'] else row['PLAYER_NAME'], axis=1)

# 排序
season_ranked = season_ranked.sort_values(by='Final_Score', ascending=False).reset_index(drop=True)

# === 新增：添加排名和顺位列 ===
season_ranked['Rank'] = season_ranked.index + 1
season_ranked['Pick'] = season_ranked['PLAYER_NAME'].map(ROOKIE_DRAFT_PICKS).fillna(99).astype(int)

# === KPI 展示 ===
col1, col2, col3, col4 = st.columns(4)
if not season_ranked.empty:
    top1 = season_ranked.iloc[0]
    col1.metric("👑 榜单领跑", top1['CN_Name'], f"{top1['Final_Score']:.1f}")
    
    eff_king = season_ranked.sort_values('Score_Eff', ascending=False).iloc[0]
    col2.metric("💎 效率之王", eff_king['CN_Name'], f"TS% {eff_king['TS_PCT']:.1%}")
    
    def_king = season_ranked.sort_values('Score_Def', ascending=False).iloc[0]
    col3.metric("🛡️ 铁闸", def_king['CN_Name'], f"评 {def_king['Score_Def']:.1f}")
    
    iron_man = season_ranked.sort_values('GP', ascending=False).iloc[0]
    col4.metric("🔋 劳模", iron_man['CN_Name'], f"{iron_man['GP']} 场")

st.markdown("---")

# === 核心 Tabs ===
main_tab1, main_tab2, main_tab3 = st.tabs(["🏆 综合排名", "🔬 六维能力雷达", "🗃️ 原始数据"])

with main_tab1:
    pos_tab1, pos_tab2, pos_tab3, pos_tab4 = st.tabs(["💠 全员", "🛡️ 后卫", "⚔️ 锋线", "🦍 中锋"])
    
    def render_chart(df, title_suf):
        if df.empty:
            st.info("暂无数据")
            return
        fig = px.bar(df.head(20), x='Final_Score', y='Display_Name', orientation='h',
                     color='Score_Prod', color_continuous_scale='Viridis', text_auto='.1f',
                     title=f"排名 {title_suf} (颜色=统治力)")
        fig.update_layout(yaxis={'categoryorder':'total ascending', 'title':''}, xaxis={'title':'Franchise Player Score'}, height=600)
        st.plotly_chart(fig, use_container_width=True)

    with pos_tab1: render_chart(season_ranked, "(全员)")
    with pos_tab2: render_chart(season_ranked[season_ranked['Calc_Pos']=='Guard'], "(后卫)")
    with pos_tab3: render_chart(season_ranked[season_ranked['Calc_Pos']=='Forward'], "(锋线)")
    with pos_tab4: render_chart(season_ranked[season_ranked['Calc_Pos']=='Center'], "(中锋)")

with main_tab2:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("新秀对比")
        p_list = season_ranked['Display_Name'].tolist()
        p1 = st.selectbox("球员 1", p_list, index=0)
        p2 = st.selectbox("球员 2", p_list, index=1 if len(p_list)>1 else 0)
        
    with c2:
        def get_radar_vals(name):
            r = season_ranked[season_ranked['Display_Name'] == name].iloc[0]
            return [r['Score_Prod'], r['Score_Eff'], r['Score_Def'], r['Score_TO'], r['Score_Team'], r['Score_Dura']], r['CN_Name']

        vals1, n1 = get_radar_vals(p1)
        vals2, n2 = get_radar_vals(p2)
        cats = ['统治力', '进攻效率', '个人防守', '失误控制', '球队贡献', '出勤耐用']
        
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=vals1, theta=cats, fill='toself', name=n1))
        fig.add_trace(go.Scatterpolar(r=vals2, theta=cats, fill='toself', name=n2))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 100])), title="六维能力模型对比", height=500)
        st.plotly_chart(fig, use_container_width=True)

with main_tab3:
    st.subheader("数据监控室")
    st.markdown(f"统计范围: **{date_from_str if date_from_str else '赛季至今'}** 至 **{date_to_str if date_to_str else '今'}**")
    
    # 增加 Rank (排名) 和 Pick (顺位)
    cols = ['Rank', 'Pick', 'Display_Name', 'Pos_Display', 'Final_Score', 
            'Score_Dura',
            'Score_Prod', 'Score_Eff', 'Score_Def', 'Score_TO', 'Score_Team',
            'GP', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PLUS_MINUS',
            'FG_PCT', 'FG3_PCT', 'FT_PCT',
            'USG_PCT', 'PCT_UAST_FGM', 'TS_PCT']
    
    show_df = season_ranked[cols].rename(columns={
        'Rank': '排名', 'Pick': '顺位',
        'Display_Name': '球员', 'Pos_Display': '位置', 'Final_Score': '总分',
        'Score_Dura': '出勤分',
        'Score_Prod': '统治', 'Score_Eff': '效率', 'Score_Def': '防守', 'Score_TO': '控失', 'Score_Team': '贡献',
        'GP': '场次', 'MIN': '时间', 'PTS': '得分', 'REB': '篮板', 'AST': '助攻', 'STL': '抢断', 'BLK': '盖帽', 'TOV': '失误', 'PLUS_MINUS': '正负值',
        'FG_PCT': '投篮%', 'FG3_PCT': '三分%', 'FT_PCT': '罚球%',
        'USG_PCT': '球权%', 'PCT_UAST_FGM': '非助攻%', 'TS_PCT': '真命%'
    })
    
    st.dataframe(
        show_df,
        column_config={
            "排名": st.column_config.NumberColumn("排名", format="#%d"),
            "顺位": st.column_config.NumberColumn("顺位", format="#%d"),
            "总分": st.column_config.ProgressColumn("总分", format="%.1f", min_value=0, max_value=100),
            "出勤分": st.column_config.NumberColumn("出勤分", format="%.1f"),
            "场次": st.column_config.NumberColumn("场次", format="%d"),
            "时间": st.column_config.NumberColumn("时间", format="%.1f"),
            "真命%": st.column_config.NumberColumn("真实命中%", format="%.1%"),
            "投篮%": st.column_config.NumberColumn("投篮%", format="%.1%"),
            "三分%": st.column_config.NumberColumn("三分%", format="%.1%"),
            "罚球%": st.column_config.NumberColumn("罚球%", format="%.1%"),
            "球权%": st.column_config.NumberColumn("使用率%", format="%.1%"),
            "非助攻%": st.column_config.NumberColumn("非受助攻%", format="%.1%"),
            "正负值": st.column_config.NumberColumn("正负值", format="%+.1f"),
            "得分": st.column_config.NumberColumn("得分", format="%.1f"),
            "篮板": st.column_config.NumberColumn("篮板", format="%.1f"),
            "助攻": st.column_config.NumberColumn("助攻", format="%.1f"),
            "抢断": st.column_config.NumberColumn("抢断", format="%.1f"),
            "盖帽": st.column_config.NumberColumn("盖帽", format="%.1f"),
            "失误": st.column_config.NumberColumn("失误", format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
        height=800
    )
