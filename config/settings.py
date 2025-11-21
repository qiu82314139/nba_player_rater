ARCHETYPES = [
    "后卫组 (Guards)",
    "锋线组 (Wings)",
    "内线组 (Bigs)"
]

THEME_COLORS = {
    "后卫组 (Guards)": "#00F0FF",
    "锋线组 (Wings)": "#FF0055",
    "内线组 (Bigs)": "#00FF99"
}

WEIGHTS = {
    "后卫组 (Guards)": {
        "Scoring": 0.25,
        "Playmaking": 0.30,
        "Defense": 0.15,
        "Rebounding": 0.05,
        "Clutch": 0.10,
        "Isolation": 0.15
    },
    "锋线组 (Wings)": {
        "Scoring": 0.25,
        "Playmaking": 0.10,
        "Defense": 0.30,
        "Rebounding": 0.10,
        "Clutch": 0.10,
        "Isolation": 0.15
    },
    "内线组 (Bigs)": {
        "Scoring": 0.20,
        "Playmaking": 0.10,
        "Defense": 0.35,
        "Rebounding": 0.25,
        "Clutch": 0.05,
        "Isolation": 0.05
    }
}

SCORING_THRESHOLDS = {
    "TS_PCT": {
        "后卫组 (Guards)": [0.50, 0.65],
        "锋线组 (Wings)": [0.52, 0.68],
        "内线组 (Bigs)": [0.55, 0.72]
    },
    "AST_PCT": {
        "后卫组 (Guards)": [0.10, 0.45],
        "锋线组 (Wings)": [0.05, 0.30],
        "内线组 (Bigs)": [0.03, 0.35]
    },
    "REB_PCT": {
        "后卫组 (Guards)": [0.03, 0.12],
        "锋线组 (Wings)": [0.06, 0.18],
        "内线组 (Bigs)": [0.10, 0.24]
    },
    "THREE_PCT": {
        "后卫组 (Guards)": [0.33, 0.40],
        "锋线组 (Wings)": [0.30, 0.38],
        "内线组 (Bigs)": [0.25, 0.36]
    }
}

SHOOTING_VOLUME_MAX = {
    "后卫组 (Guards)": 4.0,
    "锋线组 (Wings)": 2.5,
    "内线组 (Bigs)": 1.5
}

DEFENSE_MULTIPLIERS = {
    "后卫组 (Guards)": {"stl": 10.0, "blk": 2.0},
    "锋线组 (Wings)": {"stl": 6.0, "blk": 6.0},
    "内线组 (Bigs)": {"stl": 2.0, "blk": 8.0}
}