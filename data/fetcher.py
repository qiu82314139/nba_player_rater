from typing import Optional, Dict
import pandas as pd
import numpy as np
from datetime import datetime
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguedashplayerstats
import streamlit as st
import requests

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": "stats.nba.com",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/stats/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "x-nba-stats-token": "true",
}

class APIConnectionError(Exception):
    pass

class NBADataFetcher:
    def __init__(self):
        self.timeout = 5

    def search_player(self, player_name: str) -> Optional[int]:
        matches = players.find_players_by_full_name(player_name)
        if matches:
            return matches[0].get("id")
        name_lower = player_name.strip().lower()
        all_players = players.get_players()
        for p in all_players:
            if name_lower in p.get("full_name", "").lower():
                return p.get("id")
        return None

    def _season_str(self) -> str:
        year = datetime.now().year
        if datetime.now().month >= 9:
            start = year
        else:
            start = year - 1
        end = str(start + 1)[-2:]
        return f"{start}-{end}"

    def _prev_season_str(self) -> str:
        cur = self._season_str()
        start = int(cur.split("-")[0]) - 1
        end = str(start + 1)[-2:]
        return f"{start}-{end}"

    def fetch_season_stats(self, player_id: int) -> Dict[str, pd.DataFrame]:
        season_tries = [self._season_str(), self._prev_season_str()]
        last_error = None
        for season in season_tries:
            try:
                base_resp = leaguedashplayerstats.LeagueDashPlayerStats(
                    season=season,
                    per_mode_detailed="PerGame",
                    measure_type_detailed_defense="Base",
                    timeout=self.timeout,
                )
                adv_resp = leaguedashplayerstats.LeagueDashPlayerStats(
                    season=season,
                    per_mode_detailed="PerGame",
                    measure_type_detailed_defense="Advanced",
                    timeout=self.timeout,
                )
                def_resp = leaguedashplayerstats.LeagueDashPlayerStats(
                    season=season,
                    per_mode_detailed="PerGame",
                    measure_type_detailed_defense="Defense",
                    timeout=self.timeout,
                )
                base_df = base_resp.get_data_frames()[0]
                adv_df = adv_resp.get_data_frames()[0]
                def_df = def_resp.get_data_frames()[0]
                base_df = base_df[base_df["PLAYER_ID"] == player_id]
                adv_df = adv_df[adv_df["PLAYER_ID"] == player_id]
                def_df = def_df[def_df["PLAYER_ID"] == player_id]
                if base_df.empty and adv_df.empty and def_df.empty:
                    last_error = "player not found in season tables"
                    continue
                return {"base": base_df, "adv": adv_df, "def": def_df}
            except Exception as e:
                last_error = str(e)
                http_base = self._fetch_ldps_http("Base", season)
                http_adv = self._fetch_ldps_http("Advanced", season)
                http_def = self._fetch_ldps_http("Defense", season)
                if http_base is not None or http_adv is not None or http_def is not None:
                    base_df = http_base[http_base["PLAYER_ID"] == player_id] if http_base is not None else pd.DataFrame()
                    adv_df = http_adv[http_adv["PLAYER_ID"] == player_id] if http_adv is not None else pd.DataFrame()
                    def_df = http_def[http_def["PLAYER_ID"] == player_id] if http_def is not None else pd.DataFrame()
                    if base_df.empty and adv_df.empty and def_df.empty:
                        continue
                    return {"base": base_df, "adv": adv_df, "def": def_df}
                continue
        raise APIConnectionError(last_error or "unknown error")

    def _fetch_ldps_http(self, measure: str, season: str) -> Optional[pd.DataFrame]:
        url = "https://stats.nba.com/stats/leaguedashplayerstats"
        params = {
            "Season": season,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": measure,
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            rs = data.get("resultSets") or []
            if not rs:
                return None
            headers = rs[0].get("headers")
            rows = rs[0].get("rowSet")
            df = pd.DataFrame(rows, columns=headers)
            return df
        except Exception:
            return None

    def _clean_data(self, raw: Dict[str, pd.DataFrame]) -> Dict:
        base = raw.get("base")
        adv = raw.get("adv")
        defn = raw.get("def")
        base = base.iloc[0] if base is not None and not base.empty else pd.Series()
        adv = adv.iloc[0] if adv is not None and not adv.empty else pd.Series()
        defn = defn.iloc[0] if defn is not None and not defn.empty else pd.Series()
        gp = float(base.get("GP", 0.0))
        mpg = float(base.get("MIN", 0.0))
        pts_pg = float(base.get("PTS", 0.0))
        ast_pg = float(base.get("AST", 0.0))
        tov_pg = float(base.get("TOV", 0.0))
        reb_pg = float(base.get("REB", 0.0)) if "REB" in base.index else 0.0
        fg3_pct = float(base.get("FG3_PCT", 0.0))
        fg3m_pg = float(base.get("FG3M", 0.0))
        ts_pct = float(adv.get("TS_PCT", 0.0)) if "TS_PCT" in adv.index else 0.0
        ast_pct = float(adv.get("AST_PCT", 0.0)) if "AST_PCT" in adv.index else 0.0
        reb_pct = float(adv.get("REB_PCT", 0.0)) if "REB_PCT" in adv.index else 0.0
        stl_pct = float(adv.get("STL_PCT", 0.0)) if "STL_PCT" in adv.index else 0.0
        blk_pct = float(adv.get("BLK_PCT", 0.0)) if "BLK_PCT" in adv.index else 0.0
        if (stl_pct == 0.0 or blk_pct == 0.0) and ("STL" in base.index or "BLK" in base.index):
            stl_pg = float(base.get("STL", 0.0))
            blk_pg = float(base.get("BLK", 0.0))
            stl_pct = (stl_pg / max(1.0, mpg)) * 100.0
            blk_pct = (blk_pg / max(1.0, mpg)) * 100.0
        if ts_pct == 0.0:
            fga = float(base.get("FGA", 0.0))
            fta = float(base.get("FTA", 0.0))
            denom = 2.0 * (fga + 0.44 * fta)
            ts_pct = (pts_pg / denom) if denom > 0 else 0.0
        if ast_pct == 0.0:
            ast_pct = (ast_pg / max(1.0, mpg)) * 100.0
        ast_to = ast_pg / max(1.0, tov_pg)
        insufficient = gp < 10 or mpg < 15
        return {
            "PLAYER_NAME": base.get("PLAYER_NAME", ""),
            "GP": gp,
            "MIN": mpg,
            "PTS": pts_pg,
            "TS_PCT": ts_pct,
            "AST_PCT": ast_pct,
            "AST_TO": ast_to,
            "REB_PCT": reb_pct if reb_pct > 0 else reb_pg / max(1.0, gp),
            "THREE_PCT": fg3_pct,
            "THREE_PM": fg3m_pg,
            "STL_PCT": stl_pct,
            "BLK_PCT": blk_pct,
            "INSUFFICIENT": insufficient
        }

    def get_mock_data(self, player_name: str) -> Dict:
        return {
            "PLAYER_NAME": player_name,
            "GP": 60.0,
            "MIN": 32.0,
            "PTS": 25.0,
            "TS_PCT": 0.60,
            "AST_PCT": 0.25,
            "AST_TO": 2.2,
            "REB_PCT": 0.12,
            "THREE_PCT": 0.37,
            "THREE_PM": 2.8,
            "STL_PCT": 2.0,
            "BLK_PCT": 1.2,
            "INSUFFICIENT": False
        }

@st.cache_data(ttl=3600)
def fetch_data_pipeline(name: str) -> Dict:
    f = NBADataFetcher()
    pid = f.search_player(name)
    if not pid:
        return {"stats": f.get_mock_data(name), "source": "mock", "reason": "未找到匹配球员（请使用英文全名或更精确的拼写）"}
    try:
        raw = f.fetch_season_stats(pid)
        clean = f._clean_data(raw)
        return {"stats": clean, "source": "real"}
    except Exception as e:
        return {"stats": f.get_mock_data(name), "source": "mock", "reason": f"数据源错误：{e}"}