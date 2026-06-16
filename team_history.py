"""
team_history.py
===============
Extrae historial real de partidos por equipo desde:
- Mundial 2026 (partidos jugados)
- Mundial 2022
- Mundial 2018

Calcula estadísticas de últimos 5 como local y últimos 10 en general.
"""

import requests
import json
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path(__file__).parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

SOURCES = {
    "2026": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json",
    "2022": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2022/worldcup.json",
    "2018": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2018/worldcup.json",
}

# Nombres en inglés (openfootball) → español (nuestro fixture)
NAME_MAP = {
    "Mexico": "México", "South Africa": "Sudáfrica", "South Korea": "Corea",
    "Czech Republic": "Rep. Checa", "Canada": "Canadá",
    "Bosnia & Herzegovina": "Bosnia", "Brazil": "Brasil",
    "Morocco": "Marruecos", "Haiti": "Haití", "Scotland": "Escocia",
    "USA": "EEUU", "Paraguay": "Paraguay", "Australia": "Australia",
    "Turkey": "Turquía", "Germany": "Alemania", "Ecuador": "Ecuador",
    "Netherlands": "Holanda", "Japan": "Japón", "Sweden": "Suecia",
    "Tunisia": "Túnez", "Belgium": "Bélgica", "Egypt": "Egipto",
    "Colombia": "Colombia", "Saudi Arabia": "Arabia S.", "Spain": "España",
    "Cape Verde": "Cabo Verde", "Cameroon": "Camerún", "Denmark": "Dinamarca",
    "France": "Francia", "Senegal": "Senegal", "Norway": "Noruega",
    "Iraq": "Irak", "Argentina": "Argentina", "Algeria": "Argelia",
    "Austria": "Austria", "Jordan": "Jordania", "Portugal": "Portugal",
    "DR Congo": "RD Congo", "Uzbekistan": "Uzbekistán", "England": "Inglaterra",
    "Croatia": "Croacia", "Panama": "Panamá", "Ghana": "Ghana",
    "Uruguay": "Uruguay", "Switzerland": "Suiza", "Qatar": "Qatar",
    "Iran": "Irán", "Wales": "Gales", "Serbia": "Serbia",
    "Poland": "Polonia", "Russia": "Rusia", "Nigeria": "Nigeria",
    "Ivory Coast": "Costa Marfil", "Curaçao": "Curazao",
    "New Zealand": "Nueva Zelanda",
}
# Reverse map
ES_TO_EN = {v: k for k, v in NAME_MAP.items()}


def _load_tournament(year: str) -> list[dict]:
    """Carga y cachea partidos de un torneo."""
    cache = CACHE_DIR / f"wc{year}_matches.json"
    if cache.exists():
        return json.loads(cache.read_text())

    url = SOURCES[year]
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        data = r.json()
        matches = [m for m in data.get("matches", []) if m.get("score", {}).get("ft")]
        cache.write_text(json.dumps(matches, ensure_ascii=False))
        return matches
    except Exception as e:
        print(f"  Error cargando {year}: {e}")
        return []


def _normalize(name: str) -> str:
    """Normaliza nombre al español."""
    return NAME_MAP.get(name, name)


def get_team_matches(team_es: str, max_total: int = 10) -> list[dict]:
    """
    Devuelve últimos N partidos del equipo (en todos los mundiales disponibles),
    del más reciente al más antiguo.
    team_es: nombre en español (ej. "México", "Brasil")
    """
    team_en = ES_TO_EN.get(team_es, team_es)
    all_matches = []

    for year in ["2026", "2022", "2018"]:
        matches = _load_tournament(year)
        for m in matches:
            t1 = m["team1"]
            t2 = m["team2"]
            is_home = t1 == team_en
            is_away = t2 == team_en

            if not (is_home or is_away):
                # Try partial match
                is_home = team_en.lower() in t1.lower() or t1.lower() in team_en.lower()
                is_away = team_en.lower() in t2.lower() or t2.lower() in team_en.lower()
                if not (is_home or is_away):
                    continue

            ft    = m["score"]["ft"]
            gf    = ft[0] if is_home else ft[1]
            gc    = ft[1] if is_home else ft[0]
            rival = _normalize(t2 if is_home else t1)

            if gf > gc:    res = "V"
            elif gf == gc: res = "E"
            else:          res = "D"

            goles_a = m.get("goals1" if is_home else "goals2", [])
            scorers = [f"{g['name']} ({g['minute']}')" for g in goles_a if 'name' in g]

            all_matches.append({
                "año":       year,
                "fecha":     m["date"],
                "condicion": "Local" if is_home else "Visitante",
                "rival":     rival,
                "gf":        gf,
                "gc":        gc,
                "resultado": res,
                "marcador":  f"{gf}-{gc}",
                "goleadores": ", ".join(scorers) if scorers else "—",
                "ronda":     m.get("round", "Grupo"),
            })

    # Ordenar por fecha descendente
    all_matches.sort(key=lambda x: x["fecha"], reverse=True)
    return all_matches[:max_total]


