"""
sharp_money.py
==============
Rastrea movimiento de líneas de Pinnacle (referencia sharp).
- Guarda snapshot de momios cada vez que se consulta
- Detecta movimientos significativos (dinero sharp)
- Clasifica señales: sharp, público, neutral
"""

import sqlite3
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "line_movement.db"
DB_PATH.parent.mkdir(exist_ok=True)

EN_TO_ES = {
    "Belgium":"Bélgica","Egypt":"Egipto","Spain":"España","Cape Verde":"Cabo Verde",
    "France":"Francia","Senegal":"Senegal","Norway":"Noruega","Iraq":"Irak",
    "Cameroon":"Camerún","Denmark":"Dinamarca","Argentina":"Argentina","Algeria":"Argelia",
    "Brazil":"Brasil","Morocco":"Marruecos","Colombia":"Colombia","Saudi Arabia":"Arabia S.",
    "Mexico":"México","South Korea":"Corea","Netherlands":"Holanda","Japan":"Japón",
    "Germany":"Alemania","Ecuador":"Ecuador","USA":"EEUU","Paraguay":"Paraguay",
    "Portugal":"Portugal","Australia":"Australia","England":"Inglaterra","Croatia":"Croacia",
    "Uruguay":"Uruguay","Switzerland":"Suiza","Sweden":"Suecia","Tunisia":"Túnez",
    "Canada":"Canadá","Austria":"Austria","Belgium":"Bélgica","Draw":"Empate",
}


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS line_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            partido     TEXT NOT NULL,
            local       TEXT NOT NULL,
            visitante   TEXT NOT NULL,
            odd_h       REAL,
            odd_d       REAL,
            odd_a       REAL,
            bookmaker   TEXT DEFAULT 'pinnacle'
        )
    """)
    con.commit()
    con.close()

init_db()


def fetch_pinnacle_odds(api_key: str) -> list[dict]:
    """Descarga momios actuales de Pinnacle via The Odds API."""
    url = (f"https://api.the-odds-api.com/v4/sports/soccer_fifa_world_cup/odds"
           f"?apiKey={api_key}&regions=eu&markets=h2h&oddsFormat=decimal&bookmakers=pinnacle")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    
    partidos = []
    for evento in r.json():
        home = evento.get("home_team","")
        away = evento.get("away_team","")
        odd_h = odd_d = odd_a = None
        
        for bk in evento.get("bookmakers",[]):
            if bk["key"] == "pinnacle":
                for mk in bk.get("markets",[]):
                    if mk["key"] == "h2h":
                        for out in mk["outcomes"]:
                            if out["name"] == home:     odd_h = out["price"]
                            elif out["name"] == away:   odd_a = out["price"]
                            elif out["name"] == "Draw": odd_d = out["price"]
        
        if odd_h:
            partidos.append({
                "local":     EN_TO_ES.get(home, home),
                "visitante": EN_TO_ES.get(away, away),
                "partido":   f"{EN_TO_ES.get(home,home)} vs {EN_TO_ES.get(away,away)}",
                "odd_h":     odd_h,
                "odd_d":     odd_d,
                "odd_a":     odd_a,
            })
    return partidos


def save_snapshot(partidos: list[dict]):
    """Guarda snapshot de momios en la BD."""
    con = sqlite3.connect(DB_PATH)
    ts = datetime.utcnow().isoformat()
    for p in partidos:
        con.execute("""
            INSERT INTO line_snapshots (timestamp, partido, local, visitante, odd_h, odd_d, odd_a)
            VALUES (?,?,?,?,?,?,?)
        """, (ts, p["partido"], p["local"], p["visitante"],
              p.get("odd_h"), p.get("odd_d"), p.get("odd_a")))
    con.commit()
    con.close()
    return len(partidos)


def get_movement(partido: str, horas: int = 6) -> dict:
    """
    Compara momio actual vs hace N horas.
    Detecta movimiento y clasifica señal.
    """
    con = sqlite3.connect(DB_PATH)
    cutoff = (datetime.utcnow() - timedelta(hours=horas)).isoformat()
    
    # Más reciente
    cur = con.execute("""
        SELECT odd_h, odd_d, odd_a, timestamp FROM line_snapshots
        WHERE partido=? ORDER BY timestamp DESC LIMIT 1
    """, (partido,))
    latest = cur.fetchone()
    
    # Más antiguo dentro del periodo
    cur = con.execute("""
        SELECT odd_h, odd_d, odd_a, timestamp FROM line_snapshots
        WHERE partido=? AND timestamp >= ? ORDER BY timestamp ASC LIMIT 1
    """, (partido, cutoff))
    oldest = cur.fetchone()
    
    # Historial completo
    cur = con.execute("""
        SELECT odd_h, odd_d, odd_a, timestamp FROM line_snapshots
        WHERE partido=? ORDER BY timestamp ASC
    """, (partido,))
    history = cur.fetchall()
    con.close()
    
    if not latest:
        return {"error": "Sin datos"}
    
    result = {
        "partido":     partido,
        "odd_h_actual": latest[0],
        "odd_d_actual": latest[1],
        "odd_a_actual": latest[2],
        "timestamp":   latest[3],
        "snapshots":   len(history),
        "history":     [{"odd_h": h[0], "odd_d": h[1], "odd_a": h[2], "ts": h[3]} for h in history],
        "movimientos": [],
        "señal_sharp": None,
    }
    
    if oldest and oldest[3] != latest[3]:
        # Calcular cambios
        def cambio(nuevo, viejo):
            if not nuevo or not viejo: return 0
            return round(nuevo - viejo, 3)
        
        dh = cambio(latest[0], oldest[0])
        dd = cambio(latest[1], oldest[1])
        da = cambio(latest[2], oldest[2])
        
        result["cambio_h"] = dh
        result["cambio_d"] = dd
        result["cambio_a"] = da
        result["periodo_horas"] = horas
        
        # Detectar movimientos significativos (>0.05 en decimal)
        UMBRAL = 0.05
        
        if abs(dh) >= UMBRAL:
            direccion = "bajó" if dh < 0 else "subió"
            señal = "🔴 Sharp en LOCAL" if dh < -UMBRAL else "⬆️ Público en LOCAL"
            result["movimientos"].append({
                "mercado": "Local",
                "cambio": dh,
                "direccion": direccion,
                "señal": señal,
            })
        
        if abs(da) >= UMBRAL:
            direccion = "bajó" if da < 0 else "subió"
            señal = "🔴 Sharp en VISITANTE" if da < -UMBRAL else "⬆️ Público en VISITANTE"
            result["movimientos"].append({
                "mercado": "Visitante",
                "cambio": da,
                "direccion": direccion,
                "señal": señal,
            })
        
        if abs(dd) >= UMBRAL:
            direccion = "bajó" if dd < 0 else "subió"
            result["movimientos"].append({
                "mercado": "Empate",
                "cambio": dd,
                "direccion": direccion,
                "señal": f"{'🔴 Sharp' if dd < 0 else '⬆️ Público'} en EMPATE",
            })
        
        # Señal general
        if result["movimientos"]:
            sharps = [m for m in result["movimientos"] if "Sharp" in m["señal"]]
            if sharps:
                result["señal_sharp"] = f"💰 Dinero sharp detectado en {sharps[0]['mercado']}"
            else:
                result["señal_sharp"] = "👥 Movimiento de público (sin señal sharp clara)"
        else:
            result["señal_sharp"] = "➡️ Líneas estables — sin movimiento significativo"
    else:
        result["señal_sharp"] = "📊 Solo 1 snapshot — necesita más tiempo para detectar movimiento"
    
    return result


def sync_and_analyze(api_key: str) -> list[dict]:
    """
    Descarga momios actuales, los guarda y analiza movimientos.
    Devuelve lista de partidos con señales.
    """
    partidos = fetch_pinnacle_odds(api_key)
    save_snapshot(partidos)
    
    resultados = []
    for p in partidos:
        mov = get_movement(p["partido"])
        resultados.append({**p, **mov})
    
    return resultados
