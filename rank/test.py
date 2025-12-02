from nba_api.stats.endpoints import leaguedashptdefend

# 不要传 date_from/date_to，只传赛季
defense = leaguedashptdefend.LeagueDashPtDefend(
    season='2024-25',
    defense_category='Overall',
    per_mode_simple='PerGame',
    season_type_all_star='Regular Season'
).get_data_frames()[0]

# 看看列名到底叫什么
print(defense.columns)