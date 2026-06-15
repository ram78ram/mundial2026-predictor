# Mundial 2026 — Predictor de Apuestas

Sistema de predicción y análisis de apuestas para el Mundial 2026, basado en modelo de Poisson con simulación Monte Carlo.

## Demo en vivo
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://mundial2026-predictor.streamlit.app)

## Características
- Modelo de Poisson con ajuste por forma reciente
- 13 mercados de apuestas con probabilidades automáticas
- Simulación Monte Carlo del torneo completo (hasta 50,000 iteraciones)
- Fixture en vivo con resultados actualizados automáticamente desde GitHub
- Retro-análisis de partidos jugados
- Alertas de Valor Esperado positivo (EV+)
- Tracker de bankroll con Kelly Criterion
- Soporte para alertas por Telegram y email

## Instalación local
```bash
pip install -r requirements.txt
streamlit run dashboard.py
```

## Estructura
```
├── dashboard.py       # App principal (Streamlit)
├── predictor.py       # Motor de predicción
├── markets.py         # Cálculo de mercados
├── monte_carlo.py     # Simulación del torneo
├── alerts.py          # Alertas EV+
├── bankroll.py        # Tracker de apuestas
├── auto_update.py     # Sync de resultados en vivo
├── fixture.py         # Fixture del Mundial 2026
├── stats_engine.py    # Modelo Poisson
└── api_client.py      # Cliente football-data.org
```

## Modelo
Basado en distribución de Poisson con parámetros:
- λ_local = (ataque_local / avg_liga) × (defensa_rival / avg_liga) × avg_liga × ventaja_local
- Ajuste por forma reciente (últimos 5 partidos, pesos exponenciales)
- Simulación Monte Carlo para probabilidades de avance por ronda

⚠️ Las probabilidades son estimaciones estadísticas. Las apuestas conllevan riesgo financiero.
# Mon Jun 15 17:50:59 CST 2026
