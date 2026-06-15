import requests, json
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "data"
CACHE_DIR.mkdir(exist_ok=True)

SOURCES = {
    "2026": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json",
    "2022": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2022/worldcup.json",
    "2018": "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2018/worldcup.json",
}

NAME_MAP = {
    "Mexico":"México","South Africa":"Sudáfrica","South Korea":"Corea","Czech Republic":"Rep. Checa",
    "Canada":"Canadá","Bosnia & Herzegovina":"Bosnia","Brazil":"Brasil","Morocco":"Marruecos",
    "Haiti":"Haití","Scotland":"Escocia","USA":"EEUU","Paraguay":"Paraguay","Australia":"Australia",
    "Turkey":"Turquía","Germany":"Alemania","Ecuador":"Ecuador","Netherlands":"Holanda",
    "Japan":"Japón","Sweden":"Suecia","Tunisia":"Túnez","Belgium":"Bélgica","Egypt":"Egipto",
    "Colombia":"Colombia","Saudi Arabia":"Arabia S.","Spain":"España","Cape Verde":"Cabo Verde",
    "Cameroon":"Camerún","Denmark":"Dinamarca","France":"Francia","Senegal":"Senegal",
    "Norway":"Noruega","Iraq":"Irak","Argentina":"Argentina","Algeria":"Argelia",
    "Austria":"Austria","Jordan":"Jordania","Portugal":"Portugal","DR Congo":"RD Congo",
    "Uzbekistan":"Uzbekistán","England":"Inglaterra","Croatia":"Croacia","Panama":"Panamá",
    "Ghana":"Ghana","Uruguay":"Uruguay","Switzerland":"Suiza","Qatar":"Qatar",
    "Iran":"Irán","Wales":"Gales","Serbia":"Serbia","Poland":"Polonia","Russia":"Rusia",
    "Nigeria":"Nigeria","Ivory Coast":"Costa Marfil","New Zealand":"Nueva Zelanda",
}
ES_TO_EN = {v: k for k, v in NAME_MAP.items()}

def _load_tournament(year):
    cache = CACHE_DIR / f"wc{year}_matches.json"
    if cache.exists():
        return json.loads(cache.read_text())
    try:
        r = requests.get(SOURCES[year], timeout=8)
        r.raise_for_status()
        matches = [m for m in r.json().get("matches",[]) if m.get("score",{}).get("ft")]
        cache.write_text(json.dumps(matches, ensure_ascii=False))
        return matches
    except:
        return []

def get_team_matches(team_es, max_total=10):
    team_en = ES_TO_EN.get(team_es, team_es)
    all_matches = []
    for year in ["2026","2022","2018"]:
        for m in _load_tournament(year):
            t1, t2 = m["team1"], m["team2"]
            is_home = t1 == team_en or team_en.lower() in t1.lower()
            is_away = t2 == team_en or team_en.lower() in t2.lower()
            if not (is_home or is_away):
                continue
            ft = m["score"]["ft"]
            gf = ft[0] if is_home else ft[1]
            gc = ft[1] if is_home else ft[0]
            rival = NAME_MAP.get(t2 if is_home else t1, t2 if is_home else t1)
            res = "V" if gf > gc else ("E" if gf == gc else "D")
            goles = m.get("goals1" if is_home else "goals2", [])
            scorers = ", ".join(f"{g['name']} ({g['minute']}')" for g in goles if "name" in g)
            all_matches.append({
                "ano": year, "fecha": m["date"],
                "condicion": "Local" if is_home else "Visitante",
                "rival": rival, "gf": gf, "gc": gc,
                "resultado": res, "marcador": f"{gf}-{gc}",
                "goleadores": scorers if scorers else "—",
                "ronda": m.get("round", "Grupo"),
            })
    all_matches.sort(key=lambda x: x["fecha"], reverse=True)
    return all_matches[:max_total]

def compute_stats(matches):
    if not matches:
        return {}
    n = len(matches)
    gf = sum(m["gf"] for m in matches)
    gc = sum(m["gc"] for m in matches)
    v = sum(1 for m in matches if m["resultado"] == "V")
    e = sum(1 for m in matches if m["resultado"] == "E")
    d = sum(1 for m in matches if m["resultado"] == "D")
    return {
        "pj": n, "victorias": v, "empates": e, "derrotas": d,
        "goles_favor": gf, "goles_contra": gc,
        "promedio_gf": round(gf/n, 2),
        "promedio_gc": round(gc/n, 2),
        "promedio_total": round((gf+gc)/n, 2),
        "clean_sheets": sum(1 for m in matches if m["gc"] == 0),
        "forma": "".join(m["resultado"] for m in reversed(matches[-5:])),
    }

def get_full_report(team_es):
    all_10 = get_team_matches(team_es, 10)
    local_all = [m for m in get_team_matches(team_es, 30) if m["condicion"] == "Local"]
    return {
        "equipo": team_es,
        "ultimos_10": all_10,
        "stats_10": compute_stats(all_10),
        "local_5": local_all[:5],
        "stats_local": compute_stats(local_all[:5]),
    }