def compute_stats(matches: list[dict]) -> dict:
    """Calcula estadísticas de una lista de partidos."""
    if not matches:
        return {}

    n   = len(matches)
    gf  = sum(m["gf"] for m in matches)
    gc  = sum(m["gc"] for m in matches)
    v   = sum(1 for m in matches if m["resultado"] == "V")
    e   = sum(1 for m in matches if m["resultado"] == "E")
    d   = sum(1 for m in matches if m["resultado"] == "D")
    cs  = sum(1 for m in matches if m["gc"] == 0)
    bt  = sum(1 for m in matches if m["gf"] > 0 and m["gc"] > 0)

    return {
        "pj":                n,
        "victorias":         v,
        "empates":           e,
        "derrotas":          d,
        "goles_favor":       gf,
        "goles_contra":      gc,
        "promedio_gf":       round(gf / n, 2),
        "promedio_gc":       round(gc / n, 2),
        "promedio_total":    round((gf + gc) / n, 2),
        "clean_sheets":      cs,
        "btts":              bt,
        "forma":             "".join(m["resultado"] for m in reversed(matches[-5:])),
    }


def get_full_report(team_es: str) -> dict:
    """
    Reporte completo:
    - Últimos 10 partidos generales
    - Últimos 5 como local
    - Estadísticas de cada grupo
    """
    all_10   = get_team_matches(team_es, max_total=10)
    local_5  = [m for m in get_team_matches(team_es, max_total=30)
                if m["condicion"] == "Local"][:5]

    return {
        "equipo":         team_es,
        "ultimos_10":     all_10,
        "stats_10":       compute_stats(all_10),
        "local_5":        local_5,
        "stats_local":    compute_stats(local_5),
    }


if __name__ == "__main__":
    from tabulate import tabulate

    equipos = ["México", "Brasil", "Argentina", "España", "Francia"]

    for eq in equipos:
        rep = get_full_report(eq)
        s10 = rep["stats_10"]
        sl  = rep["stats_local"]

        print(f"\n{'='*60}")
        print(f"  {eq.upper()}")
        print(f"{'='*60}")

        if rep["ultimos_10"]:
            print(f"\n  Últimos {len(rep['ultimos_10'])} partidos:")
            rows = [[m["año"], m["fecha"], m["condicion"], m["rival"],
                     m["marcador"], m["resultado"], m["goleadores"][:30]]
                    for m in rep["ultimos_10"]]
            print(tabulate(rows,
                headers=["Año","Fecha","Cond.","Rival","Marcador","Res.","Goleadores"],
                tablefmt="simple"))

            print(f"\n  Estadísticas (últimos {s10['pj']} partidos):")
            print(f"    V/E/D: {s10['victorias']}/{s10['empates']}/{s10['derrotas']}")
            print(f"    Goles a favor:   {s10['goles_favor']} (prom {s10['promedio_gf']})")
            print(f"    Goles en contra: {s10['goles_contra']} (prom {s10['promedio_gc']})")
            print(f"    Promedio total:  {s10['promedio_total']} goles/partido")
            print(f"    Clean sheets:    {s10['clean_sheets']}")
            print(f"    Forma reciente:  {s10['forma']}")

        if rep["local_5"]:
            print(f"\n  Como local (últimos {len(rep['local_5'])} partidos):")
            rows_l = [[m["año"], m["fecha"], m["rival"],
                       m["marcador"], m["resultado"]]
                      for m in rep["local_5"]]
            print(tabulate(rows_l,
                headers=["Año","Fecha","Rival","Marcador","Res."],
                tablefmt="simple"))
            print(f"    Goles a favor:   {sl['goles_favor']} (prom {sl['promedio_gf']})")
            print(f"    Goles en contra: {sl['goles_contra']} (prom {sl['promedio_gc']})")


