"""
markets.py
==========
Motor de mercados de apuestas derivados de la matriz Poisson.
Calcula probabilidad automática para TODOS los mercados comunes.
"""

import numpy as np
from stats_engine import score_matrix, match_probabilities, top_scores


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN CENTRAL: calcula TODOS los mercados de una vez
# ─────────────────────────────────────────────────────────────

def all_markets(lh: float, la: float) -> dict:
    """
    Recibe los lambdas (goles esperados) de local y visitante.
    Devuelve dict con probabilidad automática de cada mercado.
    """
    mat = score_matrix(lh, la, max_goals=10)
    n   = mat.shape[0]

    # ── Acumuladores base
    p_home, p_draw, p_away = 0.0, 0.0, 0.0
    p_btts_yes, p_btts_no  = 0.0, 0.0
    over_goals  = {0.5:0.0, 1.5:0.0, 2.5:0.0, 3.5:0.0, 4.5:0.0}
    under_goals = {0.5:0.0, 1.5:0.0, 2.5:0.0, 3.5:0.0, 4.5:0.0}
    exact_goals = {}           # P(total == k)
    home_goals  = {}           # P(local anota == k)
    away_goals  = {}           # P(visita anota == k)
    dc = {"1X": 0.0, "X2": 0.0, "12": 0.0}  # doble chance
    asian_lines = {}           # handicap asiático -0.5, -1, +0.5, +1
    cs_probs    = {}           # correct score top 12

    for i in range(n):
        for j in range(n):
            p = mat[i][j]
            total = i + j

            # 1X2
            if i > j:   p_home += p
            elif i == j: p_draw += p
            else:        p_away += p

            # BTTS
            if i > 0 and j > 0: p_btts_yes += p
            else:                p_btts_no  += p

            # Over / Under
            for line in over_goals:
                if total > line:  over_goals[line]  += p
                else:             under_goals[line] += p

            # Goles exactos totales
            exact_goals[total] = exact_goals.get(total, 0.0) + p

            # Goles por equipo
            home_goals[i] = home_goals.get(i, 0.0) + p
            away_goals[j] = away_goals.get(j, 0.0) + p

            # Doble chance
            if i >= j: dc["1X"] += p   # local gana o empata
            if j >= i: dc["X2"] += p   # visita gana o empata
            if i != j: dc["12"] += p   # local o visita gana (sin empate)

            # Handicap asiático
            for hc in [-1.5, -1.0, -0.5, 0.5, 1.0, 1.5]:
                key = f"home_hc_{hc:+.1f}"
                adj = i + hc - j          # diferencia ajustada
                if adj > 0:
                    asian_lines[key] = asian_lines.get(key, 0.0) + p

            # Correct score (top)
            cs_probs[f"{i}-{j}"] = cs_probs.get(f"{i}-{j}", 0.0) + p

    # Ordenar correct score
    top_cs = sorted(cs_probs.items(), key=lambda x: x[1], reverse=True)[:12]

    # Half-time / Full-time combinado (HT approx usando Poisson 45min = λ/2)
    lh2, la2 = lh / 2, la / 2
    mat_ht   = score_matrix(lh2, la2, max_goals=6)
    ht_probs = match_probabilities(mat_ht)

    htft = _htft_probs(mat_ht, mat)

    # Win to nil (ganar sin recibir gol)
    home_win_to_nil = sum(mat[i][0] for i in range(1, n))
    away_win_to_nil = sum(mat[0][j] for j in range(1, n))

    # Clean sheet
    home_cs = sum(mat[i][0] for i in range(n))   # visitante no anota
    away_cs = sum(mat[0][j] for j in range(n))   # local no anota

    # Score en ambas mitades (aprox)
    score_both_halves_home = _score_both_halves(lh)
    score_both_halves_away = _score_both_halves(la)

    return {
        # ── 1X2
        "1x2": {
            "local":     round(p_home * 100, 2),
            "empate":    round(p_draw * 100, 2),
            "visitante": round(p_away * 100, 2),
        },
        # ── Doble chance
        "doble_chance": {
            "1X": round(dc["1X"] * 100, 2),
            "X2": round(dc["X2"] * 100, 2),
            "12": round(dc["12"] * 100, 2),
        },
        # ── BTTS
        "btts": {
            "si": round(p_btts_yes * 100, 2),
            "no": round(p_btts_no  * 100, 2),
        },
        # ── Over / Under
        "over_under": {
            f"over_{k}":  round(over_goals[k]  * 100, 2)
            for k in sorted(over_goals)
        } | {
            f"under_{k}": round(under_goals[k] * 100, 2)
            for k in sorted(under_goals)
        },
        # ── Goles exactos totales
        "goles_exactos": {
            str(k): round(exact_goals.get(k, 0) * 100, 2)
            for k in range(8)
        },
        # ── Goles por equipo (anytime scorer proxy)
        "goles_local": {
            str(k): round(home_goals.get(k, 0) * 100, 2)
            for k in range(6)
        },
        "goles_visitante": {
            str(k): round(away_goals.get(k, 0) * 100, 2)
            for k in range(6)
        },
        # ── Handicap asiático
        "handicap_asiatico": {
            k: round(v * 100, 2) for k, v in asian_lines.items()
        },
        # ── Clean sheet
        "clean_sheet": {
            "local_cs":  round(home_cs * 100, 2),   # local no recibe
            "visita_cs": round(away_cs * 100, 2),   # visitante no recibe
        },
        # ── Win to nil
        "win_to_nil": {
            "local":     round(home_win_to_nil * 100, 2),
            "visitante": round(away_win_to_nil * 100, 2),
        },
        # ── Anotar en ambas mitades
        "score_both_halves": {
            "local":     round(score_both_halves_home * 100, 2),
            "visitante": round(score_both_halves_away * 100, 2),
        },
        # ── Half-time result
        "half_time": {
            "local":     round(ht_probs["home"] * 100, 2),
            "empate":    round(ht_probs["draw"] * 100, 2),
            "visitante": round(ht_probs["away"] * 100, 2),
        },
        # ── HT/FT combinado (top 6)
        "ht_ft": htft,
        # ── Correct score top 12
        "correct_score": {
            s: round(p * 100, 2) for s, p in top_cs
        },
        # ── Lambdas usados
        "_lambda": {"home": round(lh, 4), "away": round(la, 4)},
    }


