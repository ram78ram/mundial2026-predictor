"""
fixture.py
==========
Fixture completo del Mundial 2026.
Incluye partidos jugados (con resultado real) y próximos.
Los equipos del fixture se mapean a DEMO_STATS cuando hay coincidencia.
"""

from datetime import date, datetime
import pytz

# ── Resultado real: None = por jugar, (h, a) = marcador final
FIXTURE = [
    {"fecha": "2026-06-11", "grupo": "A", "local": "México", "visitante": "Sudáfrica", "sede": "Mexico City", "resultado": (2, 0)},
    {"fecha": "2026-06-11", "grupo": "A", "local": "Corea", "visitante": "Rep. Checa", "sede": "Guadalajara (Zapopan)", "resultado": (2, 1)},
    {"fecha": "2026-06-18", "grupo": "A", "local": "Rep. Checa", "visitante": "Sudáfrica", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-06-18", "grupo": "A", "local": "México", "visitante": "Corea", "sede": "Guadalajara (Zapopan)", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "A", "local": "Rep. Checa", "visitante": "México", "sede": "Mexico City", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "A", "local": "Sudáfrica", "visitante": "Corea", "sede": "Monterrey (Guadalupe)", "resultado": None},
    {"fecha": "2026-06-12", "grupo": "B", "local": "Canadá", "visitante": "Bosnia", "sede": "Toronto", "resultado": (1, 1)},
    {"fecha": "2026-06-13", "grupo": "B", "local": "Qatar", "visitante": "Suiza", "sede": "San Francisco Bay Area (Santa Clara)", "resultado": (1, 1)},
    {"fecha": "2026-06-18", "grupo": "B", "local": "Suiza", "visitante": "Bosnia", "sede": "Los Angeles (Inglewood)", "resultado": None},
    {"fecha": "2026-06-18", "grupo": "B", "local": "Canadá", "visitante": "Qatar", "sede": "Vancouver", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "B", "local": "Suiza", "visitante": "Canadá", "sede": "Vancouver", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "B", "local": "Bosnia", "visitante": "Qatar", "sede": "Seattle", "resultado": None},
    {"fecha": "2026-06-13", "grupo": "C", "local": "Brasil", "visitante": "Marruecos", "sede": "New York/New Jersey (East Rutherford)", "resultado": (1, 1)},
    {"fecha": "2026-06-13", "grupo": "C", "local": "Haití", "visitante": "Escocia", "sede": "Boston (Foxborough)", "resultado": (0, 1)},
    {"fecha": "2026-06-19", "grupo": "C", "local": "Escocia", "visitante": "Marruecos", "sede": "Boston (Foxborough)", "resultado": None},
    {"fecha": "2026-06-19", "grupo": "C", "local": "Brasil", "visitante": "Haití", "sede": "Philadelphia", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "C", "local": "Escocia", "visitante": "Brasil", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-06-24", "grupo": "C", "local": "Marruecos", "visitante": "Haití", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-06-12", "grupo": "D", "local": "EEUU", "visitante": "Paraguay", "sede": "Los Angeles (Inglewood)", "resultado": (4, 1)},
    {"fecha": "2026-06-13", "grupo": "D", "local": "Australia", "visitante": "Turquía", "sede": "Vancouver", "resultado": (2, 0)},
    {"fecha": "2026-06-19", "grupo": "D", "local": "EEUU", "visitante": "Australia", "sede": "Seattle", "resultado": None},
    {"fecha": "2026-06-19", "grupo": "D", "local": "Turquía", "visitante": "Paraguay", "sede": "San Francisco Bay Area (Santa Clara)", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "D", "local": "Turquía", "visitante": "EEUU", "sede": "Los Angeles (Inglewood)", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "D", "local": "Paraguay", "visitante": "Australia", "sede": "San Francisco Bay Area (Santa Clara)", "resultado": None},
    {"fecha": "2026-06-14", "grupo": "E", "local": "Alemania", "visitante": "Curazao", "sede": "Houston", "resultado": (7, 1)},
    {"fecha": "2026-06-14", "grupo": "E", "local": "Costa Marfil", "visitante": "Ecuador", "sede": "Philadelphia", "resultado": (1, 0)},
    {"fecha": "2026-06-20", "grupo": "E", "local": "Alemania", "visitante": "Costa Marfil", "sede": "Toronto", "resultado": None},
    {"fecha": "2026-06-20", "grupo": "E", "local": "Ecuador", "visitante": "Curazao", "sede": "Kansas City", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "E", "local": "Curazao", "visitante": "Costa Marfil", "sede": "Philadelphia", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "E", "local": "Ecuador", "visitante": "Alemania", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
    {"fecha": "2026-06-14", "grupo": "F", "local": "Holanda", "visitante": "Japón", "sede": "Dallas (Arlington)", "resultado": (2, 2)},
    {"fecha": "2026-06-14", "grupo": "F", "local": "Suecia", "visitante": "Túnez", "sede": "Monterrey (Guadalupe)", "resultado": (5, 1)},
    {"fecha": "2026-06-20", "grupo": "F", "local": "Holanda", "visitante": "Suecia", "sede": "Houston", "resultado": None},
    {"fecha": "2026-06-20", "grupo": "F", "local": "Túnez", "visitante": "Japón", "sede": "Monterrey (Guadalupe)", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "F", "local": "Japón", "visitante": "Suecia", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-06-25", "grupo": "F", "local": "Túnez", "visitante": "Holanda", "sede": "Kansas City", "resultado": None},
    {"fecha": "2026-06-15", "grupo": "G", "local": "Bélgica", "visitante": "Egipto", "sede": "Seattle", "resultado": None},
    {"fecha": "2026-06-15", "grupo": "G", "local": "Irán", "visitante": "Nueva Zelanda", "sede": "Los Angeles (Inglewood)", "resultado": None},
    {"fecha": "2026-06-21", "grupo": "G", "local": "Bélgica", "visitante": "Irán", "sede": "Los Angeles (Inglewood)", "resultado": None},
    {"fecha": "2026-06-21", "grupo": "G", "local": "Nueva Zelanda", "visitante": "Egipto", "sede": "Vancouver", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "G", "local": "Egipto", "visitante": "Irán", "sede": "Seattle", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "G", "local": "Nueva Zelanda", "visitante": "Bélgica", "sede": "Vancouver", "resultado": None},
    {"fecha": "2026-06-15", "grupo": "H", "local": "España", "visitante": "Cabo Verde", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-06-15", "grupo": "H", "local": "Arabia S.", "visitante": "Uruguay", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-06-21", "grupo": "H", "local": "España", "visitante": "Arabia S.", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-06-21", "grupo": "H", "local": "Uruguay", "visitante": "Cabo Verde", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "H", "local": "Cabo Verde", "visitante": "Arabia S.", "sede": "Houston", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "H", "local": "Uruguay", "visitante": "España", "sede": "Guadalajara (Zapopan)", "resultado": None},
    {"fecha": "2026-06-16", "grupo": "I", "local": "Francia", "visitante": "Senegal", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
    {"fecha": "2026-06-16", "grupo": "I", "local": "Irak", "visitante": "Noruega", "sede": "Boston (Foxborough)", "resultado": None},
    {"fecha": "2026-06-22", "grupo": "I", "local": "Francia", "visitante": "Irak", "sede": "Philadelphia", "resultado": None},
    {"fecha": "2026-06-22", "grupo": "I", "local": "Noruega", "visitante": "Senegal", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "I", "local": "Noruega", "visitante": "Francia", "sede": "Boston (Foxborough)", "resultado": None},
    {"fecha": "2026-06-26", "grupo": "I", "local": "Senegal", "visitante": "Irak", "sede": "Toronto", "resultado": None},
    {"fecha": "2026-06-16", "grupo": "J", "local": "Argentina", "visitante": "Argelia", "sede": "Kansas City", "resultado": None},
    {"fecha": "2026-06-16", "grupo": "J", "local": "Austria", "visitante": "Jordania", "sede": "San Francisco Bay Area (Santa Clara)", "resultado": None},
    {"fecha": "2026-06-22", "grupo": "J", "local": "Argentina", "visitante": "Austria", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-06-22", "grupo": "J", "local": "Jordania", "visitante": "Argelia", "sede": "San Francisco Bay Area (Santa Clara)", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "J", "local": "Argelia", "visitante": "Austria", "sede": "Kansas City", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "J", "local": "Jordania", "visitante": "Argentina", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-06-17", "grupo": "K", "local": "Portugal", "visitante": "RD Congo", "sede": "Houston", "resultado": None},
    {"fecha": "2026-06-17", "grupo": "K", "local": "Uzbekistán", "visitante": "Colombia", "sede": "Mexico City", "resultado": None},
    {"fecha": "2026-06-23", "grupo": "K", "local": "Portugal", "visitante": "Uzbekistán", "sede": "Houston", "resultado": None},
    {"fecha": "2026-06-23", "grupo": "K", "local": "Colombia", "visitante": "RD Congo", "sede": "Guadalajara (Zapopan)", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "K", "local": "Colombia", "visitante": "Portugal", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "K", "local": "RD Congo", "visitante": "Uzbekistán", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-06-17", "grupo": "L", "local": "Inglaterra", "visitante": "Croacia", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-06-17", "grupo": "L", "local": "Ghana", "visitante": "Panamá", "sede": "Toronto", "resultado": None},
    {"fecha": "2026-06-23", "grupo": "L", "local": "Inglaterra", "visitante": "Ghana", "sede": "Boston (Foxborough)", "resultado": None},
    {"fecha": "2026-06-23", "grupo": "L", "local": "Panamá", "visitante": "Croacia", "sede": "Toronto", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "L", "local": "Panamá", "visitante": "Inglaterra", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
    {"fecha": "2026-06-27", "grupo": "L", "local": "Croacia", "visitante": "Ghana", "sede": "Philadelphia", "resultado": None},
    {"fecha": "2026-07-04", "grupo": "?", "local": "W74", "visitante": "W77", "sede": "Philadelphia", "resultado": None},
    {"fecha": "2026-07-04", "grupo": "?", "local": "W73", "visitante": "W75", "sede": "Houston", "resultado": None},
    {"fecha": "2026-07-05", "grupo": "?", "local": "W76", "visitante": "W78", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
    {"fecha": "2026-07-05", "grupo": "?", "local": "W79", "visitante": "W80", "sede": "Mexico City", "resultado": None},
    {"fecha": "2026-07-06", "grupo": "?", "local": "W83", "visitante": "W84", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-07-06", "grupo": "?", "local": "W81", "visitante": "W82", "sede": "Seattle", "resultado": None},
    {"fecha": "2026-07-07", "grupo": "?", "local": "W86", "visitante": "W88", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-07-07", "grupo": "?", "local": "W85", "visitante": "W87", "sede": "Vancouver", "resultado": None},
    {"fecha": "2026-07-09", "grupo": "?", "local": "W89", "visitante": "W90", "sede": "Boston (Foxborough)", "resultado": None},
    {"fecha": "2026-07-10", "grupo": "?", "local": "W93", "visitante": "W94", "sede": "Los Angeles (Inglewood)", "resultado": None},
    {"fecha": "2026-07-11", "grupo": "?", "local": "W91", "visitante": "W92", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-07-11", "grupo": "?", "local": "W95", "visitante": "W96", "sede": "Kansas City", "resultado": None},
    {"fecha": "2026-07-14", "grupo": "?", "local": "W97", "visitante": "W98", "sede": "Dallas (Arlington)", "resultado": None},
    {"fecha": "2026-07-15", "grupo": "?", "local": "W99", "visitante": "W100", "sede": "Atlanta", "resultado": None},
    {"fecha": "2026-07-18", "grupo": "?", "local": "L101", "visitante": "L102", "sede": "Miami (Miami Gardens)", "resultado": None},
    {"fecha": "2026-07-19", "grupo": "?", "local": "W101", "visitante": "W102", "sede": "New York/New Jersey (East Rutherford)", "resultado": None},
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
    "Irán":          "Irán",
    "Nueva Zelanda": "Nueva Zelanda",
}

# TODAY se calcula dentro de get_fixture_for_dashboard()

def get_fixture_for_dashboard():
    TODAY = datetime.now(pytz.timezone('America/Mexico_City')).strftime('%Y-%m-%d')
    """
    Devuelve lista de partidos enriquecida con:
    - estado: 'jugado' | 'hoy' | 'proximo'
    - tiene_modelo: True si ambos equipos están en DEMO_STATS
    """
    result = []
    for p in FIXTURE:
        fd = date.fromisoformat(p["fecha"])
        if fd.isoformat() < TODAY:
            estado = "jugado"
        elif fd.isoformat() == TODAY:
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
