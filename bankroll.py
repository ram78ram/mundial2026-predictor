"""
bankroll.py
===========
Tracker de apuestas y gestión de bankroll.
- Registra cada apuesta en SQLite (data/bankroll.db)
- Calcula Kelly Criterion para tamaño óptimo de apuesta
- Reporta ROI, P&L acumulado, racha, precisión del modelo
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from tabulate import tabulate

DB_PATH = Path(__file__).parent / "data" / "bankroll.db"
DB_PATH.parent.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────────────────────────

def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS apuestas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha       TEXT    NOT NULL,
            partido     TEXT    NOT NULL,
            mercado     TEXT    NOT NULL,
            odd         REAL    NOT NULL,
            stake       REAL    NOT NULL,
            prob_modelo REAL,
            ev_esperado REAL,
            resultado   TEXT,        -- 'ganada' | 'perdida' | 'pendiente' | 'void'
            retorno     REAL,        -- stake * odd si ganó, 0 si perdió
            notas       TEXT
        )
    """)
    con.commit()
    con.close()

init_db()


# ─────────────────────────────────────────────────────────────
#  KELLY CRITERION
# ─────────────────────────────────────────────────────────────

def kelly(prob_modelo: float, odd: float,
          bankroll: float, fraccion: float = 0.25) -> dict:
    """
    Calcula el tamaño óptimo de apuesta con Kelly Criterion.

    fraccion: fracción del Kelly completo a usar (0.25 = Kelly/4, recomendado)
    """
    p = prob_modelo / 100
    b = odd - 1          # ganancia neta por unidad apostada
    q = 1 - p

    kelly_completo = (b * p - q) / b if b > 0 else 0
    kelly_fraccionado = max(kelly_completo * fraccion, 0)

    apuesta_optima = bankroll * kelly_fraccionado
    ev_esperado = bankroll * kelly_fraccionado * (p * b - q)

    return {
        "kelly_completo_%":    round(kelly_completo * 100, 2),
        "kelly_fraccion_%":    round(kelly_fraccionado * 100, 2),
        "apuesta_optima_$":    round(apuesta_optima, 2),
        "ev_esperado_$":       round(ev_esperado, 2),
        "max_apuesta_$":       round(bankroll * 0.05, 2),  # máx 5% del bankroll
        "apuesta_recomendada_$": round(min(apuesta_optima, bankroll * 0.05), 2),
    }


# ─────────────────────────────────────────────────────────────
#  CRUD
# ─────────────────────────────────────────────────────────────

def registrar_apuesta(
    partido: str,
    mercado: str,
    odd: float,
    stake: float,
    prob_modelo: float | None = None,
    ev_esperado: float | None = None,
    notas: str = "",
) -> int:
    """Registra una apuesta nueva. Devuelve el ID."""
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("""
        INSERT INTO apuestas (fecha, partido, mercado, odd, stake,
                              prob_modelo, ev_esperado, resultado, retorno, notas)
        VALUES (?,?,?,?,?,?,?,'pendiente',0,?)
    """, (datetime.now().isoformat()[:16], partido, mercado,
          odd, stake, prob_modelo, ev_esperado, notas))
    apuesta_id = cur.lastrowid
    con.commit(); con.close()
    return apuesta_id


def resolver_apuesta(apuesta_id: int, resultado: str) -> dict:
    """
    Marca una apuesta como resuelta.
    resultado: 'ganada' | 'perdida' | 'void'
    """
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT odd, stake FROM apuestas WHERE id=?",
                      (apuesta_id,)).fetchone()
    if not row:
        con.close()
        return {"error": f"Apuesta {apuesta_id} no encontrada"}

    odd, stake = row
    retorno = round(stake * odd, 2) if resultado == "ganada" else (
        stake if resultado == "void" else 0.0)

    con.execute("""UPDATE apuestas SET resultado=?, retorno=? WHERE id=?""",
                (resultado, retorno, apuesta_id))
    con.commit(); con.close()

    ganancia = retorno - stake
    return {"id": apuesta_id, "resultado": resultado,
            "retorno": retorno, "ganancia": ganancia}


def listar_apuestas(solo_pendientes: bool = False) -> pd.DataFrame:
    con = sqlite3.connect(DB_PATH)
    q = "SELECT * FROM apuestas"
    if solo_pendientes:
        q += " WHERE resultado='pendiente'"
    q += " ORDER BY fecha DESC"
    df = pd.read_sql(q, con)
    con.close()
    return df


# ─────────────────────────────────────────────────────────────
#  REPORTE P&L
# ─────────────────────────────────────────────────────────────

