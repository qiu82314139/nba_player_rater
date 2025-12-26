import pandas as pd
import time
import urllib.parse
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re

# --- 配置 ---
INPUT_FILE = "players_2026.csv"
OUTPUT_FILE = "players_with_advanced_stats.csv"  # 新文件名
SEASON_YEAR = "2026"


def clean_name_for_url(name):
    name = name.replace(" Jr.", "").replace(" III", "").replace(" II", "")
    return urllib.parse.quote(name)


def get_barttorvik_stats():
    try:
        df = pd.read_csv(INPUT_FILE)
        print(f"📖 读取名单成功，共 {len(df)} 人。")
    except FileNotFoundError:
        print("❌ 找不到 CSV 文件。")
        return

    chrome_options = Options()
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    stats_list = []
    print(f"🚀 开始全维数据追踪 (得分/助攻/篮板/防守/效率)...")

    for index, row in df.iterrows():
        original_name = row['Name']
        search_name = clean_name_for_url(original_name)
        url = f"https://barttorvik.com/playerstat.php?year={SEASON_YEAR}&p={search_name}&t=0"

        print(f"[{index + 1}/{len(df)}] 分析: {original_name} ...", end=" ", flush=True)

        try:
            driver.get(url)

            # 冷启动
            if index == 0:
                print("\n   ⏳ 首次连接等待 12秒...")
                time.sleep(12)
            else:
                time.sleep(1.5)

            page_source = driver.page_source

            if "No stats found" in page_source:
                print(f"⚪ 无数据 (HS)")
                row_dict = row.to_dict()
                row_dict.update({'Status': 'No Data', 'PTS': 0})
                stats_list.append(row_dict)
                continue

            soup = BeautifulSoup(page_source, 'html.parser')
            tables = soup.find_all('table')

            target_table = None
            for tbl in tables:
                if 'Opponent' in tbl.get_text() and 'Pts' in tbl.get_text():
                    target_table = tbl
                    break

            if target_table:
                # --- 🔥 核心升级：智能表头映射 ---
                # 我们先找到表头行，确定 'Ast', 'Blk', 'Stl' 分别在第几列
                rows = target_table.find_all('tr')
                header_map = {}
                data_row = None

                # 1. 扫描表头
                for r in rows[:5]:  # 只看前5行
                    cells = r.find_all(['th', 'td'])
                    cell_texts = [c.get_text(strip=True).lower() for c in cells]

                    if 'opponent' in cell_texts or 'opp' in cell_texts:
                        # 建立映射: {'ast': 10, 'blk': 12, ...}
                        for idx, txt in enumerate(cell_texts):
                            header_map[txt] = idx
                        break

                # 2. 扫描最新数据行 (倒序)
                for r in reversed(rows):
                    cells = r.find_all(['td', 'th'])
                    row_text = [c.get_text(strip=True) for c in cells]
                    line_str = " ".join(row_text)

                    if 'Total' in line_str or 'Average' in line_str or 'Opponent' in line_str:
                        continue

                    if len(row_text) > 5 and '-' in row_text[0]:
                        data_row = row_text
                        break

                if data_row and header_map:
                    # --- 提取多维数据 ---
                    def get_stat(key_list, default="0"):
                        # 尝试不同的列名写法，比如 'ast' 或 'assist'
                        for key in key_list:
                            idx = header_map.get(key)
                            if idx is not None and idx < len(data_row):
                                return data_row[idx]
                        return default

                    # 基础数据
                    pts = get_stat(['pts'])
                    ast = get_stat(['ast'])
                    blk = get_stat(['blk'])
                    stl = get_stat(['stl'])
                    to = get_stat(['to'])

                    # 篮板 (Barttorvik 只有 OR 和 DR，我们需要手动加)
                    # 有些表格有 Tot Reb，有些没有，这里简单处理
                    dr = int(get_stat(['dr'], "0"))
                    or_ = int(get_stat(['or'], "0"))
                    reb = str(dr + or_)

                    # 进阶效率 (Barttorvik 表格里通常有 TS, Usg, ORtg)
                    ts = get_stat(['ts', 'ts%'], "N/A")
                    usg = get_stat(['usg', 'usage'], "N/A")
                    ortg = get_stat(['ortg'], "N/A")

                    last_opp = data_row[header_map.get('opponent', 1)] if 'opponent' in header_map else data_row[1]

                    print(f"✅ 全能数据: {pts}分 {ast}助 {reb}板 | TS: {ts}%")

                    full_record = {**row.to_dict(), **{
                        'Last_Opponent': last_opp,
                        'Last_Date': data_row[0],
                        'PTS': pts,
                        'AST': ast,
                        'REB': reb,
                        'BLK': blk,
                        'STL': stl,
                        'TOV': to,
                        'TS%': ts,
                        'USG%': usg,
                        'ORtg': ortg,
                        'Status': 'Active'
                    }}
                    stats_list.append(full_record)
                else:
                    # 如果找不到表头映射，回退到只抓分数的简单模式
                    print("⚠️ 表头解析失败，跳过")
            else:
                print(f"⚠️ 未找到数据表")
                row_dict = row.to_dict()
                row_dict.update({'Status': 'No Table', 'PTS': 0})
                stats_list.append(row_dict)

        except Exception as e:
            print(f"❌ 错误: {e}")
            stats_list.append(row.to_dict())

    driver.quit()

    if stats_list:
        result_df = pd.DataFrame(stats_list)
        result_df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n🎉 全维数据已保存至 {OUTPUT_FILE}")


if __name__ == "__main__":
    get_barttorvik_stats()