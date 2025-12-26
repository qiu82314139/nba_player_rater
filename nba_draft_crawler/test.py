import pandas as pd
import requests
import time
import random

# --- 修改点 1: 修正 AAC 的代码为 'american' ---
TARGET_CONFERENCES = [
    'acc',
    'sec',
    'big-12',
    'big-ten',
    'big-east',
    'wcc',
    'american',  # 修正: AAC 在 URL 里叫 'american'
    'mwc'
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def get_conference_stats(conf, year=2026):
    url = f"https://www.sports-reference.com/cbb/conferences/{conf}/{year}-stats.html"
    print(f"[{conf.upper()}] 正在抓取: {url} ...")

    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 404:
            print(f"  -> 警告: 找不到 {conf} 的页面")
            return None

        dfs = pd.read_html(response.content)

        # 寻找球员表
        player_df = None
        for df in dfs:
            if 'Player' in df.columns and 'PTS' in df.columns:
                player_df = df
                break

        if player_df is None:
            return None

        # 清洗
        player_df = player_df[player_df['Player'] != 'Player']

        cols_to_numeric = ['G', 'MP', 'FG', 'FGA', 'TRB', 'AST', 'STL', 'BLK', 'PTS', '3P']  # 增加 3P 以防万一
        for col in cols_to_numeric:
            if col in player_df.columns:
                player_df[col] = pd.to_numeric(player_df[col], errors='coerce')

        player_df['Conference'] = conf.upper()
        return player_df

    except Exception as e:
        print(f"  -> 错误: {e}")
        return None


def calculate_advanced_stats(df):
    # 确保 MP (场均分钟) > 0
    df = df[df['MP'] > 0].copy()

    # --- 修改点 3: 既然是 Per Game 数据，直接计算 Per 40 ---
    # 公式: (场均数据 / 场均分钟) * 40
    df['PTS_Per40'] = (df['PTS'] / df['MP']) * 40
    df['TRB_Per40'] = (df['TRB'] / df['MP']) * 40
    df['AST_Per40'] = (df['AST'] / df['MP']) * 40

    # 简单效率 eFG%
    if 'FG' in df.columns and 'FGA' in df.columns and '3P' in df.columns:
        df['3P'] = df['3P'].fillna(0)
        # 防止除以0
        df['eFG%'] = df.apply(lambda x: (x['FG'] + 0.5 * x['3P']) / x['FGA'] if x['FGA'] > 0 else 0, axis=1)

    return df


def main_scraper():
    all_players = []

    for conf in TARGET_CONFERENCES:
        df = get_conference_stats(conf, year=2026)
        if df is not None:
            all_players.append(df)
        time.sleep(random.uniform(2, 4))  # 稍微加快一点频率

    if all_players:
        full_data = pd.concat(all_players, ignore_index=True)

        full_data = calculate_advanced_stats(full_data)

        # --- 修改点 3 (续): 直接用 MP (因为它是场均) 筛选 ---
        # 筛选：场均出场时间 > 15 分钟
        final_view = full_data[(full_data['MP'] > 15) & (full_data['G'] > 3)]

        print("\n--- 抓取完成 ---")
        print(f"共收集 {len(final_view)} 名核心轮换球员数据。")

        # --- 修改点 2: 将 'School' 改为 'Team' ---
        # 顺便检查 eFG% 是否存在，不存在就不打印
        cols_to_show = ['Player', 'Team', 'Conference', 'PTS_Per40']
        if 'eFG%' in final_view.columns:
            cols_to_show.append('eFG%')

        print("预览前5名得分手 (Per 40):")
        print(final_view[cols_to_show].sort_values(by='PTS_Per40', ascending=False).head())

        return final_view
    else:
        return None


# 运行
df_2026 = main_scraper()
if df_2026 is not None:
    df_2026.to_csv('ncaa_2026_prospects_fixed.csv', index=False)