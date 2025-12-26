import pandas as pd
import time
from io import StringIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 配置 ---
MY_WATCHLIST = "players_2026.csv"
SEASON_YEAR = "2026"

# 修改 URL: 尝试去除 minmin 限制，或者调整参数以获取更多人
# xds=stats 表示基础数据，num=0 通常表示显示所有(或前100)
DIAGNOSTIC_URL = f"https://barttorvik.com/playerstat.php?year={SEASON_YEAR}&minmin=1"


def diagnose():
    # 1. 读取你的名单
    try:
        watchlist_df = pd.read_csv(MY_WATCHLIST)
        print(f"📋 你的本地名单 (前3个):")
        print(watchlist_df['Name'].head(3).tolist())
    except FileNotFoundError:
        print("❌ 找不到 players_2026.csv")
        return

    # 2. 启动浏览器
    print(f"\n🚀 正在访问 Barttorvik: {DIAGNOSTIC_URL}")
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 建议开启窗口，观察是否只有一页数据
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(DIAGNOSTIC_URL)
        print("⏳ 等待加载 (10秒)...")
        time.sleep(10)

        page_source = driver.page_source

        # 3. 尝试解析表格
        print("\n📊 正在解析表格...")
        # Barttorvik 经常有多个 table，我们遍历所有 table 找含有 'Player' 的
        dfs = pd.read_html(StringIO(page_source))

        target_df = None
        for i, df in enumerate(dfs):
            # 打印每个表格的列名，帮我们确认结构
            print(f"   [Table {i}] 列名: {df.columns.tolist()[:5]}... (共{len(df)}行)")
            if 'Player' in df.columns:
                target_df = df
                break

        if target_df is None:
            print("❌ 未找到包含 'Player' 列的表格。可能反爬或网页结构变了。")
            return

        print(f"\n✅ 锁定目标表格！共抓取到 {len(target_df)} 名球员的数据。")

        # 4. 深度诊断：名字到底长什么样？
        print("\n🔍 --- 名字格式样本 (Barttorvik 前5名) ---")
        # 打印前5行的 Player 列和 Team 列
        if 'Team' in target_df.columns:
            print(target_df[['Player', 'Team']].head(5))
        else:
            print(target_df['Player'].head(5))

        # 5. 关键测试：你的球员在里面吗？
        # 我们用几个关键词去搜
        test_names = ["Boozer", "Dybantsa", "Peterson", "Wilson"]
        print(f"\n🕵️‍♂️ --- 关键词搜索测试 (在 {len(target_df)} 名球员中查找) ---")

        target_df['Player_Str'] = target_df['Player'].astype(str)

        found_any = False
        for keyword in test_names:
            # 模糊搜索
            matches = target_df[target_df['Player_Str'].str.contains(keyword, case=False, na=False)]
            if not matches.empty:
                found_any = True
                print(f"   ✅ 找到 '{keyword}':")
                print(matches[['Player', 'Team', 'Pts', 'GP']].to_string(index=False))
            else:
                print(f"   ❌ 未找到 '{keyword}'")

        if not found_any:
            print("\n⚠️ 结论：根本没有抓到你的球员。")
            print("   可能原因 1: 抓取的数量太少 (只有52人?)，你需要翻页或者修改URL参数。")
            print("   可能原因 2: 2026赛季参数下，这些人真的还没录入 Barttorvik。")
        else:
            print("\n💡 结论：球员在里面！是名字匹配逻辑的问题。")
            print("   -> 请看上面的 '找到' 结果，对比你的 CSV 名字，看区别在哪里（比如是否包含队名）。")

    except Exception as e:
        print(f"❌ 运行错误: {e}")
    finally:
        driver.quit()


if __name__ == "__main__":
    diagnose()