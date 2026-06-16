"""
api_football.py
===============
Cliente para API-Football (api-sports.io)
Plan gratuito: 100 requests/día

Endpoints usados:
- /teams?name=X           → buscar equipo por nombre
- /fixtures?team=X&last=10 → últimos 10 partidos
- /fixtures?team=X&last=5&venue=home → últimos 5 como local
- /fixtures?team=X&last=5&venue=away → últimos 5 como visitante
"""

import requests
import json
from pathlib import Path
from datetime import datetime, date

CACHE_DIR = Path(__file__).parent / "data" / "api_football_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://v3.football.api-sports.io"

# Mapa de nombres en español a nombres en inglés para buscar en API
TEAM_SEARCH = {
    "México":       "Mexico",
    "Sudáfrica":    "South Africa",
    "Corea":        "South Korea",
    "Rep. Checa":   "Czech Republic",
    "Canadá":       "Canada",
    "Bosnia":       "Bosnia",
    "Brasil":       "Brazil",
    "Marruecos":    "Morocco",
    "Haití":        "Haiti",
    "Escocia":      "Scotland",
    "EEUU":         "USA",
    "Turquía":      "Turkey",
    "Alemania":     "Germany",
    "Holanda":      "Netherlands",
    "Japón":        "Japan",
    "Suecia":       "Sweden",
    "Túnez":        "Tunisia",
    "Bélgica":      "Belgium",
    "Egipto":       "Egypt",
    "Colombia":     "Colombia",
    "Arabia S.":    "Saudi Arabia",
    "España":       "Spain",
    "Cabo Verde":   "Cape Verde",
    "Camerún":      "Cameroon",
    "Dinamarca":    "Denmark",
    "Francia":      "France",
    "Senegal":      "Senegal",
    "Noruega":      "Norway",
    "Irak":         "Iraq",
    "Argentina":    "Argentina",
    "Argelia":      "Algeria",
    "Austria":      "Austria",
    "Jordania":     "Jordan",
    "Portugal":     "Portugal",
    "RD Congo":     "DR Congo",
    "Uzbekistán":   "Uzbekistan",
    "Inglaterra":   "England",
    "Croacia":      "Croatia",
    "Panamá":       "Panama",
    "Ghana":        "Ghana",
    "Uruguay":      "Uruguay",
    "Suiza":        "Switzerland",
    "Qatar":        "Qatar",
    "Irán":         "Iran",
    "Nueva Zelanda":"New Zealand",
    "Curazao":      "Curacao",
    "Ecuador":      "Ecuador",
    "Costa Marfil": "Ivory Coast",
    "Paraguay":     "Paraguay",
    "Australia":    "Australia",
}


class APIFootball:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {"x-apisports-key": api_key}

    def _get(self, endpoint: str, params: dict) -> dict:
        """Make API request with caching."""
        cache_key = endpoint.replace("/","_") + "_" + "_".join(f"{k}{v}" for k,v in sorted(params.items()))
        cache_file = CACHE_DIR / f"{cache_key}.json"

        # Cache válido por 6 horas
        if cache_file.exists():
            age = datetime.now().timestamp() - cache_file.stat().st_mtime
            if age < 21600:  # 6 horas
                return json.loads(cache_file.read_text())

        url = f"{BASE_URL}/{endpoint}"
        r = requests.get(url, headers=self.headers, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        cache_file.write_text(json.dumps(data, ensure_ascii=False))
        return data

    def get_team_id(self, team_es: str) -> int | None:
        """Busca el ID del equipo en la API."""
        team_en = TEAM_SEARCH.get(team_es, team_es)
        cache_file = CACHE_DIR / f"team_id_{team_en.replace(' ','_')}.json"

        if cache_file.exists():
            return json.loads(cache_file.read_text()).get("id")

        data = self._get("teams", {"name": team_en, "type": "National"})
        teams = data.get("response", [])
        if teams:
            team_id = teams[0]["team"]["id"]
            cache_file.write_text(json.dumps({"id": team_id, "name": team_en}))
            return team_id
        return None

    def get_last_matches(self, team_es: str, n: int = 10,
                         venue: str = None) -> list[dict]:
        """
        Jala los últimos N partidos del equipo.
        venue: None (todos), 'home', 'away'
        """
        team_id = self.get_team_id(team_es)
        if not team_id:
            return []

        params = {"team": team_id, "last": n, "status": "FT"}
        if venue:
            params["venue"] = venue

        data = self._get("fixtures", params)
        fixtures = data.get("response", [])

        matches = []
        for f in fixtures:
            teams = f.get("teams", {})
            goals = f.get("goals", {})
            fixture = f.get("fixture", {})
            league = f.get("league", {})

            home_id = teams.get("home", {}).get("id")
            is_home = home_id == team_id

            home_name = teams.get("home", {}).get("name", "")
            away_name = teams.get("away", {}).get("name", "")

            gf_h = goals.get("home", 0) or 0
            gf_a = goals.get("away", 0) or 0

            gf = gf_h if is_home else gf_a
            gc = gf_a if is_home else gf_h
            rival = away_name if is_home else home_name

            if gf > gc:    res = "V"
            elif gf < gc:  res = "D"
            else:          res = "E"

            matches.append({
                "fecha":     fixture.get("date","")[:10],
                "condicion": "Local" if is_home else "Visitante",
                "rival":     rival,
                "gf":        gf,
                "gc":        gc,
                "marcador":  f"{gf}-{gc}",
                "resultado": res,
                "liga":      league.get("name",""),
                "temporada": league.get("season",""),
                "goleadores": "—",  # requiere endpoint adicional
            })

        return sorted(matches, key=lambda x: x["fecha"], reverse=True)

    def get_full_report(self, team_es: str) -> dict:
        """Reporte completo: últimos 10, 5 local, 5 visitante."""
        from team_history import compute_stats

        todos   = self.get_last_matches(team_es, 10)
        locales = self.get_last_matches(team_es, 5, venue="home")
        visitas = self.get_last_matches(team_es, 5, venue="away")

        return {
            "equipo":      team_es,
            "ultimos_10":  todos,
            "stats_10":    compute_stats(todos),
            "local_5":     locales,
            "stats_local": compute_stats(locales),
            "visit_5":     visitas,
            "stats_visit": compute_stats(visitas),
            "fuente":      "API-Football",
        }
