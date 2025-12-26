from bs4 import BeautifulSoup
from crawler.utils import get_soup
from config import BASE_URL

def fetch_roster(team):
    html = get_soup(team["season_url"])
    soup = BeautifulSoup(html, "html.parser")

    players = []
    table = soup.find("table", {"id": "roster"})
    if not table:
        return players

    for row in table.tbody.find_all("tr"):
        name_cell = row.find("th")
        if not name_cell.find("a"):
            continue

        name = name_cell.text.strip()
        url = BASE_URL + name_cell.find("a")["href"]

        players.append({
            "name": name,
            "player_url": url,
            "school": team["school"]
        })

    return players


def fetch_player_season(player):
    html = get_soup(player["player_url"])
    soup = BeautifulSoup(html, "html.parser")

    data = {
        "name": player["name"],
        "school": player["school"],
        "seasons": []
    }

    table = soup.find("table", {"id": "players_per_game"})
    if not table:
        return data

    for row in table.tbody.find_all("tr"):
        season = row.find("th").text.strip()
        stats = {"season": season}

        for td in row.find_all("td"):
            stats[td["data-stat"]] = td.text

        data["seasons"].append(stats)

    return data