def reporte_pnl(bankroll_inicial: float = 1000.0) -> dict:
    """Genera reporte completo de rendimiento."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute("""
        SELECT resultado, stake, retorno, odd, prob_modelo, ev_esperado, partido
        FROM apuestas
        WHERE resultado != 'pendiente'
    """).fetchall()
    con.close()

    if not rows:
        return {"error": "Sin apuestas resueltas aún"}

    total      = len(rows)
    ganadas    = sum(1 for r in rows if r[0] == "ganada")
    perdidas   = sum(1 for r in rows if r[0] == "perdida")
    total_stk  = sum(r[1] for r in rows if r[0] != "void")
    total_ret  = sum(r[2] for r in rows)
    pnl        = total_ret - total_stk
    roi        = (pnl / total_stk * 100) if total_stk else 0

    # Racha actual
    resueltas = [r[0] for r in rows]
    racha = 0
    ultimo = resueltas[0] if resueltas else None
    for r in resueltas:
        if r == ultimo: racha += 1
        else: break

    # EV esperado vs real
    ev_esperado_total = sum(r[5] or 0 for r in rows)

    stats = {
        "total_apuestas":   total,
        "ganadas":          ganadas,
        "perdidas":         perdidas,
        "tasa_acierto_%":   round(ganadas / total * 100, 1) if total else 0,
        "total_apostado_$": round(total_stk, 2),
        "total_retorno_$":  round(total_ret, 2),
        "pnl_$":            round(pnl, 2),
        "roi_%":            round(roi, 2),
        "bankroll_actual_$": round(bankroll_inicial + pnl, 2),
        "ev_esperado_$":    round(ev_esperado_total, 2),
        "racha_actual":     f"{racha} {'ganadas' if ultimo == 'ganada' else 'perdidas'}",
    }
    return stats


def imprimir_reporte(bankroll_inicial: float = 1000.0):
    stats = reporte_pnl(bankroll_inicial)
    if "error" in stats:
        print(f"\n  {stats['error']}\n")
        return

    print("\n" + "="*52)
    print("  REPORTE DE BANKROLL")
    print("="*52)
    rows = [
        ["Apuestas totales",  stats["total_apuestas"]],
        ["Ganadas / Perdidas",f"{stats['ganadas']} / {stats['perdidas']}"],
        ["Tasa de acierto",   f"{stats['tasa_acierto_%']}%"],
        ["Total apostado",    f"${stats['total_apostado_$']:,.2f}"],
        ["Total retorno",     f"${stats['total_retorno_$']:,.2f}"],
        ["P&L",               f"${stats['pnl_$']:+,.2f}"],
        ["ROI",               f"{stats['roi_%']:+.2f}%"],
        ["Bankroll actual",   f"${stats['bankroll_actual_$']:,.2f}"],
        ["EV esperado acum.", f"${stats['ev_esperado_$']:+.2f}"],
        ["Racha actual",      stats["racha_actual"]],
    ]
    print(tabulate(rows, tablefmt="simple"))
    print("="*52 + "\n")


if __name__ == "__main__":
    print("\n=== TEST BANKROLL ===")

    # Simular apuestas de prueba
    id1 = registrar_apuesta("Brasil vs Marruecos",   "LOCAL",      1.65, 100, 50.6,  8.00, "Confianza alta")
    id2 = registrar_apuesta("Holanda vs Japón",      "VISITANTE",  4.50,  50, 26.2, 17.95, "EV+ detección alerta")
    id3 = registrar_apuesta("Alemania vs Curazao",   "LOCAL",      1.15, 150, 74.7, 10.20, "Favorito claro")
    id4 = registrar_apuesta("Ecuador vs Costa Marfil","OVER 2.5",  1.95,  75, 49.3,  9.69, "Ambos atacan")

    # Resolver con resultados ficticios para el reporte
    resolver_apuesta(id1, "ganada")
    resolver_apuesta(id2, "perdida")
    resolver_apuesta(id3, "ganada")
    resolver_apuesta(id4, "ganada")

    imprimir_reporte(bankroll_inicial=1000.0)

    # Kelly demo
    print("  Kelly Criterion — Brasil vs Marruecos @ 1.65:")
    k = kelly(prob_modelo=50.6, odd=1.65, bankroll=1000.0)
    for key, val in k.items():
        print(f"    {key}: {val}")

    # Pendientes
    pend = listar_apuestas(solo_pendientes=True)
    print(f"\n  Apuestas pendientes: {len(pend)}")
