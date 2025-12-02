import pandas as pd
import time
from nba_api.stats.endpoints import SynergyPlayTypes, PlayerDashPtShots
from nba_api.stats.static import players

# --- 1. 设置对比对象 ---
KLAY_SEASON = '2015-16'
KON_SEASON = '2025-26'


def get_player_id(name):
    try:
        p = players.find_players_by_full_name(name)
        return p[0]['id'] if p else None
    except:
        return None


# --- 2. 获取进攻方式 (Synergy Play Type) ---
def get_synergy_data(player_id, season):
    target_play_types = {
        "OffScreen": "绕掩护 (Off Screen)",
        "PRBallHandler": "挡拆持球 (P&R Handler)",
        "Isolation": "单打 (Isolation)",
        "Spotup": "定点投突 (Spot-up)"
    }

    results = {}
    try:
        print(f"   正在拉取 Synergy 数据: {season}...")
        for pt_key, pt_name in target_play_types.items():
            time.sleep(0.6)

            synergy = SynergyPlayTypes(
                player_or_team_abbreviation='P',
                play_type_nullable=pt_key,
                season=season,
                type_grouping_nullable='offensive',
                per_mode_simple='PerGame',
                season_type_all_star='Regular Season'
            )
            df = synergy.get_data_frames()[0]

            player_stats = df[df['PLAYER_ID'] == player_id]

            if not player_stats.empty:
                # --- 【强制修正】 ---
                # 根据Debug结果，列名绝对是 POSS_PCT。不再尝试其他名字。
                # 如果这里报错，说明API返回的结构在瞬间变了，或者数据为空。
                if 'POSS_PCT' in player_stats.columns:
                    freq = player_stats['POSS_PCT'].values[0]
                    ppp = player_stats['PPP'].values[0]
                    results[pt_name] = f"{freq * 100:.1f}% (效率: {ppp:.2f})"
                else:
                    # 最后的防线：如果真的没有这一列，打印出当前有什么
                    print(f"   [调试] 找不到 POSS_PCT。当前列名: {player_stats.columns.tolist()}")
                    results[pt_name] = "列名错误"
            else:
                results[pt_name] = "0.0% (无数据)"

    except Exception as e:
        print(f"   [!] 获取 Synergy 数据出错 ({season}): {e}")
        return {}

    return results


# --- 3. 获取投篮分布 (Tracking: C&S vs Pull-up) ---
def get_shooting_tracking(player_id, season):
    try:
        print(f"   正在拉取 Tracking 数据: {season}...")
        dash = PlayerDashPtShots(
            player_id=player_id,
            team_id=0,
            season=season,
            season_type_all_star="Regular Season",
            month=0,
            opponent_team_id=0,
            period=0,
            last_n_games=0,
            outcome_nullable="",
            location_nullable="",
            season_segment_nullable="",
            date_from_nullable="",
            date_to_nullable="",
            vs_conference_nullable="",
            vs_division_nullable="",
            game_segment_nullable=""
        )

        df = dash.get_data_frames()[1]
        if df.empty: return {}

        cs_data = df[df['SHOT_TYPE'] == 'Catch and Shoot']
        pu_data = df[df['SHOT_TYPE'] == 'Pull Ups']

        res = {}

        if not cs_data.empty:
            cs_freq = cs_data['FG3A_FREQUENCY'].values[0]
            cs_fg3 = cs_data['FG3_PCT'].values[0]
            res['接球投 (C&S) 三分命中率'] = f"{cs_fg3 * 100:.1f}%"
            res['接球投 (C&S) 占比'] = f"{cs_freq * 100:.1f}%"
        else:
            res['接球投 (C&S) 三分命中率'] = "N/A"

        if not pu_data.empty:
            pu_freq = pu_data['FG3A_FREQUENCY'].values[0]
            pu_fg3 = pu_data['FG3_PCT'].values[0]
            pu_efg = pu_data['EFG_PCT'].values[0]
            res['运球投 (Pull-up) 三分命中率'] = f"{pu_fg3 * 100:.1f}%"
            res['运球投 (Pull-up) 有效命中率'] = f"{pu_efg * 100:.1f}%"
            res['运球投 (Pull-up) 占比'] = f"{pu_freq * 100:.1f}%"
        else:
            res['运球投 (Pull-up) 三分命中率'] = "N/A"

        return res

    except Exception as e:
        print(f"   [!] 获取 Tracking 数据出错 ({season}): {e}")
        return {}


# --- 4. 辅助函数 ---
def format_data(klay_d, kon_d):
    data = []
    if not klay_d: klay_d = {}
    if not kon_d: kon_d = {}

    all_keys = list(set(list(klay_d.keys()) + list(kon_d.keys())))
    # 逻辑排序
    all_keys.sort(key=lambda x: "占比" in x or "OffScreen" in x or "BallHandler" in x, reverse=True)

    for k in all_keys:
        data.append({
            "对比维度": k,
            "巅峰克莱 (15-16)": klay_d.get(k, "-"),
            "新秀克努佩尔 (25-26)": kon_d.get(k, "-")
        })
    return pd.DataFrame(data)


# --- 5. 主程序 ---
if __name__ == "__main__":
    print(f"\n>>> 开始拉取最终对比: 克莱({KLAY_SEASON}) vs 克努佩尔({KON_SEASON})")

    klay_id = get_player_id("Klay Thompson")
    kon_id = get_player_id("Kon Knueppel")

    # 1. 跑克莱数据
    print(f"\n--- 获取克莱·汤普森数据 ---")
    klay_synergy = get_synergy_data(klay_id, KLAY_SEASON)
    klay_tracking = get_shooting_tracking(klay_id, KLAY_SEASON)

    # 2. 跑克努佩尔数据
    kon_synergy = {}
    kon_tracking = {}

    if kon_id:
        print(f"\n--- 获取康·克努佩尔数据 ---")
        kon_synergy = get_synergy_data(kon_id, KON_SEASON)
        kon_tracking = get_shooting_tracking(kon_id, KON_SEASON)

        # 兜底：如果 Tracking 有数据但 Synergy 没数据
        if not kon_synergy: kon_synergy = {"提示": "暂无Synergy数据"}
    else:
        print(f"\n[!] 警告: 未找到 Kon Knueppel 的 ID。")

    # 3. 输出表格
    print("\n" + "=" * 60)
    if klay_synergy or kon_synergy:
        df1 = format_data(klay_synergy, kon_synergy)
        print("【战术风格对比 (Play Type) - 终极版】")
        try:
            print(df1.to_markdown(index=False))
        except:
            print(df1.to_string(index=False))
        print("-" * 60)

    if klay_tracking or kon_tracking:
        df2 = format_data(klay_tracking, kon_tracking)
        print("【投篮机制对比 (Tracking Data) - 终极版】")
        try:
            print(df2.to_markdown(index=False))
        except:
            print(df2.to_string(index=False))
    print("=" * 60)