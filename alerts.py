"""
alerts.py
=========
Sistema de alertas automáticas de EV+.
Soporta: Telegram, Email, y consola.

Configurar en .env:
  TELEGRAM_TOKEN=tu_bot_token
  TELEGRAM_CHAT_ID=tu_chat_id
  ODDS_API_KEY=tu_api_key (the-odds-api.com, gratis)
  EMAIL_FROM=tu@gmail.com
  EMAIL_PASS=app_password
  EMAIL_TO=destino@gmail.com
"""

import os, json, requests, smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from markets import all_markets, ev_market
from stats_engine import compute_lambdas
from predictor import DEMO_STATS
from monte_carlo import fetch_live_odds, parse_odds, EN_TO_ES

CACHE_ODDS = Path(__file__).parent / "data" / "odds_cache.json"

# ─────────────────────────────────────────────────────────────
#  OBTENER MOMIOS (API o simulados para demo)
# ─────────────────────────────────────────────────────────────

DEMO_ODDS = [
    {"local":"Brasil",    "visitante":"Marruecos", "odd_h":1.65,"odd_d":3.60,"odd_a":5.50,
     "over_2.5":1.85,"btts_si":1.75},
    {"local":"Haití",     "visitante":"Escocia",   "odd_h":4.50,"odd_d":3.30,"odd_a":1.90,
     "over_2.5":2.10,"btts_si":2.00},
    {"local":"Alemania",  "visitante":"Curazao",   "odd_h":1.15,"odd_d":7.00,"odd_a":18.0,
     "over_2.5":1.50,"btts_si":2.20},
    {"local":"Holanda",   "visitante":"Japón",     "odd_h":1.80,"odd_d":3.50,"odd_a":4.50,
     "over_2.5":1.90,"btts_si":1.80},
    {"local":"Ecuador",   "visitante":"Costa Marfil","odd_h":2.10,"odd_d":3.10,"odd_a":3.50,
     "over_2.5":1.95,"btts_si":1.85},
    {"local":"Qatar",     "visitante":"Suiza",     "odd_h":5.00,"odd_d":3.50,"odd_a":1.70,
     "over_2.5":2.00,"btts_si":1.90},
    {"local":"Francia",   "visitante":"Senegal",   "odd_h":1.70,"odd_d":3.60,"odd_a":5.20,
     "over_2.5":1.85,"btts_si":1.80},
]

MERCADOS_MAP = {
    "odd_h":     "local",
    "odd_d":     "empate",
    "odd_a":     "visitante",
    "over_2.5":  "over_2.5",
    "btts_si":   "btts_si",
}

def obtener_momios(api_key: str | None = None) -> list[dict]:
    """
    Intenta descargar momios reales. Si no hay API key, usa demos.
    Los nombres se mantienen en inglés para búsqueda flexible.
    """
    if api_key:
        try:
            raw = fetch_live_odds(api_key)
            partidos = parse_odds(raw)
            CACHE_ODDS.write_text(json.dumps(partidos, ensure_ascii=False))
            print(f"  {len(partidos)} partidos con momios descargados")
            return partidos
        except Exception as e:
            print(f"  Odds API error: {e} — usando demo")
    return DEMO_ODDS


# ─────────────────────────────────────────────────────────────
#  ANÁLISIS DE VALOR
# ─────────────────────────────────────────────────────────────

def analizar_oportunidades(
    partidos: list[dict],
    stake: float = 100.0,
    umbral_ev: float = 5.0,
    umbral_edge: float = 3.0,
) -> list[dict]:
    """
    Filtra partidos con EV+ sobre el umbral.
    Devuelve lista de oportunidades ordenadas por EV descendente.
    """
    oportunidades = []

    for p in partidos:
        h = p["local"]
        a = p["visitante"]
        if h not in DEMO_STATS or a not in DEMO_STATS:
            continue

        hs = DEMO_STATS[h]; as_ = DEMO_STATS[a]
        lh, la = compute_lambdas(hs["ataque"], hs["defensa"],
                                  as_["ataque"], as_["defensa"])
        mkts = all_markets(lh, la)

        momios_partido = {MERCADOS_MAP[k]: v
                          for k, v in p.items()
                          if k in MERCADOS_MAP and v}

        for mkt_key, odd in momios_partido.items():
            prob_map = {
                "local":      mkts["1x2"]["local"],
                "empate":     mkts["1x2"]["empate"],
                "visitante":  mkts["1x2"]["visitante"],
                "over_2.5":   mkts["over_under"]["over_2.5"],
                "btts_si":    mkts["btts"]["si"],
            }
            prob = prob_map.get(mkt_key)
            if prob is None:
                continue

            ev = ev_market(prob, odd, stake)
            if ev["ev_$"] >= umbral_ev and ev["edge_%"] >= umbral_edge:
                oportunidades.append({
                    "partido":    f"{h} vs {a}",
                    "mercado":    mkt_key.upper().replace("_"," "),
                    "odd":        odd,
                    "prob_%":     prob,
                    "implied_%":  ev["prob_implicita_%"],
                    "edge_%":     ev["edge_%"],
                    "ev_$":       ev["ev_$"],
                    "roi_%":      ev["roi_%"],
                })

    return sorted(oportunidades, key=lambda x: x["ev_$"], reverse=True)


