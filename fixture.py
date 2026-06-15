"""
fixture.py
==========
Fixture completo del Mundial 2026.
Incluye partidos jugados (con resultado real) y próximos.
Los equipos del fixture se mapean a DEMO_STATS cuando hay coincidencia.
"""

from datetime import date

# ── Resultado real: None = por jugar, (h, a) = marcador final
FIXTURE = [
    # ═══════════════════════════════════════════
    # FASE DE GRUPOS — Jornada 1
    # ═══════════════════════════════════════════
    # Grupo A
    {"fecha": "2026-06-11", "grupo": "A", "local": "México",       "visitante": "Sudáfrica",   "sede": "Ciudad de México",  "resultado": (2, 0)},
    {"fecha": "2026-06-11", "grupo": "A", "local": "Corea",        "visitante": "Rep. Checa",  "sede": "Guadalajara",       "resultado": (2, 1)},
    # Grupo B
    {"fecha": "2026-06-12", "grupo": "B", "local": "Canadá",       "visitante": "Bosnia",      "sede": "Toronto",           "resultado": (1, 1)},
    {"fecha": "2026-06-13", "grupo": "B", "local": "Qatar",        "visitante": "Suiza",       "sede": "San Francisco",     "resultado": None},
    # Grupo C
    {"fecha": "2026-06-13", "grupo": "C", "local": "Brasil",       "visitante": "Marruecos",   "sede": "Nueva Jersey",      "resultado": None},
    {"fecha": "2026-06-13", "grupo": "C", "local": "Haití",        "visitante": "Escocia",     "sede": "Boston",            "resultado": None},
    # Grupo D
    {"fecha": "2026-06-12", "grupo": "D", "local": "EEUU",         "visitante": "Paraguay",    "sede": "Los Ángeles",       "resultado": (4, 1)},
    {"fecha": "2026-06-13", "grupo": "D", "local": "Australia",    "visitante": "Turquía",     "sede": "Seattle",           "resultado": None},
    # Grupo E
    {"fecha": "2026-06-13", "grupo": "E", "local": "Alemania",     "visitante": "Curazao",     "sede": "Toronto",           "resultado": None},
    {"fecha": "2026-06-13", "grupo": "E", "local": "Ecuador",      "visitante": "Costa Marfil","sede": "Kansas City",       "resultado": None},
    # Grupo F
    {"fecha": "2026-06-13", "grupo": "F", "local": "Holanda",      "visitante": "Japón",       "sede": "Houston",           "resultado": None},
    {"fecha": "2026-06-14", "grupo": "F", "local": "Suecia",       "visitante": "Túnez",       "sede": "Monterrey",         "resultado": (1, 1)},
    # Grupo G
    {"fecha": "2026-06-15", "grupo": "G", "local": "Bélgica",      "visitante": "Egipto",      "sede": "Miami",             "resultado": None},
    {"fecha": "2026-06-15", "grupo": "G", "local": "Colombia",     "visitante": "Arabia S.",   "sede": "Dallas",            "resultado": None},
    # Grupo H
    {"fecha": "2026-06-15", "grupo": "H", "local": "España",       "visitante": "Cabo Verde",  "sede": "Atlanta",           "resultado": None},
    {"fecha": "2026-06-15", "grupo": "H", "local": "Camerún",      "visitante": "Dinamarca",   "sede": "NRG Houston",       "resultado": None},
    # Grupo I
    {"fecha": "2026-06-15", "grupo": "I", "local": "Francia",      "visitante": "Senegal",     "sede": "San Francisco",     "resultado": None},
    {"fecha": "2026-06-15", "grupo": "I", "local": "Noruega",      "visitante": "Irak",        "sede": "Minneapolis",       "resultado": None},
    # Grupo J
    {"fecha": "2026-06-16", "grupo": "J", "local": "Argentina",    "visitante": "Argelia",     "sede": "Dallas",            "resultado": None},
    {"fecha": "2026-06-16", "grupo": "J", "local": "Austria",      "visitante": "Jordania",    "sede": "Miami",             "resultado": None},
    # Grupo K
    {"fecha": "2026-06-17", "grupo": "K", "local": "Portugal",     "visitante": "RD Congo",    "sede": "Kansas City",       "resultado": None},
    {"fecha": "2026-06-17", "grupo": "K", "local": "Colombia",     "visitante": "Uzbekistán",  "sede": "Atlanta",           "resultado": None},
    # Grupo L
    {"fecha": "2026-06-17", "grupo": "L", "local": "Inglaterra",   "visitante": "Croacia",     "sede": "NRG Houston",       "resultado": None},
    {"fecha": "2026-06-18", "grupo": "L", "local": "Panamá",       "visitante": "Ghana",       "sede": "Los Ángeles",       "resultado": None},

    # ═══════════════════════════════════════════
    # FASE DE GRUPOS — Jornada 2
    # ═══════════════════════════════════════════
    # Grupo A
    {"fecha": "2026-06-19", "grupo": "A", "local": "México",       "visitante": "Corea",       "sede": "Guadalajara",       "resultado": None},
    {"fecha": "2026-06-19", "grupo": "A", "local": "Sudáfrica",    "visitante": "Rep. Checa",  "sede": "Atlanta",           "resultado": None},
    # Grupo C
    {"fecha": "2026-06-20", "grupo": "C", "local": "Brasil",       "visitante": "Haití",       "sede": "Filadelfia",        "resultado": None},
    {"fecha": "2026-06-20", "grupo": "C", "local": "Escocia",      "visitante": "Marruecos",   "sede": "Boston",            "resultado": None},
    # Grupo J
    {"fecha": "2026-06-22", "grupo": "J", "local": "Argentina",    "visitante": "Austria",     "sede": "Dallas",            "resultado": None},
    {"fecha": "2026-06-22", "grupo": "J", "local": "Argelia",      "visitante": "Jordania",    "sede": "Miami",             "resultado": None},
    # Grupo I
    {"fecha": "2026-06-23", "grupo": "I", "local": "Francia",      "visitante": "Noruega",     "sede": "San Francisco",     "resultado": None},
    {"fecha": "2026-06-23", "grupo": "I", "local": "Senegal",      "visitante": "Irak",        "sede": "Minneapolis",       "resultado": None},
    # Grupo L
    {"fecha": "2026-06-24", "grupo": "L", "local": "Inglaterra",   "visitante": "Panamá",      "sede": "NRG Houston",       "resultado": None},
    {"fecha": "2026-06-24", "grupo": "L", "local": "Croacia",      "visitante": "Ghana",       "sede": "Los Ángeles",       "resultado": None},
    # Grupo K
    {"fecha": "2026-06-25", "grupo": "K", "local": "Portugal",     "visitante": "Colombia",    "sede": "Kansas City",       "resultado": None},
    {"fecha": "2026-06-25", "grupo": "K", "local": "RD Congo",     "visitante": "Uzbekistán",  "sede": "Atlanta",           "resultado": None},

    # ═══════════════════════════════════════════
    # FASE DE GRUPOS — Jornada 3
    # ═══════════════════════════════════════════
    {"fecha": "2026-06-26", "grupo": "A", "local": "México",       "visitante": "Rep. Checa",  "sede": "Ciudad de México",  "resultado": None},
    {"fecha": "2026-06-26", "grupo": "A", "local": "Sudáfrica",    "visitante": "Corea",       "sede": "Guadalajara",       "resultado": None},
    {"fecha": "2026-06-27", "grupo": "C", "local": "Brasil",       "visitante": "Escocia",     "sede": "Filadelfia",        "resultado": None},
    {"fecha": "2026-06-27", "grupo": "C", "local": "Marruecos",    "visitante": "Haití",       "sede": "Boston",            "resultado": None},
    {"fecha": "2026-06-27", "grupo": "J", "local": "Argentina",    "visitante": "Jordania",    "sede": "Dallas",            "resultado": None},
    {"fecha": "2026-06-27", "grupo": "J", "local": "Argelia",      "visitante": "Austria",     "sede": "Miami",             "resultado": None},
    {"fecha": "2026-06-28", "grupo": "I", "local": "Francia",      "visitante": "Irak",        "sede": "San Francisco",     "resultado": None},
    {"fecha": "2026-06-28", "grupo": "I", "local": "Senegal",      "visitante": "Noruega",     "sede": "Minneapolis",       "resultado": None},
    {"fecha": "2026-06-28", "grupo": "L", "local": "Inglaterra",   "visitante": "Ghana",       "sede": "NRG Houston",       "resultado": None},
    {"fecha": "2026-06-28", "grupo": "L", "local": "Croacia",      "visitante": "Panamá",      "sede": "Los Ángeles",       "resultado": None},
    {"fecha": "2026-06-28", "grupo": "K", "local": "Portugal",     "visitante": "Uzbekistán",  "sede": "Kansas City",       "resultado": None},
    {"fecha": "2026-06-28", "grupo": "K", "local": "Colombia",     "visitante": "RD Congo",    "sede": "Atlanta",           "resultado": None},
]

