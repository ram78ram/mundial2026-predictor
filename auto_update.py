"""
auto_update.py
==============
Sincroniza resultados reales del Mundial 2026 desde:
  https://github.com/openfootball/world-cup.json

- Descarga el JSON en cada ejecución (con caché de 15 min)
- Mapea nombres en inglés → nombres en español del fixture
- Actualiza automáticamente fixture.py con los resultados confirmados
- Imprime un resumen de qué cambió
"""

import requests
import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import pytz

# ── Fuente de datos
SOURCE_URL = "https://raw.githubusercontent.com/openfootball/world-cup.json/master/2026/worldcup.json"
CACHE_FILE = Path(__file__).parent / "data" / "wc2026_live.json"
CACHE_MINUTES = 15

# ── Mapa inglés → español (nombres del fixture.py)
EN_TO_ES = {
    "Mexico":               "México",
    "South Africa":         "Sudáfrica",
    "South Korea":          "Corea",
    "Czech Republic":       "Rep. Checa",
    "Canada":               "Canadá",
    "Bosnia & Herzegovina": "Bosnia",
    "Qatar":                "Qatar",
    "Switzerland":          "Suiza",
    "Brazil":               "Brasil",
    "Morocco":              "Marruecos",
    "Haiti":                "Haití",
    "Scotland":             "Escocia",
    "USA":                  "EEUU",
    "Paraguay":             "Paraguay",
    "Australia":            "Australia",
    "Turkey":               "Turquía",
    "Germany":              "Alemania",
    "Curaçao":              "Curazao",
    "Ivory Coast":          "Costa Marfil",
    "Ecuador":              "Ecuador",
    "Netherlands":          "Holanda",
    "Japan":                "Japón",
    "Sweden":               "Suecia",
    "Tunisia":              "Túnez",
    "Belgium":              "Bélgica",
    "Egypt":                "Egipto",
    "Colombia":             "Colombia",
    "Saudi Arabia":         "Arabia S.",
    "Spain":                "España",
    "Cape Verde":           "Cabo Verde",
    "Cameroon":             "Camerún",
    "Denmark":              "Dinamarca",
    "France":               "Francia",
    "Senegal":              "Senegal",
    "Norway":               "Noruega",
    "Iraq":                 "Irak",
    "Argentina":            "Argentina",
    "Algeria":              "Argelia",
    "Austria":              "Austria",
    "Jordan":               "Jordania",
    "Portugal":             "Portugal",
    "DR Congo":             "RD Congo",
    "Uzbekistan":           "Uzbekistán",
    "England":              "Inglaterra",
    "Croatia":              "Croacia",
    "Panama":               "Panamá",
    "Ghana":                "Ghana",
    "Uruguay":              "Uruguay",
    "Iran":                 "Irán",
    "New Zealand":          "Nueva Zelanda",
}


def _fetch_data() -> dict:
    """Descarga el JSON con caché de 15 minutos."""
    CACHE_FILE.parent.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        age = datetime.now() - datetime.fromtimestamp(CACHE_FILE.stat().st_mtime)
        if age < timedelta(minutes=CACHE_MINUTES):
            print(f"  [caché] Usando datos de hace {int(age.total_seconds()/60)} min")
            return json.loads(CACHE_FILE.read_text())

    print(f"  [descarga] {SOURCE_URL}")
    resp = requests.get(SOURCE_URL, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    CACHE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"  {len(data.get('matches', []))} partidos descargados")
    return data


def get_live_results() -> dict[tuple, tuple | None]:
    """
    Devuelve dict  (local_es, visitante_es) → (goles_local, goles_visitante) | None
    Solo incluye partidos con score confirmado (ft != None).
    """
    data = _fetch_data()
    results = {}
    for m in data.get("matches", []):
        t1 = EN_TO_ES.get(m["team1"])
        t2 = EN_TO_ES.get(m["team2"])
        if not t1 or not t2:
            continue                         # partido eliminatorio aún sin equipos fijos
        score = m.get("score", {})
        ft = score.get("ft")
        results[(t1, t2)] = tuple(ft) if ft else None
    return results


def patch_fixture(dry_run: bool = False) -> list[str]:
    """
    Lee fixture.py, aplica los resultados reales y lo reescribe.
    Devuelve lista de cambios realizados.
    Pasa dry_run=True para solo ver qué cambiaría sin escribir.
    """
    live = get_live_results()
    fixture_path = Path(__file__).parent / "fixture.py"
    content = fixture_path.read_text()
    changes = []

    from datetime import date
    today = datetime.now(pytz.timezone('America/Mexico_City')).strftime('%Y-%m-%d')
    
    for (local, visitante), score in live.items():
        if score is None:
            continue

        # Busca la línea con resultado: None para este partido
        old = f'"local": "{local}",       "visitante": "{visitante}"'
        if old not in content:
            # Intenta variante con espacios distintos
            old = None
            import re
            pat = rf'"local":\s*"{re.escape(local)}",\s*"visitante":\s*"{re.escape(visitante)}"[^}}]+?"resultado":\s*None'
            match = re.search(pat, content)
            if match:
                old_block = match.group(0)
                new_block = old_block.replace('"resultado": None', f'"resultado": {score}')
                if old_block != new_block:
                    changes.append(f"  {local} {score[0]}-{score[1]} {visitante}")
                    if not dry_run:
                        content = content.replace(old_block, new_block)
        else:
            # Encontró la parte del nombre, ahora verifica si ya tiene resultado
            import re
            pat = rf'"local":\s*"{re.escape(local)}",\s*"visitante":\s*"{re.escape(visitante)}"[^}}]+?"resultado":\s*None'
            match = re.search(pat, content)
            if match:
                old_block = match.group(0)
                # NO aplicar resultados de partidos de hoy o futuros
                fecha_en_bloque = re.search(r'"fecha": "(\d{4}-\d{2}-\d{2})"', old_block)
                if fecha_en_bloque and fecha_en_bloque.group(1) >= today:
                    continue
                new_block = old_block.replace('"resultado": None', f'"resultado": {score}')
                changes.append(f"  {local} {score[0]}-{score[1]} {visitante}")
                if not dry_run:
                    content = content.replace(old_block, new_block)

    if not dry_run and changes:
        fixture_path.write_text(content)

    return changes


def sync(dry_run: bool = False) -> None:
    """Punto de entrada principal. Sincroniza y reporta."""
    print("\n═" * 30)
    print("  Mundial 2026 — Sincronización de resultados")
    print("═" * 30)

    changes = patch_fixture(dry_run=dry_run)

    if changes:
        prefix = "[DRY RUN] Cambiaría:" if dry_run else "Actualizados:"
        print(f"\n  {prefix}")
        for c in changes:
            print(c)
    else:
        print("\n  Sin cambios — fixture ya está al día")

    # Mostrar resumen actual
    live = get_live_results()
    scored = [(k, v) for k, v in live.items() if v is not None]
    pending = [(k, v) for k, v in live.items() if v is None]
    print(f"\n  Partidos con resultado: {len(scored)}")
    print(f"  Partidos pendientes:    {len(pending)}")
    print("═" * 30 + "\n")


if __name__ == "__main__":
    import sys
    dry = "--dry" in sys.argv
    sync(dry_run=dry)
