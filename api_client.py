"""
api_client.py
=============
Cliente para football-data.org
- Descarga partidos y standings del Mundial
- Guarda caché local en /data para no gastar llamadas
- API gratuita: 10 llamadas/minuto, necesitas token en x-auth-token
"""

import requests
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "https://api.football-data.org/v4"
CACHE_DIR = Path(__file__).parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

# ── Pon aquí tu token de football-data.org (registro gratuito)
# https://www.football-data.org/client/register
API_TOKEN = os.getenv("FOOTBALL_API_TOKEN", "TU_TOKEN_AQUI")

HEADERS = {
    "X-Auth-Token": API_TOKEN,
    "Accept": "application/json",
}

# Códigos de competición
COMPETITIONS = {
    "mundial_2026": "WC",        # World Cup
    "champions":    "CL",
    "premier":      "PL",
    "laliga":       "PD",
    "bundesliga":   "BL1",
    "ligue1":       "FL1",
    "serie_a":      "SA",
}


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def _is_fresh(path: Path, max_age_hours: int = 6) -> bool:
    """Devuelve True si el caché tiene menos de max_age_hours horas."""
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=max_age_hours)


def _get(endpoint: str, cache_key: str, max_age_hours: int = 6) -> dict:
    """GET con caché local. Si el caché es fresco lo usa sin llamar la API."""
    cache = _cache_path(cache_key)

    if _is_fresh(cache, max_age_hours):
        print(f"  [caché] {cache_key}")
        return json.loads(cache.read_text())

    if API_TOKEN == "TU_TOKEN_AQUI":
        raise ValueError(
            "\n\n  ⚠ Necesitas un token gratuito de football-data.org\n"
            "  1. Regístrate en https://www.football-data.org/client/register\n"
            "  2. Copia tu token y ponlo en la variable de entorno:\n"
            "     export FOOTBALL_API_TOKEN='tu_token'\n"
            "  3. O edita api_client.py línea 19 directamente.\n"
        )

    url = f"{BASE_URL}{endpoint}"
    print(f"  [API]   GET {url}")
    resp = requests.get(url, headers=HEADERS, timeout=10)

    if resp.status_code == 429:
        print("  Rate limit alcanzado, esperando 60s…")
        time.sleep(61)
        resp = requests.get(url, headers=HEADERS, timeout=10)

    resp.raise_for_status()
    data = resp.json()
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data


# ──────────────────────────────────────────────
#  Funciones públicas
# ──────────────────────────────────────────────

def get_matches(competition: str = "WC", season: int = 2026) -> list[dict]:
    """
    Devuelve lista de partidos de la competición.
    competition: código de la API  (WC, CL, PL…)
    season:      año de inicio de la temporada
    """
    data = _get(
        f"/competitions/{competition}/matches?season={season}",
        cache_key=f"matches_{competition}_{season}",
        max_age_hours=2,
    )
    return data.get("matches", [])


def get_standings(competition: str = "WC", season: int = 2026) -> list[dict]:
    """Devuelve la tabla de posiciones de la fase de grupos."""
    data = _get(
        f"/competitions/{competition}/standings?season={season}",
        cache_key=f"standings_{competition}_{season}",
        max_age_hours=6,
    )
    standings = []
    for group in data.get("standings", []):
        for row in group.get("table", []):
            standings.append({
                "grupo":      group.get("group", ""),
                "equipo":     row["team"]["name"],
                "team_id":    row["team"]["id"],
                "pj":         row["playedGames"],
                "g":          row["won"],
                "e":          row["draw"],
                "p":          row["lost"],
                "gf":         row["goalsFor"],
                "gc":         row["goalsAgainst"],
                "pts":        row["points"],
            })
    return standings


def get_team_matches(team_id: int, competition: str = "WC", season: int = 2026) -> list[dict]:
    """Partidos de un equipo específico en la competición."""
    all_matches = get_matches(competition, season)
    return [
        m for m in all_matches
        if m["homeTeam"]["id"] == team_id or m["awayTeam"]["id"] == team_id
    ]


def list_teams(competition: str = "WC", season: int = 2026) -> list[dict]:
    """Lista de equipos participantes con sus IDs."""
    data = _get(
        f"/competitions/{competition}/teams?season={season}",
        cache_key=f"teams_{competition}_{season}",
        max_age_hours=24,
    )
    return [
        {"id": t["id"], "nombre": t["name"], "codigo": t.get("tla", "")}
        for t in data.get("teams", [])
    ]
