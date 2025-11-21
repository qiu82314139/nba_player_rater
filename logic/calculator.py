from typing import Dict
from config.settings import SCORING_THRESHOLDS, WEIGHTS, DEFENSE_MULTIPLIERS, SHOOTING_VOLUME_MAX

def normalize(value: float, min_val: float, max_val: float) -> int:
    if max_val == min_val:
        return 60
    score = 60 + (value - min_val) / (max_val - min_val) * 40
    if score < 60:
        return 60
    if score > 99:
        return 99
    return int(round(score))

def calculate_sub_scores(stats: Dict, archetype: str, sliders: Dict) -> Dict[str, int]:
    ts_min, ts_max = SCORING_THRESHOLDS["TS_PCT"][archetype]
    scoring = normalize(stats.get("TS_PCT", 0.0), ts_min, ts_max)
    ast_min, ast_max = SCORING_THRESHOLDS["AST_PCT"][archetype]
    playmaking = normalize(stats.get("AST_PCT", 0.0), ast_min, ast_max)
    if stats.get("AST_TO", 0.0) < 2.0:
        playmaking = max(60, playmaking - 5)
    three_min, three_max = SCORING_THRESHOLDS["THREE_PCT"][archetype]
    shooting_base = normalize(stats.get("THREE_PCT", 0.0), three_min, three_max)
    vol_cap = SHOOTING_VOLUME_MAX[archetype]
    vol_ratio = min(1.0, stats.get("THREE_PM", 0.0) / vol_cap)
    shooting = min(99, int(round(shooting_base + vol_ratio * 10)))
    reb_min, reb_max = SCORING_THRESHOLDS["REB_PCT"][archetype]
    rebounding = normalize(stats.get("REB_PCT", 0.0), reb_min, reb_max)
    dm = DEFENSE_MULTIPLIERS[archetype]
    data_def = 60 + stats.get("STL_PCT", 0.0) * dm["stl"] + stats.get("BLK_PCT", 0.0) * dm["blk"]
    if data_def < 60:
        data_def = 60
    if data_def > 99:
        data_def = 99
    def_slider = sliders.get("def_eye_test", 75)
    defense = int(round(0.4 * data_def + 0.6 * def_slider))
    isolation = int(sliders.get("isolation", 75))
    clutch = int(sliders.get("clutch", 75))
    scores = {
        "Scoring": scoring,
        "Playmaking": playmaking,
        "Shooting": shooting,
        "Rebounding": rebounding,
        "Defense": defense,
        "Isolation": isolation,
        "Clutch": clutch
    }
    return scores

def calculate_ovr(sub_scores: Dict[str, int], archetype: str) -> int:
    weights = WEIGHTS[archetype]
    total = 0.0
    total += sub_scores["Scoring"] * weights["Scoring"]
    total += sub_scores["Playmaking"] * weights["Playmaking"]
    total += sub_scores["Defense"] * weights["Defense"]
    total += sub_scores["Rebounding"] * weights["Rebounding"]
    total += sub_scores["Clutch"] * weights["Clutch"]
    total += sub_scores["Isolation"] * weights["Isolation"]
    if total < 60:
        total = 60
    if total > 99:
        total = 99
    return int(round(total))

def get_tier_badge(ovr: int) -> str:
    if ovr >= 96:
        return "T0"
    if ovr >= 90:
        return "T1"
    if ovr >= 85:
        return "T1.5"
    if ovr >= 80:
        return "T2"
    return "T3"