"""
predictor.py  (v2)
==================
Predictor completo con TODOS los mercados y cálculo automático de probabilidades.
"""

import pandas as pd
from tabulate import tabulate
from stats_engine import compute_lambdas, build_team_stats
from markets import all_markets, ev_market

LEAGUE_AVG = 1.35
HOME_ADV   = 1.10

DEMO_STATS = {
    "Brasil":     {"ataque": 1.85, "defensa": 0.75},
    "Argentina":  {"ataque": 1.70, "defensa": 0.90},
    "Francia":    {"ataque": 1.80, "defensa": 0.85},
    "Inglaterra": {"ataque": 1.60, "defensa": 0.95},
    "España":     {"ataque": 1.75, "defensa": 0.80},
    "Alemania":   {"ataque": 1.65, "defensa": 1.05},
    "Portugal":   {"ataque": 1.90, "defensa": 1.00},
    "Holanda":    {"ataque": 1.55, "defensa": 1.00},
    "Uruguay":    {"ataque": 1.40, "defensa": 0.85},
    "México":     {"ataque": 1.20, "defensa": 1.10},
    "Colombia":   {"ataque": 1.35, "defensa": 1.05},
    "Ecuador":    {"ataque": 1.15, "defensa": 1.15},
    "Marruecos":  {"ataque": 1.10, "defensa": 0.80},
    "Senegal":    {"ataque": 1.20, "defensa": 1.05},
    "Japón":      {"ataque": 1.25, "defensa": 1.00},
    "Corea":      {"ataque": 1.10, "defensa": 1.20},
    "EEUU":       {"ataque": 1.30, "defensa": 1.10},
    "Canadá":       {"ataque": 1.20, "defensa": 1.20},
    "Australia":    {"ataque": 1.20, "defensa": 1.15},
    "Austria":      {"ataque": 1.35, "defensa": 1.10},
    "Bosnia":       {"ataque": 1.10, "defensa": 1.25},
    "Bélgica":      {"ataque": 1.55, "defensa": 1.00},
    "Cabo Verde":   {"ataque": 0.90, "defensa": 1.30},
    "Camerún":      {"ataque": 1.05, "defensa": 1.20},
    "Costa Marfil": {"ataque": 1.15, "defensa": 1.15},
    "Croacia":      {"ataque": 1.30, "defensa": 1.05},
    "Curazao":      {"ataque": 0.70, "defensa": 1.60},
    "Dinamarca":    {"ataque": 1.35, "defensa": 1.00},
    "Egipto":       {"ataque": 1.00, "defensa": 1.10},
    "Escocia":      {"ataque": 1.05, "defensa": 1.20},
    "Ghana":        {"ataque": 1.00, "defensa": 1.25},
    "Haití":        {"ataque": 0.75, "defensa": 1.50},
    "Irak":         {"ataque": 0.85, "defensa": 1.35},
    "Jordania":     {"ataque": 0.80, "defensa": 1.20},
    "Noruega":      {"ataque": 1.45, "defensa": 1.10},
    "Panamá":       {"ataque": 0.90, "defensa": 1.30},
    "Paraguay":     {"ataque": 1.05, "defensa": 1.20},
    "Qatar":        {"ataque": 0.85, "defensa": 1.40},
    "RD Congo":     {"ataque": 1.00, "defensa": 1.20},
    "Rep. Checa":   {"ataque": 1.20, "defensa": 1.15},
    "Arabia S.":    {"ataque": 1.10, "defensa": 1.15},
    "Sudáfrica":    {"ataque": 1.00, "defensa": 1.20},
    "Suecia":       {"ataque": 1.25, "defensa": 1.10},
    "Suiza":        {"ataque": 1.30, "defensa": 1.00},
    "Turquía":      {"ataque": 1.20, "defensa": 1.15},
    "Túnez":        {"ataque": 1.00, "defensa": 1.15},
    "Uzbekistán":   {"ataque": 1.00, "defensa": 1.20},
    "Argelia":      {"ataque": 1.10, "defensa": 1.10},
    "Irán":          {"ataque": 1.15, "defensa": 1.10},
    "Nueva Zelanda": {"ataque": 0.85, "defensa": 1.30},
}