# ─────────────────────────────────────────────────────────────
#  ENVÍO DE ALERTAS
# ─────────────────────────────────────────────────────────────

def _fmt_mensaje(oportunidades: list[dict], stake: float) -> str:
    lines = [
        f"MUNDIAL 2026 — ALERTAS EV+",
        f"{datetime.now().strftime('%d/%m/%Y %H:%M')}",
        f"{len(oportunidades)} oportunidades detectadas\n",
    ]
    for i, o in enumerate(oportunidades, 1):
        lines.append(
            f"{i}. {o['partido']}\n"
            f"   Mercado: {o['mercado']} @ {o['odd']}\n"
            f"   Prob modelo: {o['prob_%']:.1f}%  Implícita: {o['implied_%']:.1f}%\n"
            f"   Edge: +{o['edge_%']:.1f}%  EV: +${o['ev_$']:.2f}  ROI: +{o['roi_%']:.1f}%\n"
        )
    return "\n".join(lines)


def enviar_telegram(token: str, chat_id: str, mensaje: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": mensaje}, timeout=10)
    return r.status_code == 200


def enviar_email(from_: str, password: str, to: str, mensaje: str) -> bool:
    msg = MIMEText(mensaje)
    msg["Subject"] = f"Mundial 2026 — {len(mensaje.splitlines())} alertas EV+"
    msg["From"]    = from_
    msg["To"]      = to
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(from_, password)
            s.sendmail(from_, [to], msg.as_string())
        return True
    except Exception as e:
        print(f"  Email error: {e}")
        return False


# ─────────────────────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────────────────────

def correr_alertas(
    stake: float = 100.0,
    umbral_ev: float = 5.0,
    umbral_edge: float = 3.0,
    odds_api_key: str | None = None,
    telegram_token: str | None = None,
    telegram_chat_id: str | None = None,
    email_from: str | None = None,
    email_pass: str | None = None,
    email_to: str | None = None,
) -> list[dict]:
    """Punto de entrada. Detecta y envía alertas."""
    from tabulate import tabulate

    print("\n" + "="*56)
    print("  SISTEMA DE ALERTAS EV+ — MUNDIAL 2026")
    print("="*56)

    partidos   = obtener_momios(odds_api_key)
    oportunidades = analizar_oportunidades(partidos, stake, umbral_ev, umbral_edge)

    if not oportunidades:
        print(f"\n  Sin oportunidades EV≥${umbral_ev} con edge≥{umbral_edge}% ahora mismo.\n")
        return []

    print(f"\n  {len(oportunidades)} oportunidades detectadas:\n")
    rows = [[o["partido"], o["mercado"], o["odd"],
             f"{o['prob_%']:.1f}%", f"{o['edge_%']:+.1f}%",
             f"${o['ev_$']:+.2f}", f"{o['roi_%']:+.1f}%"]
            for o in oportunidades]
    print(tabulate(rows,
        headers=["Partido","Mercado","Odd","P.Modelo","Edge",f"EV(${stake:.0f})","ROI"],
        tablefmt="simple"))

    # Enviar alertas si hay credenciales
    mensaje = _fmt_mensaje(oportunidades, stake)

    tg_token = telegram_token or os.getenv("TELEGRAM_TOKEN")
    tg_chat  = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
    if tg_token and tg_chat:
        ok = enviar_telegram(tg_token, tg_chat, mensaje)
        print(f"\n  Telegram: {'enviado' if ok else 'error'}")

    em_from  = email_from or os.getenv("EMAIL_FROM")
    em_pass  = email_pass or os.getenv("EMAIL_PASS")
    em_to    = email_to   or os.getenv("EMAIL_TO")
    if em_from and em_pass and em_to:
        ok = enviar_email(em_from, em_pass, em_to, mensaje)
        print(f"  Email: {'enviado' if ok else 'error'}")

    print()
    return oportunidades


if __name__ == "__main__":
    correr_alertas(stake=100, umbral_ev=4.0, umbral_edge=2.5)