# ── Mapa de nombres del fixture → nombres en DEMO_STATS
TEAM_MAP = {
    "México":       "México",
    "Corea":        "Corea",
    "Brasil":       "Brasil",
    "Marruecos":    "Marruecos",
    "EEUU":         "EEUU",
    "Alemania":     "Alemania",
    "Ecuador":      "Ecuador",
    "Holanda":      "Holanda",
    "Japón":        "Japón",
    "Colombia":     "Colombia",
    "España":       "España",
    "Francia":      "Francia",
    "Senegal":      "Senegal",
    "Argentina":    "Argentina",
    "Portugal":     "Portugal",
    "Inglaterra":   "Inglaterra",
    "Uruguay":      "Uruguay",
    "Canadá":       "Canadá",
    "Australia":    "Australia",
    "Austria":      "Austria",
    "Bosnia":       "Bosnia",
    "Bélgica":      "Bélgica",
    "Cabo Verde":   "Cabo Verde",
    "Camerún":      "Camerún",
    "Costa Marfil": "Costa Marfil",
    "Croacia":      "Croacia",
    "Curazao":      "Curazao",
    "Dinamarca":    "Dinamarca",
    "Egipto":       "Egipto",
    "Escocia":      "Escocia",
    "Ghana":        "Ghana",
    "Haití":        "Haití",
    "Irak":         "Irak",
    "Jordania":     "Jordania",
    "Noruega":      "Noruega",
    "Panamá":       "Panamá",
    "Paraguay":     "Paraguay",
    "Qatar":        "Qatar",
    "RD Congo":     "RD Congo",
    "Rep. Checa":   "Rep. Checa",
    "Arabia S.":    "Arabia S.",
    "Sudáfrica":    "Sudáfrica",
    "Suecia":       "Suecia",
    "Suiza":        "Suiza",
    "Turquía":      "Turquía",
    "Túnez":        "Túnez",
    "Uzbekistán":   "Uzbekistán",
    "Argelia":      "Argelia",
}

TODAY = date.today()

def get_fixture_for_dashboard():
    """
    Devuelve lista de partidos enriquecida con:
    - estado: 'jugado' | 'hoy' | 'proximo'
    - tiene_modelo: True si ambos equipos están en DEMO_STATS
    """
    result = []
    for p in FIXTURE:
        fd = date.fromisoformat(p["fecha"])
        if fd < TODAY:
            estado = "jugado"
        elif fd == TODAY:
            estado = "hoy"
        else:
            estado = "proximo"

        tiene_modelo = (
            p["local"]     in TEAM_MAP and
            p["visitante"] in TEAM_MAP
        )
        result.append({**p, "estado": estado, "tiene_modelo": tiene_modelo})
    return result


def partidos_jugados():
    return [p for p in get_fixture_for_dashboard() if p["estado"] == "jugado"]

def partidos_hoy():
    return [p for p in get_fixture_for_dashboard() if p["estado"] == "hoy"]

def partidos_proximos():
    return [p for p in get_fixture_for_dashboard() if p["estado"] == "proximo"]