# ─────────────────────────────────────────────────────────────
#  TENDENCIAS Y RACHAS (estilo Betmines)
# ─────────────────────────────────────────────────────────────

def get_trends(matches: list[dict]) -> dict:
    """
    Calcula tendencias estadísticas de una lista de partidos.
    Similar al análisis de Betmines.
    """
    if not matches:
        return {}

    n = len(matches)

    # ── Racha actual (desde el más reciente)
    tipo_racha = matches[0]["resultado"]
    racha_n = 0
    for m in matches:
        if m["resultado"] == tipo_racha:
            racha_n += 1
        else:
            break

    # ── Sin perder / sin ganar
    sin_perder = 0
    for m in matches:
        if m["resultado"] != "D":
            sin_perder += 1
        else:
            break

    sin_ganar = 0
    for m in matches:
        if m["resultado"] != "V":
            sin_ganar += 1
        else:
            break

    # ── % mercados
    over05  = sum(1 for m in matches if m["gf"]+m["gc"] > 0.5)
    over15  = sum(1 for m in matches if m["gf"]+m["gc"] > 1.5)
    over25  = sum(1 for m in matches if m["gf"]+m["gc"] > 2.5)
    over35  = sum(1 for m in matches if m["gf"]+m["gc"] > 3.5)
    btts    = sum(1 for m in matches if m["gf"] > 0 and m["gc"] > 0)
    cs      = sum(1 for m in matches if m["gc"] == 0)
    scored  = sum(1 for m in matches if m["gf"] > 0)
    wins    = sum(1 for m in matches if m["resultado"] == "V")
    draws   = sum(1 for m in matches if m["resultado"] == "E")
    losses  = sum(1 for m in matches if m["resultado"] == "D")

    # ── Primeros 15 min (no tenemos datos granulares, lo omitimos)
    # ── Goles promedio por partido
    gf_total = sum(m["gf"] for m in matches)
    gc_total = sum(m["gc"] for m in matches)

    return {
        # Rachas
        "racha_tipo":       tipo_racha,
        "racha_n":          racha_n,
        "sin_perder":       sin_perder,
        "sin_ganar":        sin_ganar,
        # Resultados
        "win_%":            round(wins/n*100),
        "draw_%":           round(draws/n*100),
        "loss_%":           round(losses/n*100),
        # Goles
        "over_0.5_%":       round(over05/n*100),
        "over_1.5_%":       round(over15/n*100),
        "over_2.5_%":       round(over25/n*100),
        "over_3.5_%":       round(over35/n*100),
        "btts_%":           round(btts/n*100),
        "cs_%":             round(cs/n*100),
        "scored_%":         round(scored/n*100),
        "avg_gf":           round(gf_total/n, 2),
        "avg_gc":           round(gc_total/n, 2),
        "avg_total":        round((gf_total+gc_total)/n, 2),
        "partidos":         n,
    }


