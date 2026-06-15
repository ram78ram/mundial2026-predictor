"""
monte_carlo.py
==============
Simulación Monte Carlo del Mundial 2026.
- Simula N veces el torneo completo (grupos + eliminatorias)
- Calcula probabilidades de: pasar grupos, llegar a cuartos, semis, final, ganar
- Integra forma reciente y ajuste por bajas
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from stats_engine import compute_lambdas, score_matrix, match_probabilities
from fixture import FIXTURE, TEAM_MAP
from predictor import DEMO_STATS


EN_TO_ES = {
    "Mexico": "México", "South Africa": "Sudáfrica", "South Korea": "Corea",
    "Czech Republic": "Rep. Checa", "Canada": "Canadá", "Bosnia & Herzegovina": "Bosnia",
    "Qatar": "Qatar", "Switzerland": "Suiza", "Brazil": "Brasil",
    "Morocco": "Marruecos", "Haiti": "Haití", "Scotland": "Escocia",
    "USA": "EEUU", "Paraguay": "Paraguay", "Australia": "Australia",
    "Turkey": "Turquía", "Germany": "Alemania", "Curacao": "Curazao",
    "Ivory Coast": "Costa Marfil", "Ecuador": "Ecuador",
    "Netherlands": "Holanda", "Japan": "Japón", "Sweden": "Suecia",
    "Tunisia": "Túnez", "Belgium": "Bélgica", "Egypt": "Egipto",
    "Colombia": "Colombia", "Saudi Arabia": "Arabia S.", "Spain": "España",
    "Cape Verde": "Cabo Verde", "Cameroon": "Camerún", "Denmark": "Dinamarca",
    "France": "Francia", "Senegal": "Senegal", "Norway": "Noruega",
    "Iraq": "Irak", "Argentina": "Argentina", "Algeria": "Argelia",
    "Austria": "Austria", "Jordan": "Jordania", "Portugal": "Portugal",
    "DR Congo": "RD Congo", "Uzbekistan": "Uzbekistán", "England": "Inglaterra",
    "Croatia": "Croacia", "Panama": "Panamá", "Ghana": "Ghana",
    "Uruguay": "Uruguay",
}

LEAGUE_AVG   = 1.35
HOME_ADV     = 1.02   # torneo neutral, ventaja mínima

# Grupos del Mundial 2026
GRUPOS = {
    "A": ["México",      "Sudáfrica",   "Corea",       "Rep. Checa"],
    "B": ["Canadá",      "Bosnia",      "Qatar",       "Suiza"],
    "C": ["Brasil",      "Marruecos",   "Haití",       "Escocia"],
    "D": ["EEUU",        "Paraguay",    "Australia",   "Turquía"],
    "E": ["Alemania",    "Curazao",     "Ecuador",     "Costa Marfil"],
    "F": ["Holanda",     "Japón",       "Suecia",      "Túnez"],
    "G": ["Bélgica",     "Egipto",      "Colombia",    "Arabia S."],
    "H": ["España",      "Cabo Verde",  "Camerún",     "Dinamarca"],
    "I": ["Francia",     "Senegal",     "Noruega",     "Irak"],
    "J": ["Argentina",   "Argelia",     "Austria",     "Jordania"],
    "K": ["Portugal",    "Colombia",    "Uzbekistán",  "RD Congo"],
    "L": ["Inglaterra",  "Croacia",     "Panamá",      "Ghana"],
}

# ─────────────────────────────────────────────────────────────
#  AJUSTE POR FORMA RECIENTE
# ─────────────────────────────────────────────────────────────

# Últimos 5 partidos oficiales antes del Mundial (W/D/L)
# Fuente: clasificatorias y amistosos previos al torneo
FORMA_RECIENTE = {
    "Brasil":      ["W","W","W","D","W"],
    "Argentina":   ["W","W","W","W","W"],
    "Francia":     ["W","W","D","W","W"],
    "España":      ["W","W","W","W","D"],
    "Alemania":    ["W","D","W","W","L"],
    "Portugal":    ["W","W","W","D","W"],
    "Holanda":     ["W","W","D","W","W"],
    "Inglaterra":  ["W","W","W","D","W"],
    "México":      ["W","W","D","W","W"],
    "EEUU":        ["W","W","W","W","D"],
    "Colombia":    ["W","D","W","W","D"],
    "Uruguay":     ["W","W","D","W","D"],
    "Marruecos":   ["W","W","W","D","W"],
    "Senegal":     ["W","D","W","W","D"],
    "Japón":       ["W","W","D","W","W"],
    "Corea":       ["W","D","W","D","W"],
    "Ecuador":     ["D","W","W","D","W"],
    "Canadá":      ["W","W","D","W","D"],
    "Australia":   ["D","W","W","D","W"],
    "Croacia":     ["W","D","W","W","D"],
    "Bélgica":     ["W","W","D","W","W"],
    "Suiza":       ["W","W","W","D","D"],
    "Dinamarca":   ["W","W","D","W","W"],
    "Noruega":     ["W","W","W","D","W"],
    "Turquía":     ["W","D","W","W","D"],
    "Suecia":      ["W","D","W","W","D"],
    "Austria":     ["W","W","D","W","D"],
}

def forma_factor(equipo: str) -> float:
    """
    Multiplica el ataque del equipo según su forma reciente.
    W=1.0, D=0.0, L=-1.0 con pesos recientes.
    Rango resultado: 0.88 a 1.12
    """
    forma = FORMA_RECIENTE.get(equipo, ["D","D","D","D","D"])
    pesos = [0.10, 0.15, 0.20, 0.25, 0.30]
    mapa  = {"W": 1.0, "D": 0.0, "L": -1.0}
    score = sum(mapa[r]*p for r, p in zip(forma[-5:], pesos))
    return round(1.0 + score * 0.12, 4)   # ±12% máximo


# ─────────────────────────────────────────────────────────────
#  SIMULACIÓN DE UN PARTIDO
# ─────────────────────────────────────────────────────────────

def simular_partido(home: str, away: str,
                    ajustes: dict | None = None,
                    usar_forma: bool = True) -> tuple[int, int]:
    """
    Simula un partido y devuelve (goles_local, goles_visitante).
    ajustes: {"México": {"ataque": 0.9}} para bajas o penalizaciones.
    """
    stats = {k: dict(v) for k, v in DEMO_STATS.items()}

    # Aplicar ajustes manuales (bajas)
    if ajustes:
        for equipo, mod in ajustes.items():
            if equipo in stats:
                for campo, val in mod.items():
                    stats[equipo][campo] *= val

    h = stats.get(home, {"ataque": 1.20, "defensa": 1.15})
    a = stats.get(away, {"ataque": 1.20, "defensa": 1.15})

    ff_h = forma_factor(home) if usar_forma else 1.0
    ff_a = forma_factor(away) if usar_forma else 1.0

    lh, la = compute_lambdas(
        h["ataque"] * ff_h, h["defensa"],
        a["ataque"] * ff_a, a["defensa"],
        LEAGUE_AVG, HOME_ADV,
    )

    gh = np.random.poisson(lh)
    ga = np.random.poisson(la)
    return int(gh), int(ga)


def simular_partido_eliminatorio(home: str, away: str,
                                  ajustes: dict | None = None) -> str:
    """Igual que simular_partido pero con penales en empate. Devuelve el ganador."""
    gh, ga = simular_partido(home, away, ajustes)
    if gh > ga:
        return home
    if ga > gh:
        return away
    # Penales: 50/50 ajustado levemente por fuerza relativa
    h_att = DEMO_STATS.get(home, {}).get("ataque", 1.2)
    a_att = DEMO_STATS.get(away, {}).get("ataque", 1.2)
    prob_h = h_att / (h_att + a_att)
    return home if np.random.random() < prob_h else away


# ─────────────────────────────────────────────────────────────
#  FASE DE GRUPOS
# ─────────────────────────────────────────────────────────────

def simular_grupo(equipos: list[str],
                  ajustes: dict | None = None) -> list[dict]:
    """
    Simula la fase de grupos round-robin (cada par juega 1 vez).
    Devuelve lista de dicts ordenados por pts, dif, gf.
    """
    tabla = {e: {"pj":0,"g":0,"e":0,"p":0,"gf":0,"gc":0,"pts":0} for e in equipos}

    for i, h in enumerate(equipos):
        for a in equipos[i+1:]:
            gh, ga = simular_partido(h, a, ajustes)
            tabla[h]["pj"] += 1; tabla[h]["gf"] += gh; tabla[h]["gc"] += ga
            tabla[a]["pj"] += 1; tabla[a]["gf"] += ga; tabla[a]["gc"] += gh
            if gh > ga:
                tabla[h]["g"] += 1; tabla[h]["pts"] += 3; tabla[a]["p"] += 1
            elif ga > gh:
                tabla[a]["g"] += 1; tabla[a]["pts"] += 3; tabla[h]["p"] += 1
            else:
                tabla[h]["e"] += 1; tabla[h]["pts"] += 1
                tabla[a]["e"] += 1; tabla[a]["pts"] += 1

    ranking = sorted(
        [{"equipo": e, **v, "dif": v["gf"]-v["gc"]} for e, v in tabla.items()],
        key=lambda x: (x["pts"], x["dif"], x["gf"]),
        reverse=True,
    )
    return ranking


# ─────────────────────────────────────────────────────────────
#  SIMULACIÓN COMPLETA DEL TORNEO
# ─────────────────────────────────────────────────────────────

def simular_torneo(ajustes: dict | None = None) -> dict[str, str]:
    """
    Simula un torneo completo.
    Devuelve dict equipo → mejor resultado: 'grupos'|'r32'|'r16'|'qf'|'sf'|'final'|'campeon'
    """
    resultados = {e: "grupos" for grupo in GRUPOS.values() for e in grupo}

    # ── Fase de grupos: top 2 clasifican + mejores 8 terceros
    clasificados_por_grupo = {}
    terceros = []

    for nombre_grupo, equipos in GRUPOS.items():
        tabla = simular_grupo(equipos, ajustes)
        clasificados_por_grupo[nombre_grupo] = tabla
        # Primero y segundo clasifican directamente
        for t in tabla[:2]:
            resultados[t["equipo"]] = "r32"
        # Tercero acumula para los 8 mejores terceros
        t3 = tabla[2]
        t3["grupo"] = nombre_grupo
        terceros.append(t3)

    # Los 8 mejores terceros también clasifican
    terceros_ord = sorted(terceros, key=lambda x: (x["pts"], x["dif"], x["gf"]), reverse=True)
    for t in terceros_ord[:8]:
        resultados[t["equipo"]] = "r32"

    # ── Construir bracket de 32 (simplificado: semillas por posición en grupo)
    bracket = []
    grupos_ord = list(GRUPOS.keys())
    for g in grupos_ord:
        tabla = clasificados_por_grupo[g]
        bracket.append(tabla[0]["equipo"])  # 1eros
    for g in grupos_ord:
        tabla = clasificados_por_grupo[g]
        bracket.append(tabla[1]["equipo"])  # 2dos

    # Agregar mejores terceros
    for t in terceros_ord[:8]:
        bracket.append(t["equipo"])

    # Asegurar exactamente 32 equipos
    bracket = list(dict.fromkeys(bracket))[:32]
    while len(bracket) < 32:
        bracket.append(bracket[-1])

    # ── Fase eliminatoria
    rondas = ["r16", "qf", "sf", "final", "campeon"]
    equipos_ronda = bracket[:]

    for ronda in rondas:
        siguientes = []
        for i in range(0, len(equipos_ronda), 2):
            if i+1 >= len(equipos_ronda):
                siguientes.append(equipos_ronda[i])
                resultados[equipos_ronda[i]] = ronda
                continue
            ganador = simular_partido_eliminatorio(
                equipos_ronda[i], equipos_ronda[i+1], ajustes)
            perdedor = equipos_ronda[i] if ganador == equipos_ronda[i+1] else equipos_ronda[i+1]
            resultados[perdedor] = ronda
            siguientes.append(ganador)
        equipos_ronda = siguientes
        if len(equipos_ronda) == 1:
            resultados[equipos_ronda[0]] = "campeon"
            break

    return resultados


# ─────────────────────────────────────────────────────────────
#  MONTECARLO PRINCIPAL
# ─────────────────────────────────────────────────────────────

RONDA_ORDEN = {"grupos": 0, "r32": 1, "r16": 2, "qf": 3, "sf": 4, "final": 5, "campeon": 6}

def correr_montecarlo(
    n_sims: int = 10_000,
    ajustes: dict | None = None,
    usar_forma: bool = True,
    seed: int | None = 42,
) -> pd.DataFrame:
    """
    Corre N simulaciones y devuelve DataFrame con probabilidades por equipo.

    Columnas: equipo, pasa_grupos%, r16%, qf%, sf%, final%, campeon%
    """
    if seed is not None:
        np.random.seed(seed)

    conteo: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    todos_equipos = [e for grupo in GRUPOS.values() for e in grupo]

    print(f"  Corriendo {n_sims:,} simulaciones Monte Carlo...", end="", flush=True)

    for i in range(n_sims):
        res = simular_torneo(ajustes)
        for equipo, ronda in res.items():
            nivel = RONDA_ORDEN[ronda]
            conteo[equipo]["total"] += 1
            if nivel >= 1: conteo[equipo]["pasa_grupos"] += 1
            if nivel >= 2: conteo[equipo]["r16"] += 1
            if nivel >= 3: conteo[equipo]["qf"] += 1
            if nivel >= 4: conteo[equipo]["sf"] += 1
            if nivel >= 5: conteo[equipo]["final"] += 1
            if nivel >= 6: conteo[equipo]["campeon"] += 1

        if (i+1) % (n_sims // 4) == 0:
            print(".", end="", flush=True)

    print(" listo")

    filas = []
    for equipo in todos_equipos:
        c = conteo[equipo]
        n = c["total"] or n_sims
        filas.append({
            "equipo":        equipo,
            "pasa_grupos_%": round(c["pasa_grupos"] / n * 100, 1),
            "r16_%":         round(c["r16"]         / n * 100, 1),
            "qf_%":          round(c["qf"]          / n * 100, 1),
            "sf_%":          round(c["sf"]           / n * 100, 1),
            "final_%":       round(c["final"]        / n * 100, 1),
            "campeon_%":     round(c["campeon"]      / n * 100, 1),
        })

    df = pd.DataFrame(filas).sort_values("campeon_%", ascending=False).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────────────────────
#  ODDS API  —  momios en vivo (the-odds-api.com)
# ─────────────────────────────────────────────────────────────

def fetch_live_odds(api_key: str, sport: str = "soccer_fifa_world_cup") -> list[dict]:
    """
    Descarga momios en vivo de the-odds-api.com.
    Plan gratuito: 500 requests/mes.
    Regístrate en https://the-odds-api.com
    """
    import requests
    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        f"?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal"
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()


def parse_odds(raw: list[dict]) -> list[dict]:
    """Transforma la respuesta de the-odds-api a formato interno."""
    partidos = []
    for evento in raw:
        home = evento.get("home_team", "")
        away = evento.get("away_team", "")
        odds_h = odds_d = odds_a = None
        for book in evento.get("bookmakers", [])[:1]:
            for market in book.get("markets", []):
                if market["key"] == "h2h":
                    for out in market.get("outcomes", []):
                        if out["name"] == home:        odds_h = out["price"]
                        elif out["name"] == away:      odds_a = out["price"]
                        elif out["name"] == "Draw":    odds_d = out["price"]
                elif market["key"] == "totals":
                    for out in market.get("outcomes", []):
                        pt = out.get("point", 0)
                        nm = out.get("name", "")
                        if nm=="Over"  and abs(pt-2.5)<0.1: over_25 = out["price"]
                        if nm=="Under" and abs(pt-2.5)<0.1: under_25 = out["price"]
                        if nm=="Over"  and abs(pt-1.5)<0.1: over_15 = out["price"]
                        if nm=="Under" and abs(pt-1.5)<0.1: under_15 = out["price"]
        partidos.append({"local":home,"visitante":away,"odd_h":odds_h,"odd_d":odds_d,"odd_a":odds_a,"over_2.5":over_25,"under_2.5":under_25,"over_1.5":over_15,"under_1.5":under_15,"commence":evento.get("commence_time","")})
    return partidos


if __name__ == "__main__":
    print("\n" + "="*56)
    print("  SIMULACIÓN MONTE CARLO — MUNDIAL 2026")
    print("="*56)

    df = correr_montecarlo(n_sims=10_000, usar_forma=True)

    print("\n  TOP 16 — Probabilidades por ronda (%)\n")
    from tabulate import tabulate
    print(tabulate(
        df.head(16).values.tolist(),
        headers=["Equipo","Grupos","R16","Cuartos","Semis","Final","Campeón"],
        tablefmt="simple",
        floatfmt=".1f",
    ))

    print("\n  Con ajuste por baja de Mbappé en Francia:")
    df2 = correr_montecarlo(
        n_sims=5_000,
        ajustes={"Francia": {"ataque": 0.80}},
        seed=99,
    )
    f_normal = df[df["equipo"]=="Francia"]["campeon_%"].values[0]
    f_baja   = df2[df2["equipo"]=="Francia"]["campeon_%"].values[0]
    print(f"  Francia campeón (normal): {f_normal}%")
    print(f"  Francia campeón (sin Mbappé): {f_baja}%")
    print(f"  Impacto: {f_baja - f_normal:+.1f}%\n")

    df.to_csv("data/montecarlo_mundial2026.csv", index=False)
    print("  Guardado: data/montecarlo_mundial2026.csv\n")
