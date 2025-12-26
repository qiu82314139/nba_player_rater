import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import REQUEST_DELAY

def create_session():
    session = requests.Session()

    # 非常重要：像真实浏览器
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    # 自动重试策略
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


# 全局 Session（非常关键）
SESSION = create_session()


def get_soup(url):
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        time.sleep(REQUEST_DELAY)
        return resp.text
    except requests.exceptions.RequestException as e:
        print(f"⚠️ 请求失败: {url}")
        print(e)
        return None