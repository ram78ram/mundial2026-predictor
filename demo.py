"""
demo.py  (v2)
=============
Demo completa del sistema con todos los mercados.
"""
from predictor import Predictor
import pandas as pd

def main():
    p = Predictor()

    print("\n" + "="*62)
    print("  MUNDIAL 2026 — DEMO COMPLETA DE MERCADOS")
    print("="*62)

    # ── Partido 1: solo probabilidades automáticas (sin momios)
    print("\n>>> SOLO PROBABILIDADES (sin momios):")
    p.analizar("Brasil", "Argentina")

    # ── Partido 2: con momios en múltiples mercados
    print("\n>>> CON MOMIOS + VALOR ESPERADO:")
    p.analizar(
        "Francia", "España",
        momios={
            "local":      2.25,
            "empate":     3.10,
            "visitante":  3.20,
            "over_2.5":   1.90,
            "under_2.5":  1.95,
            "btts_si":    1.75,
            "btts_no":    2.05,
            "dc_1X":      1.30,
            "dc_X2":      1.40,
            "dc_12":      1.35,
            "over_1.5":   1.35,
            "over_3.5":   3.20,
        },
        stake=100,
    )

    # ── Partido 3: México en el Mundial
    p.analizar(
        "México", "Ecuador",
        momios={
            "local":     1.95,
            "empate":    3.30,
            "visitante": 4.00,
            "over_2.5":  2.05,
            "under_2.5": 1.80,
            "btts_si":   1.90,
        },
        stake=200,
    )

    # ── Exportar tabla resumen de 5 partidos
    partidos = [
        ("Brasil",   "Argentina", {"local":2.10,"empate":3.20,"visitante":3.50,
                                   "over_2.5":1.85,"btts_si":1.70}),
        ("Francia",  "España",    {"local":2.25,"empate":3.10,"visitante":3.20,
                                   "over_2.5":1.90,"btts_si":1.75}),
        ("México",   "Ecuador",   {"local":1.95,"empate":3.30,"visitante":4.00,
                                   "over_2.5":2.05,"btts_si":1.90}),
        ("Portugal", "Marruecos", {"local":1.70,"empate":3.50,"visitante":5.00,
                                   "over_2.5":1.80,"btts_si":1.65}),
        ("Japón",    "EEUU",      {"local":3.20,"empate":3.10,"visitante":2.30,
                                   "over_2.5":1.95,"btts_si":1.80}),
    ]

    rows = []
    for h, a, m in partidos:
        r = p.analizar(h, a, momios=m, stake=100, mostrar=False)
        mk = r["markets"]
        ev = r["ev"]

        best_ev_key  = max(ev, key=lambda k: ev[k]["ev_$"]) if ev else "—"
        best_ev_val  = ev[best_ev_key]["ev_$"] if ev else 0

        rows.append({
            "Partido":          f"{r['local']} vs {r['visitante']}",
            "λ local":          r["lambda_h"],
            "λ visita":         r["lambda_a"],
            "P local %":        mk["1x2"]["local"],
            "P empate %":       mk["1x2"]["empate"],
            "P visita %":       mk["1x2"]["visitante"],
            "Over 2.5 %":       mk["over_under"]["over_2.5"],
            "Under 2.5 %":      mk["over_under"]["under_2.5"],
            "BTTS sí %":        mk["btts"]["si"],
            "Marcador #1":      list(mk["correct_score"].keys())[0],
            "Prob marc.1 %":    list(mk["correct_score"].values())[0],
            "Mejor EV mkt":     best_ev_key,
            "EV $100":          f"${best_ev_val:+.2f}",
        })

    df = pd.DataFrame(rows)
    df.to_csv("data/predicciones_full.csv", index=False)

    print("\n" + "="*62)
    print("  RESUMEN — 5 PARTIDOS")
    print("="*62)
    print(df[["Partido","P local %","P empate %","P visita %",
              "Over 2.5 %","BTTS sí %","Mejor EV mkt","EV $100"]].to_string(index=False))
    print("\n  Exportado: data/predicciones_full.csv\n")

if __name__ == "__main__":
    main()
