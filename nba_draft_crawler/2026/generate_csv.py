import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 2026年选秀页面
TARGET_URL = "https://www.tankathon.com/mock_draft"
OUTPUT_FILE = "players_2026.csv"


def get_tankathon_data_final():
    print(f"🚀 启动浏览器访问: {TARGET_URL}")

    chrome_options = Options()
    # chrome_options.add_argument("--headless") # 调试成功后可取消注释
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(TARGET_URL)
        print("⏳ 等待页面加载 (6秒)...")
        time.sleep(6)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        rows = soup.find_all('div', class_='mock-row')

        print(f"✅ 定位到 {len(rows)} 个数据行。开始解析...")

        players_data = []

        for i, row in enumerate(rows):
            try:
                # 1. 提取排名 (修正 Class 名: mock-row-pick-number)
                rank_div = row.find('div', class_='mock-row-pick-number')
                rank = rank_div.get_text(strip=True) if rank_div else str(i + 1)

                # 2. 提取关键链接 (修正: 搜索 /players/ 复数)
                link_tag = row.find('a', href=lambda x: x and '/players/' in x)

                if not link_tag:
                    # 备用方案: 只要是在 mock-row-player 下的链接就行
                    player_div = row.find('div', class_='mock-row-player')
                    if player_div:
                        link_tag = player_div.find('a')

                if not link_tag:
                    print(f"⚠️ 第 {i + 1} 行未找到球员链接，跳过。")
                    continue

                # 3. 提取名字 (在 mock-row-name div 中)
                name_div = link_tag.find('div', class_='mock-row-name')
                # 如果找不到专门的 div，就直接取链接文本
                name = name_div.get_text(strip=True) if name_div else link_tag.get_text(strip=True)

                # 4. 提取 URL
                full_url = f"https://www.tankathon.com{link_tag['href']}"

                # 5. 提取位置和学校 (HTML显示它们混在一起: SG/PG | Kansas)
                # Class: mock-row-school-position
                school_pos_div = link_tag.find('div', class_='mock-row-school-position')
                school_raw = school_pos_div.get_text(strip=True) if school_pos_div else "N/A"

                # 简单清洗一下，把位置和学校分开 (如果你需要)
                # 比如 "SG/PG | Kansas" -> School: Kansas
                if "|" in school_raw:
                    school = school_raw.split("|")[-1].strip()
                else:
                    school = school_raw

                players_data.append({
                    'Rank': rank,
                    'Name': name,
                    'School': school,
                    'Raw_Info': school_raw,  # 保留原始信息备用
                    'URL': full_url
                })

            except Exception as e:
                print(f"❌ 解析第 {i + 1} 行时出错: {e}")
                continue

        return players_data

    except Exception as e:
        print(f"❌ 程序错误: {e}")
        return []

    finally:
        driver.quit()


def main():
    data = get_tankathon_data_final()

    if data:
        df = pd.DataFrame(data)
        df.to_csv(OUTPUT_FILE, index=False)
        print(f"\n🎉 完美抓取！共 {len(data)} 人。")
        print(f"名单已保存至: {OUTPUT_FILE}")
        # 打印前3行预览
        print("\n数据预览:")
        print(df.head(3).to_string())
    else:
        print("\n⚠️ 列表依然为空，请检查网络。")


if __name__ == "__main__":
    main()