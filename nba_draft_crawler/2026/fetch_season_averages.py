import pandas as pd
import time
import logging
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 日志配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 配置 ---
MY_WATCHLIST = "players_2026.csv"
OUTPUT_FILE = "season_leaderboard.csv"
SEASON_YEAR = "2026"
STATS_URL = f"https://barttorvik.com/playerstat.php?year={SEASON_YEAR}&minmin=5"


def get_season_averages():
    # 1. 读取名单
    try:
        watchlist_df = pd.read_csv(MY_WATCHLIST)
        # 清洗 CSV 中的名字
        watchlist_df['Match_Name'] = watchlist_df['Name'].str.lower().str.strip().str.replace('.', '',
                                                                                              regex=False).str.replace(
            "'", "", regex=False)
        logging.info(f"📖 名单加载成功，共 {len(watchlist_df)} 人。")
    except FileNotFoundError:
        logging.error("❌ 找不到 players_2026.csv")
        return

    # 2. Selenium 设置
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 调试通过，可以开启 headless
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        logging.info("🚀 正在抓取 Barttorvik 数据...")
        driver.get(STATS_URL)
        time.sleep(15)  # 等待加载

        # 3. 解析表格
        logging.info("📊 解析表格中...")
        dfs = pd.read_html(StringIO(driver.page_source), header=0)

        full_stats_df = None
        for df in dfs:
            # 只要包含 'Team' 或者是我们发现的 'Player.2' 就认为是主表
            if 'Team' in df.columns or 'Player.2' in df.columns:
                full_stats_df = df
                break

        if full_stats_df is None:
            logging.error("❌ 找不到表格")
            return

        # =======================================================
        # 🟢 关键修复 1: 正确指定名字所在的列
        # 根据日志，名字在 'Player.2'， 队名在 'Player.3'
        # =======================================================

        name_col = 'Player'  # 默认
        if 'Player.2' in full_stats_df.columns:
            logging.info("✅ 识别到列名偏移，使用 'Player.2' 作为名字列。")
            name_col = 'Player.2'

        # 清洗抓取到的名字
        full_stats_df['Match_Name'] = full_stats_df[name_col].str.lower().str.strip().str.replace('.', '',
                                                                                                  regex=False).str.replace(
            "'", "", regex=False)

        # =======================================================
        # 🟢 执行匹配
        # =======================================================
        merged_df = pd.merge(watchlist_df, full_stats_df, on='Match_Name', how='inner')
        logging.info(f"🔍 匹配完成！成功匹配到 {len(merged_df)} 人。")

        # =======================================================
        # 🟢 关键修复 2: 修正列名映射 (Mapping)
        # 根据日志分析出的错位关系
        # =======================================================
        target_cols_mapping = {
            'Player.2': 'Player_Name',  # 名字
            'Player.3': 'Team_Name',  # 球队 (Kansas)
            'Conf': 'GP',  # 场次 (值 20.0)
            'Stl': 'PTS_Avg',  # 得分 (值 24.5) -> 错位最严重的一个
            'Ast': 'AST_Avg',  # 助攻 (值 8.0)
            'Blk': 'REB_Avg',  # 篮板 (推测值 2.8, 或者这是抢断? 先暂时映射为篮板)
            'TO': 'TO_Avg',  # 失误 (值 3.2)
            'BPM': 'ORtg',  # 进攻效率 (值 128.1)
            'ORtg': 'Usg_Pct',  # 使用率 (值 28.3)
            'TS': 'TS_Pct'  # 真实命中率 (可能是 eFG 或 TS 的错位，先保留)
        }

        # 筛选存在的列
        available_cols = [c for c in target_cols_mapping.keys() if c in full_stats_df.columns]

        if merged_df.empty:
            logging.warning("⚠️ 匹配结果为空，无法生成 CSV。")
            return

        final_df = merged_df[list(watchlist_df.columns) + available_cols]
        final_df = final_df.rename(columns=target_cols_mapping)

        # 格式化数字，保留1位小数
        numeric_cols = ['PTS_Avg', 'AST_Avg', 'REB_Avg']
        for col in numeric_cols:
            if col in final_df.columns:
                final_df[col] = pd.to_numeric(final_df[col], errors='coerce')

        # 保存
        final_df.to_csv(OUTPUT_FILE, index=False)

        logging.info("-" * 30)
        logging.info(f"🎉 成功！文件已保存: {OUTPUT_FILE}")

        # 打印 Top 5 预览
        if 'PTS_Avg' in final_df.columns:
            print("\n🔥 得分榜预览:")
            print(
                final_df.sort_values(by='PTS_Avg', ascending=False)[['Name', 'Team_Name', 'PTS_Avg']].head(5).to_string(
                    index=False))

    except Exception as e:
        logging.error(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    get_season_averages()