# ─────────────────────────────────────────────────────────────
#  Helpers internos
# ─────────────────────────────────────────────────────────────

def _htft_probs(mat_ht: np.ndarray, mat_ft: np.ndarray) -> dict:
    """Probabilidades HT/FT combinadas (aproximación independiente)."""
    ht = match_probabilities(mat_ht)
    ft = match_probabilities(mat_ft)
    combos = {
        "H/H": round(ht["home"] * ft["home"] * 100, 2),
        "H/X": round(ht["home"] * ft["draw"] * 100, 2),
        "H/A": round(ht["home"] * ft["away"] * 100, 2),
        "X/H": round(ht["draw"] * ft["home"] * 100, 2),
        "X/X": round(ht["draw"] * ft["draw"] * 100, 2),
        "X/A": round(ht["draw"] * ft["away"] * 100, 2),
        "A/H": round(ht["away"] * ft["home"] * 100, 2),
        "A/X": round(ht["away"] * ft["draw"] * 100, 2),
        "A/A": round(ht["away"] * ft["away"] * 100, 2),
    }
    return dict(sorted(combos.items(), key=lambda x: x[1], reverse=True))


def _score_both_halves(lam: float) -> float:
    """P(un equipo anota en AMBAS mitades) ≈ P(anota en 1a) × P(anota en 2a)."""
    from scipy.stats import poisson
    lam_half = lam / 2
    p_score_half = 1 - poisson.pmf(0, lam_half)
    return p_score_half ** 2


# ─────────────────────────────────────────────────────────────
#  EV para cualquier mercado dado su momio
# ─────────────────────────────────────────────────────────────

def ev_market(prob_pct: float, odd: float, stake: float = 100.0) -> dict:
    """
    Calcula EV para cualquier mercado.
    prob_pct : probabilidad en % (ej. 46.3)
    odd      : momio decimal (ej. 2.10)
    stake    : monto apostado
    """
    prob = prob_pct / 100
    ev   = stake * (prob * odd - 1)
    roi  = (ev / stake) * 100
    implied = (1 / odd) * 100
    edge = prob_pct - implied
    return {
        "prob_modelo_%":   round(prob_pct, 2),
        "prob_implicita_%": round(implied, 2),
        "edge_%":          round(edge, 2),
        "ev_$":            round(ev, 2),
        "roi_%":           round(roi, 2),
        "señal":           "EV+" if ev > 0 else ("Neutro" if abs(ev) < 0.01 else "EV-"),
    }
