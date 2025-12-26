from bs4 import BeautifulSoup, Comment
from config import BASE_URL, SEASON
from crawler.utils import get_soup


SCHOOL_URLS = [
    f"{BASE_URL}/cbb/schools/",
    f"{BASE_URL}/cbb/schools/?view=active"  # ✅ 稳定备用
]


def extract_schools_table(soup):
    """
    从 soup 或其 HTML 注释中提取 schools 表
    """
    table = soup.find("table", {"id": "schools"})
    if table:
        return table

    # 🔥 注释解封
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        if 'id="schools"' in comment:
            comment_soup = BeautifulSoup(comment, "html.parser")
            table = comment_soup.find("table", {"id": "schools"})
            if table:
                return table
    return None


def fetch_teams():
    for url in SCHOOL_URLS:
        print(f"🌐 尝试抓取学校列表: {url}")
        html = get_soup(url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        table = extract_schools_table(soup)

        if not table:
            print("⚠️ 当前入口未返回 schools 表，尝试下一个入口")
            continue

        teams = []
        for row in table.tbody.find_all("tr"):
            th = row.find("th")
            if not th or not th.find("a"):
                continue

            school = th.text.strip()
            link = th.find("a")["href"]

            teams.append({
                "school": school,
                "url": BASE_URL + link,
                "season_url": BASE_URL + link.replace(".html", f"/{SEASON}.html")
            })

        print(f"✅ 成功抓取 {len(teams)} 支 NCAA 球队")
        return teams

    print("❌ 所有 schools 入口均失败，可能被临时限流")
    return []