class Predictor:
    def __init__(self, api_token=None, competition="WC", season=2026,
                 league_avg=LEAGUE_AVG, home_advantage=HOME_ADV):
        self.league_avg     = league_avg
        self.home_advantage = home_advantage
        self.team_stats     = {}
        if api_token:
            self._load_from_api(api_token, competition, season)
        else:
            print("  Modo demo — estadísticas históricas integradas.\n")
            self.team_stats = DEMO_STATS

    def _load_from_api(self, token, competition, season):
        import os; os.environ["FOOTBALL_API_TOKEN"] = token
        from api_client import get_matches
        matches = get_matches(competition, season)
        df = build_team_stats(matches)
        for _, row in df.iterrows():
            self.team_stats[row["equipo"]] = {
                "ataque": row["ataque"], "defensa": row["defensa"]}
        print(f"  {len(self.team_stats)} equipos cargados.\n")

    def _get_team(self, nombre):
        for key, val in self.team_stats.items():
            if key.lower() == nombre.lower() or nombre.lower() in key.lower():
                return {"nombre": key, **val}
        # Si no encuentra, usa stats promedio
        print(f"  Aviso: '{nombre}' no en stats, usando promedio")
        return {"nombre": nombre, "ataque": 1.10, "defensa": 1.15}

    # ─────────────────────────────────────────────────────────
    #  MÉTODO PRINCIPAL
    # ─────────────────────────────────────────────────────────
    def analizar(self, local: str, visitante: str,
                 momios: dict | None = None,
                 stake: float = 100.0,
                 mostrar: bool = True) -> dict:
        """
        Analiza un partido y calcula TODOS los mercados automáticamente.

        momios: dict con momios decimales opcionales, ej:
          {
            "local": 2.10, "empate": 3.20, "visitante": 3.50,
            "over_2.5": 1.90, "under_2.5": 1.95,
            "btts_si": 1.75, "btts_no": 2.05,
            "dc_1X": 1.30,  "dc_X2": 1.45, "dc_12": 1.35,
          }
        Si no se pasan momios, solo muestra probabilidades sin EV.
        """
        h = self._get_team(local)
        a = self._get_team(visitante)

        lh, la = compute_lambdas(
            h["ataque"], h["defensa"],
            a["ataque"], a["defensa"],
            self.league_avg, self.home_advantage,
        )

        mkts = all_markets(lh, la)
        ev   = self._calc_ev(mkts, momios or {}, stake)

        result = {
            "local":      h["nombre"],
            "visitante":  a["nombre"],
            "lambda_h":   lh,
            "lambda_a":   la,
            "markets":    mkts,
            "ev":         ev,
            "momios":     momios or {},
            "stake":      stake,
        }

        if mostrar:
            self._print_report(result)

        return result

    # ─────────────────────────────────────────────────────────
    #  Calcula EV para cada momio que se haya pasado
    # ─────────────────────────────────────────────────────────
    def _calc_ev(self, mkts: dict, momios: dict, stake: float) -> dict:
        ev = {}
        MAP = {
            "local":       mkts["1x2"]["local"],
            "empate":      mkts["1x2"]["empate"],
            "visitante":   mkts["1x2"]["visitante"],
            "over_0.5":    mkts["over_under"]["over_0.5"],
            "over_1.5":    mkts["over_under"]["over_1.5"],
            "over_2.5":    mkts["over_under"]["over_2.5"],
            "over_3.5":    mkts["over_under"]["over_3.5"],
            "over_4.5":    mkts["over_under"]["over_4.5"],
            "under_0.5":   mkts["over_under"]["under_0.5"],
            "under_1.5":   mkts["over_under"]["under_1.5"],
            "under_2.5":   mkts["over_under"]["under_2.5"],
            "under_3.5":   mkts["over_under"]["under_3.5"],
            "under_4.5":   mkts["over_under"]["under_4.5"],
            "btts_si":     mkts["btts"]["si"],
            "btts_no":     mkts["btts"]["no"],
            "dc_1X":       mkts["doble_chance"]["1X"],
            "dc_X2":       mkts["doble_chance"]["X2"],
            "dc_12":       mkts["doble_chance"]["12"],
        }
        for key, odd in momios.items():
            if key in MAP:
                ev[key] = ev_market(MAP[key], odd, stake)
        return ev

    # ─────────────────────────────────────────────────────────
    #  REPORTE EN CONSOLA
    # ─────────────────────────────────────────────────────────
    def _print_report(self, r: dict):
        m  = r["markets"]
        ev = r["ev"]
        h  = r["local"]
        a  = r["visitante"]
        sep = "─" * 62

        print(f"\n{'═'*62}")
        print(f"  {h}  vs  {a}")
        print(f"  λ local: {r['lambda_h']}   λ visitante: {r['lambda_a']}   "
              f"Total esperado: {round(r['lambda_h']+r['lambda_a'],2)} goles")
        print(f"{'═'*62}")

        # ── 1X2
        _section("1X2  (probabilidades automáticas)")
        rows = [
            [h,        _bar(m["1x2"]["local"]),     f"{m['1x2']['local']}%",     _ev_cell(ev.get("local"))],
            ["Empate",  _bar(m["1x2"]["empate"]),    f"{m['1x2']['empate']}%",    _ev_cell(ev.get("empate"))],
            [a,        _bar(m["1x2"]["visitante"]),  f"{m['1x2']['visitante']}%", _ev_cell(ev.get("visitante"))],
        ]
        print(tabulate(rows, headers=["Mercado","","Prob.","EV"], tablefmt="simple"))

        # ── Over/Under
        _section("Over / Under")
        ou = m["over_under"]
        rows_ou = []
        for line in [0.5, 1.5, 2.5, 3.5, 4.5]:
            ok = f"over_{line}"
            uk = f"under_{line}"
            rows_ou.append([
                f"Over  {line}", f"{ou[ok]}%",  _ev_cell(ev.get(ok)),
                f"Under {line}", f"{ou[uk]}%", _ev_cell(ev.get(uk)),
            ])
        print(tabulate(rows_ou,
            headers=["Mercado","Prob.","EV","Mercado","Prob.","EV"],
            tablefmt="simple"))

        # ── BTTS
        _section("Ambos equipos marcan (BTTS)")
        rows_b = [
            ["BTTS Sí", f"{m['btts']['si']}%", _ev_cell(ev.get("btts_si"))],
            ["BTTS No", f"{m['btts']['no']}%", _ev_cell(ev.get("btts_no"))],
        ]
        print(tabulate(rows_b, headers=["Mercado","Prob.","EV"], tablefmt="simple"))

        # ── Doble Chance
        _section("Doble chance")
        dc = m["doble_chance"]
        rows_dc = [
            [f"1X  ({h} o empate)", f"{dc['1X']}%", _ev_cell(ev.get("dc_1X"))],
            [f"X2  (empate o {a})", f"{dc['X2']}%", _ev_cell(ev.get("dc_X2"))],
            [f"12  ({h} o {a})",    f"{dc['12']}%", _ev_cell(ev.get("dc_12"))],
        ]
        print(tabulate(rows_dc, headers=["Mercado","Prob.","EV"], tablefmt="simple"))

        # ── Clean sheet & Win to nil
        _section("Clean sheet / Win to nil")
        cs = m["clean_sheet"]; wn = m["win_to_nil"]
        rows_cs = [
            [f"{h} CS (no recibe gol)",  f"{cs['local_cs']}%"],
            [f"{a} CS (no recibe gol)",  f"{cs['visita_cs']}%"],
            [f"{h} gana sin recibir",    f"{wn['local']}%"],
            [f"{a} gana sin recibir",    f"{wn['visitante']}%"],
        ]
        print(tabulate(rows_cs, headers=["Mercado","Prob."], tablefmt="simple"))

        # ── Goles exactos
        _section("Total de goles exactos")
        ge = m["goles_exactos"]
        rows_ge = [(f"{k} goles", f"{v}%") for k, v in ge.items()]
        print(tabulate(rows_ge, headers=["Goles","Prob."], tablefmt="simple"))

        # ── Goles por equipo
        _section("Goles marcados por equipo")
        gl = m["goles_local"]; ga = m["goles_visitante"]
        rows_team = [
            (f"{h} anota {k}", f"{v}%", f"{a} anota {k}", f"{ga.get(k,'0')}%")
            for k, v in gl.items()
        ]
        print(tabulate(rows_team,
            headers=[f"{h}","Prob.",f"{a}","Prob."],
            tablefmt="simple"))

        # ── Handicap asiático
        _section("Handicap asiático (cubre local)")
        hc = m["handicap_asiatico"]
        rows_hc = sorted(
            [(k.replace("home_hc_","HC "), f"{v}%") for k, v in hc.items()],
            key=lambda x: float(x[0].replace("HC ",""))
        )
        print(tabulate(rows_hc, headers=["Línea","P(local cubre)"], tablefmt="simple"))

        # ── Half time
        _section("Resultado al descanso (HT)")
        ht = m["half_time"]
        rows_ht = [
            [h,       f"{ht['local']}%"],
            ["Empate", f"{ht['empate']}%"],
            [a,       f"{ht['visitante']}%"],
        ]
        print(tabulate(rows_ht, headers=["HT","Prob."], tablefmt="simple"))

        # ── HT/FT top 5
        _section("HT / FT combinado (top 5)")
        rows_htft = [(k, f"{v}%") for k, v in list(m["ht_ft"].items())[:5]]
        print(tabulate(rows_htft, headers=["HT/FT","Prob."], tablefmt="simple"))

        # ── Correct Score top 10
        _section("Marcadores exactos (top 10)")
        rows_cs2 = [(s, f"{p}%", _bar(p, 16)) for s, p in list(m["correct_score"].items())[:10]]
        print(tabulate(rows_cs2, headers=["Marcador","Prob.",""], tablefmt="simple"))

        # ── Resumen EV si hay momios
        if ev:
            print(f"\n  {sep}")
            print("  RESUMEN  VALOR ESPERADO")
            print(f"  {sep}")
            ev_rows = []
            for k, d in ev.items():
                ev_rows.append([
                    k, f"{d['prob_modelo_%']}%", f"{d['prob_implicita_%']}%",
                    f"{d['edge_%']:+.1f}%", f"${d['ev_$']:+.2f}", d["señal"]
                ])
            ev_rows.sort(key=lambda x: float(x[4].replace("$","")), reverse=True)
            print(tabulate(ev_rows,
                headers=["Mercado","P.Modelo","P.Implícita","Edge",
                         f"EV(${r['stake']:.0f})","Señal"],
                tablefmt="simple"))

            best = max(ev.items(), key=lambda x: x[1]["ev_$"])
            print(f"\n  {'═'*62}")
            if best[1]["ev_$"] > 0:
                print(f"  MEJOR APUESTA → {best[0].upper()}  "
                      f"EV ${best[1]['ev_$']:+.2f}  "
                      f"(ROI {best[1]['roi_%']:+.1f}%  |  edge {best[1]['edge_%']:+.1f}%)")
            else:
                print("  Ningún mercado tiene valor esperado positivo con estos momios.")
            print(f"  {'═'*62}\n")
        else:
            print(f"\n  Tip: pasa momios={{'local':2.10,'empate':3.20,'visitante':3.50,...}}")
            print("       para ver el cálculo de Valor Esperado en cada mercado.\n")


# ─────────────────────────────────────────────────────────────
#  Helpers de formato
# ─────────────────────────────────────────────────────────────

def _section(title: str):
    print(f"\n  ── {title}")

def _bar(pct: float, width: int = 18) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)

def _ev_cell(ev_dict) -> str:
    if ev_dict is None:
        return "—"
    v = ev_dict["ev_$"]
    s = ev_dict["señal"]
    return f"{'+'if v>0 else ''}{v:.2f} ({s})"