def get_suggestions(team: str, trends: dict, rival_trends: dict = None) -> list[dict]:
    """
    Genera sugerencias automáticas de apuesta basadas en tendencias.
    Devuelve lista de dicts con: mercado, descripcion, fuerza (1-3), tipo (positivo/negativo)
    """
    sugerencias = []
    n = trends.get("partidos", 0)
    if n == 0:
        return []

    mapa_racha = {"V": "victorias", "E": "empates", "D": "derrotas"}

    # ── Rachas
    if trends["racha_n"] >= 4:
        sugerencias.append({
            "mercado": "Forma",
            "desc": f"🔥 Racha de {trends['racha_n']} {mapa_racha.get(trends['racha_tipo'],'?')} consecutivas",
            "fuerza": 3, "tipo": "positivo" if trends["racha_tipo"] == "V" else "neutro"
        })
    elif trends["racha_n"] >= 2:
        sugerencias.append({
            "mercado": "Forma",
            "desc": f"📈 {trends['racha_n']} {mapa_racha.get(trends['racha_tipo'],'?')} seguidas",
            "fuerza": 2, "tipo": "positivo" if trends["racha_tipo"] == "V" else "neutro"
        })

    if trends["sin_perder"] >= 4:
        sugerencias.append({
            "mercado": "Invicto",
            "desc": f"🛡️ {trends['sin_perder']} partidos sin perder",
            "fuerza": 3, "tipo": "positivo"
        })

    # ── Over/Under
    if trends["over_2.5_%"] >= 70:
        sugerencias.append({
            "mercado": "Over 2.5",
            "desc": f"⚽ Over 2.5 en {trends['over_2.5_%']}% de sus últimos {n} partidos",
            "fuerza": 3, "tipo": "positivo"
        })
    elif trends["over_2.5_%"] >= 55:
        sugerencias.append({
            "mercado": "Over 2.5",
            "desc": f"⚽ Over 2.5 en {trends['over_2.5_%']}% de sus últimos {n} partidos",
            "fuerza": 2, "tipo": "positivo"
        })

    if trends["over_2.5_%"] <= 30:
        sugerencias.append({
            "mercado": "Under 2.5",
            "desc": f"🔒 Under 2.5 en {100-trends['over_2.5_%']}% de sus últimos {n} partidos",
            "fuerza": 3, "tipo": "positivo"
        })

    if trends["over_1.5_%"] >= 80:
        sugerencias.append({
            "mercado": "Over 1.5",
            "desc": f"⚽ Over 1.5 en {trends['over_1.5_%']}% de sus últimos {n} partidos",
            "fuerza": 3, "tipo": "positivo"
        })

    # ── BTTS
    if trends["btts_%"] >= 65:
        sugerencias.append({
            "mercado": "BTTS Sí",
            "desc": f"🎯 Ambos anotan en {trends['btts_%']}% de sus últimos {n} partidos",
            "fuerza": 3, "tipo": "positivo"
        })
    elif trends["btts_%"] >= 50:
        sugerencias.append({
            "mercado": "BTTS Sí",
            "desc": f"🎯 Ambos anotan en {trends['btts_%']}% de sus últimos {n} partidos",
            "fuerza": 2, "tipo": "positivo"
        })

    if trends["btts_%"] <= 30:
        sugerencias.append({
            "mercado": "BTTS No",
            "desc": f"🔒 BTTS No en {100-trends['btts_%']}% de sus últimos {n} partidos",
            "fuerza": 3, "tipo": "positivo"
        })

    # ── Clean sheet
    if trends["cs_%"] >= 50:
        sugerencias.append({
            "mercado": "Clean Sheet",
            "desc": f"🧤 Portería a cero en {trends['cs_%']}% de sus últimos {n} partidos",
            "fuerza": 2, "tipo": "positivo"
        })

    # ── Siempre marca
    if trends["scored_%"] >= 80:
        sugerencias.append({
            "mercado": "Marca",
            "desc": f"⚡ Ha marcado en {trends['scored_%']}% de sus últimos {n} partidos",
            "fuerza": 2, "tipo": "positivo"
        })

    # ── Goles promedio
    if trends["avg_total"] >= 3.0:
        sugerencias.append({
            "mercado": "Goles",
            "desc": f"📊 Promedio de {trends['avg_total']} goles/partido en sus últimos {n}",
            "fuerza": 2, "tipo": "positivo"
        })

    return sorted(sugerencias, key=lambda x: x["fuerza"], reverse=True)


def get_match_report(home_es: str, away_es: str) -> dict:
    """
    Reporte completo de un partido con tendencias de ambos equipos
    y sugerencias combinadas (estilo Betmines).
    """
    home_all    = get_team_matches(home_es, 10)
    home_local  = [m for m in get_team_matches(home_es, 30) if m["condicion"] == "Local"][:5]
    away_all    = get_team_matches(away_es, 10)
    away_visit  = [m for m in get_team_matches(away_es, 30) if m["condicion"] == "Visitante"][:5]

    home_trends = get_trends(home_all)
    home_local_trends = get_trends(home_local)
    away_trends = get_trends(away_all)
    away_visit_trends = get_trends(away_visit)

    home_suggestions = get_suggestions(home_es, home_trends, away_trends)
    away_suggestions = get_suggestions(away_es, away_trends, home_trends)

    # Sugerencias combinadas del partido
    match_suggestions = []

    # Over/Under combinado
    avg_total = round((home_trends.get("avg_total", 0) + away_trends.get("avg_total", 0)) / 2, 2)
    over_pct  = round((home_trends.get("over_2.5_%", 0) + away_trends.get("over_2.5_%", 0)) / 2)
    btts_pct  = round((home_trends.get("btts_%", 0) + away_trends.get("btts_%", 0)) / 2)

    if over_pct >= 60:
        match_suggestions.append({
            "mercado": "Over 2.5",
            "desc": f"⚽ Over 2.5 — promedio combinado: {over_pct}% entre ambos equipos",
            "fuerza": 3 if over_pct >= 70 else 2
        })
    if over_pct <= 35:
        match_suggestions.append({
            "mercado": "Under 2.5",
            "desc": f"🔒 Under 2.5 — solo {over_pct}% Over 2.5 promedio entre ambos",
            "fuerza": 3 if over_pct <= 25 else 2
        })
    if btts_pct >= 60:
        match_suggestions.append({
            "mercado": "BTTS Sí",
            "desc": f"🎯 BTTS Sí — promedio combinado: {btts_pct}% entre ambos equipos",
            "fuerza": 3 if btts_pct >= 70 else 2
        })

    return {
        "home":               home_es,
        "away":               away_es,
        "home_all":           home_all,
        "home_local":         home_local,
        "away_all":           away_all,
        "away_visit":         away_visit,
        "home_trends":        home_trends,
        "home_local_trends":  home_local_trends,
        "away_trends":        away_trends,
        "away_visit_trends":  away_visit_trends,
        "home_suggestions":   home_suggestions,
        "away_suggestions":   away_suggestions,
        "match_suggestions":  match_suggestions,
        "avg_total_goles":    avg_total,
    }

