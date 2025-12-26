from crawler.teams import fetch_teams
from crawler.players import fetch_roster, fetch_player_season
from storage.save import save_json

def main():
    print("▶ 抓取 NCAA 球队中...")
    teams = fetch_teams()
    save_json("teams.json", teams)

    all_players = []
    all_player_seasons = []

    for team in teams:
        print(f"▶ 抓取 {team['school']} roster")
        players = fetch_roster(team)
        all_players.extend(players)

        for player in players:
            print(f"  ▶ 抓取球员 {player['name']}")
            season_data = fetch_player_season(player)
            all_player_seasons.append(season_data)

    save_json("players.json", all_players)
    save_json("player_seasons.json", all_player_seasons)

    print("✅ 数据抓取完成")

if __name__ == "__main__":
    main()