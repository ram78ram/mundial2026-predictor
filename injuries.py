"""
injuries.py
===========
Sistema de bajas y disponibilidad de jugadores.
Funciona para cualquier liga/torneo.

Impacto en el modelo:
- Portero titular baja    → defensa -15%
- Defensa central titular → defensa -10% por cada uno
- Mediocampista clave     → ataque -8%, defensa -5%
- Delantero titular       → ataque -12% por cada uno
- Jugador dudoso          → mitad del impacto
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "injuries.db"
DB_PATH.parent.mkdir(exist_ok=True)

# ── Impacto por posición y tipo de baja
IMPACTO = {
    "Portero": {
        "confirmed": {"ataque": 0.0,  "defensa": -0.15},
        "doubt":     {"ataque": 0.0,  "defensa": -0.07},
        "suspended": {"ataque": 0.0,  "defensa": -0.12},
    },
    "Defensa": {
        "confirmed": {"ataque": -0.03, "defensa": -0.10},
        "doubt":     {"ataque": -0.01, "defensa": -0.05},
        "suspended": {"ataque": -0.02, "defensa": -0.08},
    },
    "Mediocampista": {
        "confirmed": {"ataque": -0.08, "defensa": -0.05},
        "doubt":     {"ataque": -0.04, "defensa": -0.02},
        "suspended": {"ataque": -0.06, "defensa": -0.04},
    },
    "Delantero": {
        "confirmed": {"ataque": -0.12, "defensa": 0.0},
        "doubt":     {"ataque": -0.06, "defensa": 0.0},
        "suspended": {"ataque": -0.10, "defensa": 0.0},
    },
}

TIPO_LABELS = {
    "confirmed": "🔴 Baja confirmada",
    "doubt":     "🟡 Dudoso",
    "suspended": "🟠 Sancionado",
}

POSICION_EMOJIS = {
    "Portero":       "🧤",
    "Defensa":       "🛡️",
    "Mediocampista": "⚙️",
    "Delantero":     "⚡",
}


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS bajas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            partido_key TEXT NOT NULL,
            equipo      TEXT NOT NULL,
            jugador     TEXT NOT NULL,
            posicion    TEXT NOT NULL,
            es_titular  INTEGER DEFAULT 1,
            tipo        TEXT NOT NULL,
            liga        TEXT DEFAULT 'Mundial',
            fecha       TEXT NOT NULL,
            notas       TEXT DEFAULT ''
        )
    """)
    con.commit()
    con.close()

init_db()


def partido_key(local: str, visitante: str, fecha: str) -> str:
    return f"{fecha}_{local}_{visitante}".replace(" ", "_").lower()


def registrar_baja(
    local: str, visitante: str, fecha: str,
    equipo: str, jugador: str, posicion: str,
    es_titular: bool = True, tipo: str = "confirmed",
    liga: str = "Mundial", notas: str = ""
) -> int:
    con = sqlite3.connect(DB_PATH)
    key = partido_key(local, visitante, fecha)
    cur = con.execute("""
        INSERT INTO bajas (partido_key, equipo, jugador, posicion, es_titular, tipo, liga, fecha, notas)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (key, equipo, jugador, posicion, int(es_titular), tipo, liga,
          datetime.now().isoformat()[:16], notas))
    baja_id = cur.lastrowid
    con.commit()
    con.close()
    return baja_id


def eliminar_baja(baja_id: int):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM bajas WHERE id=?", (baja_id,))
    con.commit()
    con.close()


def get_bajas(local: str, visitante: str, fecha: str) -> list[dict]:
    con = sqlite3.connect(DB_PATH)
    key = partido_key(local, visitante, fecha)
    rows = con.execute("""
        SELECT id, equipo, jugador, posicion, es_titular, tipo, notas
        FROM bajas WHERE partido_key=? ORDER BY equipo, posicion
    """, (key,)).fetchall()
    con.close()
    return [{"id": r[0], "equipo": r[1], "jugador": r[2], "posicion": r[3],
             "es_titular": bool(r[4]), "tipo": r[5], "notas": r[6]} for r in rows]


def calcular_ajuste(local: str, visitante: str, fecha: str) -> dict:
    """
    Calcula el ajuste de ataque/defensa para cada equipo
    basado en las bajas registradas.
    
    Devuelve:
    {
        "local":     {"ataque": -0.12, "defensa": -0.10},
        "visitante": {"ataque": -0.20, "defensa": 0.0},
        "resumen":   [{"equipo": ..., "jugador": ..., "impacto": ...}]
    }
    """
    bajas = get_bajas(local, visitante, fecha)
    
    ajuste = {
        local:     {"ataque": 0.0, "defensa": 0.0},
        visitante: {"ataque": 0.0, "defensa": 0.0},
    }
    resumen = []

    for b in bajas:
        if b["equipo"] not in ajuste:
            continue
        if not b["es_titular"]:
            continue  # Solo titulares tienen impacto significativo

        pos = b["posicion"]
        tipo = b["tipo"]
        imp = IMPACTO.get(pos, {}).get(tipo, {"ataque": 0, "defensa": 0})

        ajuste[b["equipo"]]["ataque"]  += imp["ataque"]
        ajuste[b["equipo"]]["defensa"] += imp["defensa"]

        resumen.append({
            "equipo":   b["equipo"],
            "jugador":  b["jugador"],
            "posicion": pos,
            "tipo":     tipo,
            "impacto_ataque":  imp["ataque"],
            "impacto_defensa": imp["defensa"],
        })

    return {
        "local":     ajuste[local],
        "visitante": ajuste[visitante],
        "resumen":   resumen,
    }


def aplicar_ajuste_al_modelo(stats_local: dict, stats_visitante: dict,
                              ajuste: dict) -> tuple[dict, dict]:
    """
    Aplica el ajuste de bajas a las estadísticas del modelo.
    stats_local/visitante: {"ataque": X, "defensa": Y}
    """
    def apply(stats, adj):
        return {
            "ataque":  max(0.5, stats["ataque"]  * (1 + adj["ataque"])),
            "defensa": max(0.5, stats["defensa"] * (1 + adj["defensa"])),
        }

    new_local     = apply(stats_local,     ajuste["local"])
    new_visitante = apply(stats_visitante, ajuste["visitante"])
    return new_local, new_visitante