EXTRA_SOURCES = {
    "euro_2024": "https://raw.githubusercontent.com/openfootball/euro.json/master/2024/euro.json",
    "wc_2022":   "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2022/worldcup.json",
    "wc_2018":   "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2018/worldcup.json",
    "wc_2026":   "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json",
}

def _load_extra(key):
    cache = CACHE_DIR / f"{key}_matches.json"
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        r = requests.get(EXTRA_SOURCES[key], timeout=8)
        r.raise_for_status()
        ms = [m for m in r.json().get("matches",[]) if m.get("score",{}).get("ft")]
        cache.write_text(json.dumps(ms, ensure_ascii=False))
        return ms
    except: return []

def get_h2h(team1_es, team2_es, max_results=10):
    t1_en = ES_TO_EN.get(team1_es, team1_es)
    t2_en = ES_TO_EN.get(team2_es, team2_es)
    h2h = []
    for src in EXTRA_SOURCES:
        torneo = src.replace("_"," ").upper()
        for m in _load_extra(src):
            mt1, mt2 = m.get("team1",""), m.get("team2","")
            fwd = (t1_en.lower() in mt1.lower() or mt1.lower() in t1_en.lower()) and (t2_en.lower() in mt2.lower() or mt2.lower() in t2_en.lower())
            rev = (t2_en.lower() in mt1.lower() or mt1.lower() in t2_en.lower()) and (t1_en.lower() in mt2.lower() or mt2.lower() in t1_en.lower())
            if not (fwd or rev): continue
            ft = m.get("score",{}).get("ft",[0,0])
            gf,gc = (ft[0],ft[1]) if fwd else (ft[1],ft[0])
            res = "V" if gf>gc else ("D" if gf<gc else "E")
            ganador = team1_es if res=="V" else (team2_es if res=="D" else "Empate")
            h2h.append({"fecha":m.get("date",""),"torneo":torneo,"marcador":f"{gf}-{gc}","gf":gf,"gc":gc,"resultado":res,"ganador":ganador,"ronda":m.get("round",m.get("group","Grupo"))})
    h2h.sort(key=lambda x: x["fecha"], reverse=True)
    h2h = h2h[:max_results]
    n = len(h2h)
    if n == 0: return {"partidos":[],"stats":{},"team1":team1_es,"team2":team2_es}
    v1=sum(1 for m in h2h if m["resultado"]=="V")
    e=sum(1 for m in h2h if m["resultado"]=="E")
    d1=sum(1 for m in h2h if m["resultado"]=="D")
    gft=sum(m["gf"] for m in h2h); gct=sum(m["gc"] for m in h2h)
    stats={f"{team1_es}_V":v1,"empates":e,f"{team2_es}_V":d1,"total":n,
           "avg_goles_t1":round(gft/n,2),"avg_goles_t2":round(gct/n,2),
           "avg_total":round((gft+gct)/n,2),
           "over_2.5_%":round(sum(1 for m in h2h if m["gf"]+m["gc"]>2.5)/n*100),
           "btts_%":round(sum(1 for m in h2h if m["gf"]>0 and m["gc"]>0)/n*100),
           "dominante":team1_es if v1>d1 else (team2_es if d1>v1 else "Equilibrado")}
    return {"partidos":h2h,"stats":stats,"team1":team1_es,"team2":team2_es}
