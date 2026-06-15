"""
stats_engine.py
===============
Calcula estadísticas ofensivas y defensivas de cada equipo
a partir de sus partidos jugados, y genera parámetros λ
para el modelo de Poisson Dixon-Coles simplificado.
"""

import numpy as np
import pandas as pd
from collections import defaultdict
from typing import Optional


# ──────────────────────────────────────────────
#  Construcción de estadísticas desde partidos
# ──────────────────────────────────────────────

def build_team_stats(matches: list[dict]) -> pd.DataFrame:
    """
    Recibe lista de partidos de la API y devuelve DataFrame con
    ataque, defensa y forma reciente de cada equipo.

    Filtra solo partidos con status FINISHED.
    """
    stats: dict[str, dict] = defaultdict(lambda: {
        "nombre": "",
        "pj": 0,
        "gf": 0,
        "gc": 0,
        "victorias": 0,
        "empates": 0,
        "derrotas": 0,
        "gf_local": 0,
        "gc_local": 0,
        "gf_visita": 0,
        "gc_visita": 0,
        "ultimos": [],          # últimos 5: 'W', 'D', 'L'
    })

    finished = [m for m in matches if m.get("status") == "FINISHED"]

    for m in finished:
        h_id   = m["homeTeam"]["id"]
        a_id   = m["awayTeam"]["id"]
        h_name = m["homeTeam"]["name"]
        a_name = m["awayTeam"]["name"]
        h_gf   = m["score"]["fullTime"]["home"]
        a_gf   = m["score"]["fullTime"]["away"]

        if h_gf is None or a_gf is None:
            continue

        # ── Local
        s = stats[h_id]
        s["nombre"]    = h_name
        s["pj"]       += 1
        s["gf"]       += h_gf
        s["gc"]       += a_gf
        s["gf_local"] += h_gf
        s["gc_local"] += a_gf
        if h_gf > a_gf:
            s["victorias"] += 1
            s["ultimos"].append("W")
        elif h_gf == a_gf:
            s["empates"] += 1
            s["ultimos"].append("D")
        else:
            s["derrotas"] += 1
            s["ultimos"].append("L")

        # ── Visitante
        s = stats[a_id]
        s["nombre"]    = a_name
        s["pj"]       += 1
        s["gf"]       += a_gf
        s["gc"]       += h_gf
        s["gf_visita"] += a_gf
        s["gc_visita"] += h_gf
        if a_gf > h_gf:
            s["victorias"] += 1
            s["ultimos"].append("W")
        elif a_gf == h_gf:
            s["empates"] += 1
            s["ultimos"].append("D")
        else:
            s["derrotas"] += 1
            s["ultimos"].append("L")

    rows = []
    for tid, s in stats.items():
        if s["pj"] == 0:
            continue
        rows.append({
            "team_id":       tid,
            "equipo":        s["nombre"],
            "pj":            s["pj"],
            "gf":            s["gf"],
            "gc":            s["gc"],
            "ataque":        round(s["gf"] / s["pj"], 3),
            "defensa":       round(s["gc"] / s["pj"], 3),
            "victorias":     s["victorias"],
            "empates":       s["empates"],
            "derrotas":      s["derrotas"],
            "forma":         "".join(s["ultimos"][-5:]),
            "puntos_forma":  _forma_pts(s["ultimos"][-5:]),
        })

    df = pd.DataFrame(rows).sort_values("ataque", ascending=False).reset_index(drop=True)
    return df


def _forma_pts(ultimos: list[str]) -> float:
    """Puntos ponderados de la forma reciente (partido más reciente = más peso)."""
    pesos = [0.10, 0.15, 0.20, 0.25, 0.30]
    mapa  = {"W": 3, "D": 1, "L": 0}
    pts   = [mapa.get(r, 0) for r in ultimos[-5:]]
    while len(pts) < 5:
        pts.insert(0, 0)
    return round(sum(p * w for p, w in zip(pts, pesos)), 3)


# ──────────────────────────────────────────────
#  Modelo Poisson
# ──────────────────────────────────────────────

def poisson_pmf(lam: float, k: int) -> float:
    """P(X = k) para distribución de Poisson."""
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    log_p = -lam + k * np.log(lam) - sum(np.log(i) for i in range(1, k + 1))
    return float(np.exp(log_p))


def compute_lambdas(
    home_att: float,
    home_def: float,
    away_att: float,
    away_def: float,
    league_avg: float = 1.35,
    home_advantage: float = 1.15,
) -> tuple[float, float]:
    """
    Devuelve (λ_home, λ_away) esperados usando el modelo Dixon-Coles simplificado.

    λ_home = (ataque_local / λ_liga) × (defensa_rival / λ_liga) × λ_liga × ventaja_local
    λ_away = (ataque_visita / λ_liga) × (defensa_local / λ_liga) × λ_liga
    """
    lh = (home_att / league_avg) * (away_def / league_avg) * league_avg * home_advantage
    la = (away_att / league_avg) * (home_def / league_avg) * league_avg
    return round(max(lh, 0.01), 4), round(max(la, 0.01), 4)


def score_matrix(lh: float, la: float, max_goals: int = 8) -> np.ndarray:
    """
    Matriz de probabilidades de marcadores.
    mat[i][j] = P(local=i, visitante=j)
    """
    mat = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            mat[i][j] = poisson_pmf(lh, i) * poisson_pmf(la, j)
    return mat


def match_probabilities(mat: np.ndarray) -> dict[str, float]:
    """Calcula P(local gana), P(empate), P(visitante gana) desde la matriz."""
    n = mat.shape[0]
    ph, pd_, pa = 0.0, 0.0, 0.0
    for i in range(n):
        for j in range(n):
            if i > j:
                ph += mat[i][j]
            elif i == j:
                pd_ += mat[i][j]
            else:
                pa += mat[i][j]
    return {
        "home":  round(ph,  4),
        "draw":  round(pd_, 4),
        "away":  round(pa,  4),
    }


def top_scores(mat: np.ndarray, top_n: int = 8) -> list[dict]:
    """Devuelve los n marcadores más probables en orden descendente."""
    n = mat.shape[0]
    scores = []
    for i in range(n):
        for j in range(n):
            scores.append({"marcador": f"{i}-{j}", "prob": round(mat[i][j], 5)})
    return sorted(scores, key=lambda x: x["prob"], reverse=True)[:top_n]


# ──────────────────────────────────────────────
#  Valor esperado
# ──────────────────────────────────────────────

def expected_value(prob: float, decimal_odd: float, stake: float = 100.0) -> dict:
    """
    EV = prob × (odd - 1) × stake  -  (1 - prob) × stake
       = stake × (prob × odd - 1)

    Devuelve dict con ev, roi_pct, veredicto.
    """
    ev     = stake * (prob * decimal_odd - 1)
    roi    = (ev / stake) * 100
    implied_prob = 1 / decimal_odd

    return {
        "ev":           round(ev, 2),
        "roi_pct":      round(roi, 2),
        "prob_modelo":  round(prob * 100, 2),
        "prob_implicita": round(implied_prob * 100, 2),
        "edge":         round((prob - implied_prob) * 100, 2),
        "veredicto":    "EV+" if ev > 0 else ("Neutro" if ev == 0 else "EV-"),
    }


def overround(odd_h: float, odd_d: float, odd_a: float) -> float:
    """Margen de la casa en %. 0% = mercado justo."""
    return round((1/odd_h + 1/odd_d + 1/odd_a - 1) * 100, 2)
