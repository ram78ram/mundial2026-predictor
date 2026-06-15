import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import date, datetime
from predictor import Predictor, DEMO_STATS
from markets import all_markets, ev_market
from stats_engine import compute_lambdas
from fixture import get_fixture_for_dashboard, TEAM_MAP
from auto_update import sync, get_live_results, CACHE_FILE

st.set_page_config(page_title="Mundial 2026 — Predictor", page_icon="⚽", layout="wide")

# ── Auto-sync al iniciar (una vez por sesión, respetando caché de 15 min)
if "last_sync" not in st.session_state:
    with st.spinner("Sincronizando resultados..."):
        try:
            sync(dry_run=False)
            import importlib, fixture as _fix
            importlib.reload(_fix)
            st.session_state["last_sync"] = datetime.now()
        except Exception as e:
            st.session_state["last_sync"] = None
            st.session_state["sync_error"] = str(e)

st.markdown("""
<style>
.metric-card{background:var(--secondary-background-color,#f0f2f6);border-radius:10px;padding:14px 16px;text-align:center}
.metric-val{font-size:1.8rem;font-weight:700;margin:4px 0}
.metric-lbl{font-size:.75rem;color:#888;text-transform:uppercase;letter-spacing:.05em}
.tag{display:inline-block;padding:2px 9px;border-radius:10px;font-size:.75rem;font-weight:600}
.tag-pos{background:#d1e7dd;color:#0f5132}
.tag-neg{background:#f8d7da;color:#842029}
.tag-hoy{background:#fff3cd;color:#664d03}
.tag-jugado{background:#e2e3e5;color:#41464b}
.tag-proximo{background:#cfe2ff;color:#084298}
.partido-card{border:1px solid #dee2e6;border-radius:10px;padding:12px 16px;margin-bottom:8px;cursor:pointer}
.partido-card:hover{background:#f8f9fa}
.match-score{font-size:1.1rem;font-weight:700;color:#212529}
</style>
""", unsafe_allow_html=True)

# Cargar API key desde Streamlit secrets o variable de entorno
import os
ODDS_API_KEY = None
try:
    ODDS_API_KEY = st.secrets["ODDS_API_KEY"]
except:
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")

@st.cache_resource
def get_predictor():
    return Predictor()

predictor = get_predictor()
all_matches = get_fixture_for_dashboard()

# ─────────────────────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Mundial 2026")
    st.caption(f"Hoy: {date.today().strftime('%d %b %Y')}")

    # ── Estado de sincronización
    if st.session_state.get("sync_error"):
        st.error(f"Sin conexión: usando datos locales")
    else:
        last = st.session_state.get("last_sync")
        if last:
            mins = int((datetime.now() - last).total_seconds() / 60)
            st.success(f"Datos actualizados hace {mins} min")
        if CACHE_FILE.exists():
            age_min = int((datetime.now() - datetime.fromtimestamp(
                CACHE_FILE.stat().st_mtime)).total_seconds() / 60)
            live = get_live_results()
            scored = sum(1 for v in live.values() if v)
            st.caption(f"{scored} resultados confirmados · caché {age_min} min")

    if st.button("Sincronizar resultados", use_container_width=True):
        # Borrar caché para forzar descarga
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
        with st.spinner("Descargando resultados..."):
            try:
                sync(dry_run=False)
                import importlib, fixture as _fix
                importlib.reload(_fix)
                st.session_state["last_sync"] = datetime.now()
                st.session_state.pop("sync_error", None)
                st.success("Actualizado")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")

    vista = st.radio("Vista", ["Fixture", "Analizador de partido", "Monte Carlo", "Alertas EV+", "Sharp Money", "Bankroll"], label_visibility="collapsed")

    if vista == "Analizador de partido":
        st.markdown("### Equipos")
        equipos = sorted(DEMO_STATS.keys())
        home = st.selectbox("Local", equipos, index=equipos.index("Brasil"))
        away_opts = [e for e in equipos if e != home]
        away = st.selectbox("Visitante", away_opts, index=away_opts.index("Argentina") if "Argentina" in away_opts else 0)

        st.markdown("### Momios de Playdoit")
        st.caption("Ingresa los momios que ves en Playdoit")
        odd_h  = st.number_input("Local",     1.01, 50.0, 2.10, 0.05)
        odd_d  = st.number_input("Empate",    1.01, 50.0, 3.20, 0.05)
        odd_a  = st.number_input("Visitante", 1.01, 50.0, 3.50, 0.05)
        odd_o25     = st.number_input("Over 2.5",  1.01, 20.0, 1.90, 0.05)
        odd_u25     = st.number_input("Under 2.5", 1.01, 20.0, 1.95, 0.05)
        odd_o15     = st.number_input("Over 1.5",  1.01, 20.0, 1.35, 0.05)
        odd_btts_si = st.number_input("BTTS Sí",   1.01, 20.0, 1.75, 0.05)
        odd_btts_no = st.number_input("BTTS No",   1.01, 20.0, 2.05, 0.05)
        odd_dc1X    = st.number_input("DC 1X",     1.01, 20.0, 1.30, 0.05)
        odd_dcX2    = st.number_input("DC X2",     1.01, 20.0, 1.40, 0.05)
        stake       = st.number_input("Apuesta ($)", 1, 10000, 100, 10)
        analizar_btn = st.button("🔍 Analizar partido", type="primary", use_container_width=True)
        if not analizar_btn and "analizador_ready" not in st.session_state:
            st.session_state["analizador_ready"] = False
        if analizar_btn:
            st.session_state["analizador_ready"] = True

    else:
        # Valores por defecto para variables del analizador
        home = "Brasil"; away = "Argentina"
        odd_h = 2.10; odd_d = 3.20; odd_a = 3.50
        odd_o25 = 1.90; odd_u25 = 1.95; odd_o15 = 1.35
        odd_btts_si = 1.75; odd_btts_no = 2.05
        odd_dc1X = 1.30; odd_dcX2 = 1.40; stake = 100

        st.markdown("### Filtrar fixture")
        filtro_estado = st.multiselect(
            "Estado",
            ["jugado", "hoy", "proximo"],
            default=["hoy", "proximo"],
        )
        grupos_disp = sorted(set(p["grupo"] for p in all_matches))
        filtro_grupo = st.multiselect("Grupo", grupos_disp, default=grupos_disp)
        solo_con_modelo = st.toggle("Solo equipos con modelo", value=False)

# ═════════════════════════════════════════════════════════════
#  VISTA FIXTURE
# ═════════════════════════════════════════════════════════════
if vista == "Fixture" and not st.session_state.get("vista_override"):
    st.markdown("# Fixture Mundial 2026")

    # Métricas rápidas
    jugados  = sum(1 for p in all_matches if p["estado"] == "jugado")
    hoy_n    = sum(1 for p in all_matches if p["estado"] == "hoy")
    proximos = sum(1 for p in all_matches if p["estado"] == "proximo")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Total partidos</div><div class="metric-val">{len(all_matches)}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Jugados</div><div class="metric-val" style="color:#6c757d">{jugados}</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Hoy</div><div class="metric-val" style="color:#f59e0b">{hoy_n}</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-lbl">Próximos</div><div class="metric-val" style="color:#3b82f6">{proximos}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filtrar
    mostrar = [
        p for p in all_matches
        if p["estado"] in filtro_estado
        and p["grupo"] in filtro_grupo
        and (not solo_con_modelo or p["tiene_modelo"])
    ]

    if not mostrar:
        st.info("No hay partidos con los filtros seleccionados.")
        st.stop()

    # Agrupar por fecha
    from itertools import groupby
    mostrar_sorted = sorted(mostrar, key=lambda x: x["fecha"])

    for fecha, grupo_iter in groupby(mostrar_sorted, key=lambda x: x["fecha"]):
        partidos_fecha = list(grupo_iter)
        fd = date.fromisoformat(fecha)
        if fd == date.today():
            st.markdown(f"### Hoy — {fd.strftime('%d %b %Y')}")
        else:
            st.markdown(f"### {fd.strftime('%A %d %b %Y').capitalize()}")

        for p in partidos_fecha:
            col_info, col_match, col_btn = st.columns([1.2, 2.5, 1.3])

            estado_tag = {
                "jugado":  '<span class="tag tag-jugado">Jugado</span>',
                "hoy":     '<span class="tag tag-hoy">En curso / Hoy</span>',
                "proximo": '<span class="tag tag-proximo">Próximo</span>',
            }[p["estado"]]

            with col_info:
                st.markdown(f'Grupo **{p["grupo"]}**<br>{estado_tag}<br><small style="color:#888">{p["sede"]}</small>', unsafe_allow_html=True)

            with col_match:
                if p["resultado"]:
                    gh, ga = p["resultado"]
                    st.markdown(
                        f'<div style="text-align:center;padding:8px 0">'
                        f'<span style="font-size:1rem;font-weight:500">{p["local"]}</span>'
                        f'&nbsp;&nbsp;<span class="match-score">{gh} — {ga}</span>&nbsp;&nbsp;'
                        f'<span style="font-size:1rem;font-weight:500">{p["visitante"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div style="text-align:center;padding:8px 0">'
                        f'<span style="font-size:1rem;font-weight:500">{p["local"]}</span>'
                        f'&nbsp;&nbsp;<span style="font-size:1.1rem;color:#aaa">vs</span>&nbsp;&nbsp;'
                        f'<span style="font-size:1rem;font-weight:500">{p["visitante"]}</span>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            with col_btn:
                if p["tiene_modelo"]:
                    lbl = "Ver predicción" if not p["resultado"] else "Ver retro-análisis"
                    if st.button(lbl, key=f"btn_{p['fecha']}_{p['local']}_{p['visitante']}"):
                        st.session_state["partido_sel"] = p
                        st.session_state["vista_override"] = True
                        st.rerun()
                else:
                    st.caption("Sin datos")

        st.markdown("---")

# ═════════════════════════════════════════════════════════════
#  PANEL DE ANÁLISIS (desde fixture o sidebar)
# ═════════════════════════════════════════════════════════════
def mostrar_analisis(home, away, momios, stake, resultado_real=None):
    result = predictor.analizar(home, away, momios=momios, stake=stake, mostrar=False)
    mk = result["markets"]
    ev = result["ev"]
    lh, la = result["lambda_h"], result["lambda_a"]

    # Cabecera
    if resultado_real:
        gh, ga = resultado_real
        ganador = home if gh > ga else (away if ga > gh else "Empate")
        pred_ganador = home if mk["1x2"]["local"] > mk["1x2"]["visitante"] and mk["1x2"]["local"] > mk["1x2"]["empate"] \
                       else (away if mk["1x2"]["visitante"] > mk["1x2"]["empate"] else "Empate")
        acierto = "Predicción acertada" if ganador == pred_ganador else f"Ganó: {ganador}"
        marcador_pred = list(mk["correct_score"].keys())[0]
        marcador_real = f"{gh}-{ga}"
        prob_real = mk["correct_score"].get(marcador_real, 0)

        st.markdown(f"## {home}  {gh} — {ga}  {away}  ·  Retro-análisis")
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Resultado real", marcador_real)
        col_r2.metric("Marcador predicho", marcador_pred)
        col_r3.metric("Prob. del marcador real", f"{prob_real:.2f}%")
        color_av = "normal" if ganador == pred_ganador else "inverse"
        st.metric("Resultado del modelo", acierto, delta=f"Predijo: {pred_ganador}", delta_color=color_av)
        st.markdown("---")
    else:
        st.markdown(f"## {home}  vs  {away}")

    ovr = round((1/momios.get('local',2)+1/momios.get('empate',3)+1/momios.get('visitante',3.5)-1)*100,1)
    st.caption(f"λ {home}: **{lh}** · λ {away}: **{la}** · Total esperado: **{round(lh+la,2)}** goles · Overround: **{ovr}%**")

    # ── Tabla de probabilidades puras + momio justo
    import pandas as _pd

    def _fair(p): return round(100/p, 2) if p > 0 else 0
    def _color_prob(v):
        try:
            val = float(v.replace("%",""))
            if val >= 60: return "background:#d1e7dd;color:#0f5132;font-weight:700"
            if val >= 40: return "background:#fff3cd;color:#664d03;font-weight:600"
        except: pass
        return ""

    mercados_prob = [
        (f"🏠 {home} gana",        mk["1x2"]["local"]),
        ("🤝 Empate",               mk["1x2"]["empate"]),
        (f"✈️ {away} gana",        mk["1x2"]["visitante"]),
        ("⚽ Over 2.5 goles",       mk["over_under"]["over_2.5"]),
        ("⚽ Under 2.5 goles",      mk["over_under"]["under_2.5"]),
        ("⚽ Over 1.5 goles",       mk["over_under"]["over_1.5"]),
        ("⚽ Under 1.5 goles",      mk["over_under"]["under_1.5"]),
        ("🎯 Ambos anotan (Sí)",    mk["btts"]["si"]),
        ("🎯 Ambos anotan (No)",    mk["btts"]["no"]),
        (f"🔵 {home} o Empate",     mk["doble_chance"]["1X"]),
        (f"🔴 {away} o Empate",     mk["doble_chance"]["X2"]),
        (f"⚡ {home} o {away}",     mk["doble_chance"]["12"]),
    ]

    rows_prob = [{"Mercado": n, "P. Modelo": f"{p}%",
                  "Momio justo": f"{_fair(p)}",
                  "¿Cuándo apostar?": f"Si Playdoit da MÁS de {_fair(p)} → 🟢 Valor"}
                 for n, p in mercados_prob]

    st.markdown("---")
    st.markdown("#### Probabilidades del modelo")
    st.caption("**Momio justo** = el mínimo que debe dar Playdoit para que haya valor. Si el momio real es **mayor** → hay EV positivo.")
    st.dataframe(
        _pd.DataFrame(rows_prob).style.map(_color_prob, subset=["P. Modelo"]),
        use_container_width=True, hide_index=True,
    )
    st.markdown("---")

    # Métricas 1X2
    c1,c2,c3,c4,c5 = st.columns(5)
    ph, pd_, pa = mk["1x2"]["local"], mk["1x2"]["empate"], mk["1x2"]["visitante"]
    with c1: st.markdown(f'<div class="metric-card"><div class="metric-lbl">P({home})</div><div class="metric-val">{ph}%</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><div class="metric-lbl">P(Empate)</div><div class="metric-val">{pd_}%</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><div class="metric-lbl">P({away})</div><div class="metric-val">{pa}%</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><div class="metric-lbl">Over 2.5</div><div class="metric-val">{mk["over_under"]["over_2.5"]}%</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="metric-card"><div class="metric-lbl">BTTS sí</div><div class="metric-val">{mk["btts"]["si"]}%</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_m, col_r = st.columns([1.2,1.2,1.6])

    with col_l:
        st.markdown("#### 1X2")
        fig = go.Figure(go.Pie(
            labels=[home,"Empate",away], values=[ph,pd_,pa], hole=0.55,
            marker_colors=["#4361ee","#adb5bd","#f72585"],
            textinfo="label+percent", hovertemplate="%{label}: %{value}%<extra></extra>",
        ))
        fig.update_layout(margin=dict(t=10,b=10,l=0,r=0), height=240, showlegend=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col_m:
        st.markdown("#### Goles exactos")
        ge = mk["goles_exactos"]
        fig2 = go.Figure(go.Bar(
            x=[f"{k}G" for k in ge], y=list(ge.values()),
            marker_color=["#4361ee" if i<=2 else "#adb5bd" for i in range(len(ge))],
            text=[f"{v}%" for v in ge.values()], textposition="outside",
        ))
        fig2.update_layout(margin=dict(t=10,b=10,l=0,r=0), height=240,
                           yaxis=dict(showgrid=False,showticklabels=False),
                           paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

    with col_r:
        st.markdown("#### Valor esperado")
        if ev:
            ev_df = pd.DataFrame([
                {"Mercado": k.upper().replace("_"," "), "EV": v["ev_$"], "Señal": v["señal"]}
                for k,v in ev.items()
            ]).sort_values("EV", ascending=True)
            colors = ["#198754" if x>0 else "#dc3545" for x in ev_df["EV"]]
            fig3 = go.Figure(go.Bar(
                x=ev_df["EV"], y=ev_df["Mercado"], orientation="h",
                marker_color=colors,
                text=[f"${v:+.2f}" for v in ev_df["EV"]], textposition="outside",
            ))
            fig3.add_vline(x=0, line_width=1, line_color="gray")
            fig3.update_layout(margin=dict(t=10,b=10,l=0,r=40), height=240,
                               xaxis=dict(showgrid=False,showticklabels=False),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Agrega momios para ver EV.")

    st.markdown("---")

    # Heatmap + mercados
    col_hm, col_mk = st.columns([1.6,1])
    with col_hm:
        st.markdown("#### Heatmap marcadores")
        max_g=5
        z = np.zeros((max_g+1,max_g+1))
        for i in range(max_g+1):
            for j in range(max_g+1):
                z[i][j] = mk["correct_score"].get(f"{i}-{j}", 0)
        # Marca el resultado real si existe
        annotations = []
        if resultado_real:
            gh, ga = resultado_real
            if gh <= max_g and ga <= max_g:
                annotations.append(dict(x=f"{away} {ga}", y=f"{home} {gh}",
                    text="REAL", showarrow=False,
                    font=dict(color="white", size=10, family="Arial Black")))
        fig_hm = go.Figure(go.Heatmap(
            z=z,
            x=[f"{away} {j}" for j in range(max_g+1)],
            y=[f"{home} {i}" for i in range(max_g+1)],
            colorscale="Blues",
            text=[[f"{z[i][j]:.2f}%" for j in range(max_g+1)] for i in range(max_g+1)],
            texttemplate="%{text}", textfont={"size":11}, showscale=False,
        ))
        if annotations:
            fig_hm.update_layout(annotations=annotations)
        fig_hm.update_layout(height=300, margin=dict(t=20,b=20,l=0,r=0),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hm, use_container_width=True)
        if resultado_real:
            st.caption("El marcador real está marcado en el heatmap.")

    with col_mk:
        st.markdown("#### Mercados clave")
        ou = mk["over_under"]; dc = mk["doble_chance"]; cs = mk["clean_sheet"]
        datos = {
            f"Over 2.5": ou["over_2.5"],
            f"Under 2.5": ou["under_2.5"],
            f"BTTS Sí": mk["btts"]["si"],
            f"BTTS No": mk["btts"]["no"],
            f"DC 1X": dc["1X"], f"DC X2": dc["X2"],
            f"{home} CS": cs["local_cs"], f"{away} CS": cs["visita_cs"],
        }
        fig_mk = go.Figure(go.Bar(
            x=list(datos.values()), y=list(datos.keys()), orientation="h",
            marker_color=["#4361ee","#adb5bd","#4cc9f0","#adb5bd",
                          "#f72585","#f72585","#4361ee","#f72585"],
            text=[f"{v}%" for v in datos.values()], textposition="outside",
        ))
        fig_mk.update_layout(height=300, margin=dict(t=20,b=20,l=0,r=40),
                             xaxis=dict(range=[0,110], showgrid=False, showticklabels=False),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_mk, use_container_width=True)

    # ── Tendencias y sugerencias (estilo Betmines)
    st.markdown("---")
    st.markdown("### Tendencias y sugerencias")
    try:
        from team_history import get_match_report

        rep_full = get_match_report(home, away)
        ht = rep_full["home_trends"]
        at = rep_full["away_trends"]
        hl = rep_full["home_local_trends"]
        av = rep_full["away_visit_trends"]

        # ── Sugerencias del partido
        home_sugg = [dict(s, desc=f"🏠 " + home + ": " + s["desc"]) for s in rep_full["home_suggestions"][:3]]
        away_sugg = [dict(s, desc=f"✈️ " + away + ": " + s["desc"]) for s in rep_full["away_suggestions"][:3]]
        all_sugg = rep_full["match_suggestions"] + home_sugg + away_sugg

        if all_sugg:
            st.markdown("#### 💡 Sugerencias automáticas")
            for s in sorted(all_sugg, key=lambda x: x["fuerza"], reverse=True)[:8]:
                stars = "⭐" * s["fuerza"]
                color = "#d1e7dd" if s["fuerza"] == 3 else "#fff3cd" if s["fuerza"] == 2 else "#f8f9fa"
                txt_color = "#0f5132" if s["fuerza"] == 3 else "#664d03" if s["fuerza"] == 2 else "#495057"
                st.markdown(
                    f'<div style="background:{color};color:{txt_color};padding:8px 14px;'
                    f'border-radius:8px;margin-bottom:6px;font-size:14px">'
                    f'{stars} <b>[{s["mercado"]}]</b> {s["desc"]}</div>',
                    unsafe_allow_html=True
                )

        st.markdown("---")

        # ── Comparativa de tendencias
        st.markdown("#### 📊 Comparativa de tendencias (últimos 10 partidos)")
        col_t1, col_t2, col_t3 = st.columns([1,0.3,1])

        import pandas as _pd3
        mapa_r = {'V':'victorias','E':'empates','D':'derrotas'}
        h_racha_txt = f"{ht.get('racha_n',0)} {mapa_r.get(ht.get('racha_tipo','V'),'')}"
        a_racha_txt = f"{at.get('racha_n',0)} {mapa_r.get(at.get('racha_tipo','V'),'')}"
        df_cmp = _pd3.DataFrame([
            [f"{ht.get('win_%',0)}%",     'Victorias %',        f"{at.get('win_%',0)}%"],
            [f"{ht.get('over_2.5_%',0)}%",'Over 2.5 %',         f"{at.get('over_2.5_%',0)}%"],
            [f"{ht.get('over_1.5_%',0)}%",'Over 1.5 %',         f"{at.get('over_1.5_%',0)}%"],
            [f"{ht.get('btts_%',0)}%",    'BTTS Sí %',          f"{at.get('btts_%',0)}%"],
            [f"{ht.get('cs_%',0)}%",      'Clean Sheet %',      f"{at.get('cs_%',0)}%"],
            [f"{ht.get('scored_%',0)}%",  'Siempre marca %',    f"{at.get('scored_%',0)}%"],
            [str(ht.get('avg_gf',0)),     'Prom. GF',           str(at.get('avg_gf',0))],
            [str(ht.get('avg_gc',0)),     'Prom. GC',           str(at.get('avg_gc',0))],
            [str(ht.get('avg_total',0)),  'Prom. total/partido',str(at.get('avg_total',0))],
            [h_racha_txt,                 'Racha actual',       a_racha_txt],
            [str(ht.get('sin_perder',0)), 'Sin perder',         str(at.get('sin_perder',0))],
        ], columns=[home, 'Estadística', away])
        st.dataframe(df_cmp, use_container_width=True, hide_index=True)

    except Exception as e:
        st.caption(f"Tendencias no disponibles: {e}")

    # ── Historial de equipos
    st.markdown("---")
    st.markdown("### Historial de partidos")
    col_h1, col_h2 = st.columns(2)
    try:
        from team_history import get_full_report
        import pandas as _pd2

        def _render_history(equipo, col):
            with col:
                st.markdown(f'**{equipo}**')
                from team_history import get_team_matches, compute_stats
                todos   = get_team_matches(equipo, 10)
                locales = [m for m in get_team_matches(equipo, 30) if m['condicion'] == 'Local'][:5]
                visitas = [m for m in get_team_matches(equipo, 30) if m['condicion'] == 'Visitante'][:5]
                def _rows(lst):
                    return [{'Año': m['año'], 'Rival': m['rival'],
                             'Cond.': '🏠' if m['condicion']=='Local' else '✈️',
                             'Marcador': m['marcador'],
                             'Res.': ('✅ V' if m['resultado']=='V' else '🟡 E' if m['resultado']=='E' else '❌ D'),
                             'Goleadores': m['goleadores'][:35] if m['goleadores'] != '—' else '—'}
                            for m in lst]
                def _stats(lst):
                    s = compute_stats(lst)
                    if not s: return
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric('V/E/D', f"{s['victorias']}/{s['empates']}/{s['derrotas']}")
                    c2.metric('Prom. GF', s['promedio_gf'])
                    c3.metric('Prom. GC', s['promedio_gc'])
                    c4.metric('Total/ptdo', s['promedio_total'])
                t1, t2, t3 = st.tabs([
                    f'📋 Últimos {len(todos)}',
                    f'🏠 Local ({len(locales)})',
                    f'✈️ Visitante ({len(visitas)})'
                ])
                with t1:
                    _stats(todos)
                    if todos: st.dataframe(_pd2.DataFrame(_rows(todos)), use_container_width=True, hide_index=True, height=300)
                with t2:
                    _stats(locales)
                    if locales: st.dataframe(_pd2.DataFrame(_rows(locales)), use_container_width=True, hide_index=True)
                    else: st.caption('Sin datos como local')
                with t3:
                    _stats(visitas)
                    if visitas: st.dataframe(_pd2.DataFrame(_rows(visitas)), use_container_width=True, hide_index=True)
                    else: st.caption('Sin datos como visitante')

        _render_history(home, col_h1)
        _render_history(away, col_h2)
    except Exception as e:
        st.caption(f"Historial no disponible: {e}")



# Desde fixture (botón de partido)
if st.session_state.get("vista_override") and "partido_sel" in st.session_state:
    p = st.session_state["partido_sel"]
    h_name = TEAM_MAP.get(p["local"], p["local"])
    a_name = TEAM_MAP.get(p["visitante"], p["visitante"])

    if st.button("← Volver al fixture"):
        st.session_state.pop("partido_sel", None)
        st.session_state.pop("vista_override", None)
        st.rerun()
    else:
        # Intentar cargar momios reales desde Odds API
        momios_live = None
        if ODDS_API_KEY:
            try:
                from alerts import obtener_momios
                from monte_carlo import EN_TO_ES
                ES_TO_EN = {v: k for k, v in EN_TO_ES.items()}
                h_en = ES_TO_EN.get(h_name, h_name)
                a_en = ES_TO_EN.get(a_name, a_name)
                partidos_odds = obtener_momios(ODDS_API_KEY)
                for po in partidos_odds:
                    ph = po["local"].lower()
                    pa = po["visitante"].lower()
                    h_match = h_en.lower() in ph or ph in h_en.lower()
                    a_match = a_en.lower() in pa or pa in a_en.lower()
                    h_match2 = h_en.lower() in pa or pa in h_en.lower()
                    a_match2 = a_en.lower() in ph or ph in a_en.lower()
                    if (h_match and a_match) or (h_match2 and a_match2):
                        momios_live = {
                            "local":     po.get("odd_h") or 2.0,
                            "empate":    po.get("odd_d") or 3.2,
                            "visitante": po.get("odd_a") or 3.6,
                            "over_2.5":  po.get("over_2.5") or 1.90,
                            "under_2.5": po.get("under_2.5") or 1.95,
                            "over_1.5":  po.get("over_1.5") or 1.35,
                            "btts_si":   1.80,
                            "btts_no":   2.00,
                            "dc_1X":     1.30,
                            "dc_X2":     1.40,
                        }
                        break
            except Exception as e:
                pass

        momios_default = momios_live or {"local":2.0,"empate":3.2,"visitante":3.6,
                          "over_2.5":1.90,"under_2.5":1.95,
                          "btts_si":1.75,"btts_no":2.05,"dc_1X":1.30,"dc_X2":1.40}

        if momios_live:
            st.success(f"Momios en vivo cargados · Local: {momios_live['local']} · Empate: {momios_live['empate']} · Visitante: {momios_live['visitante']}")
        else:
            st.info("Momios por defecto — sin datos en vivo para este partido")

        mostrar_analisis(h_name, a_name, momios_default, stake=100,
                         resultado_real=p.get("resultado"))

# Desde sidebar
elif vista == "Analizador de partido":
    if st.session_state.get("analizador_ready", False):
        momios = {"local":odd_h,"empate":odd_d,"visitante":odd_a,
                  "over_2.5":odd_o25,"under_2.5":odd_u25,"over_1.5":odd_o15,
                  "btts_si":odd_btts_si,"btts_no":odd_btts_no,"dc_1X":odd_dc1X,"dc_X2":odd_dcX2}
        mostrar_analisis(home, away, momios, stake)
    else:
        st.markdown("## Analizador de partido")
        st.info("👈 Selecciona los equipos, ingresa los momios de Playdoit y presiona **Analizar partido**")
        st.markdown("""
        **¿Cómo usar?**
        1. Elige el equipo **Local** y **Visitante**
        2. Abre Playdoit y copia los momios de cada mercado
        3. Ingresa los momios en el panel izquierdo
        4. Presiona **Analizar partido**
        5. El sistema te dice qué mercados tienen valor real
        """)

st.markdown("<br><center><small>Modelo de Poisson · Datos estadísticos históricos · No garantiza resultados</small></center>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════
#  SECCIÓN MONTE CARLO (inyectada al sidebar)
# ═════════════════════════════════════════════════════════════
# Esta sección se agrega como nueva opción de vista en el sidebar

# ═════════════════════════════════════════════════════════════
#  MONTE CARLO
# ═════════════════════════════════════════════════════════════
if vista == "Monte Carlo" and not st.session_state.get("vista_override"):
    from monte_carlo import correr_montecarlo, GRUPOS, FORMA_RECIENTE
    import plotly.express as px

    st.markdown("# Simulación Monte Carlo")
    st.caption("Simula el torneo completo N veces y calcula probabilidades reales por ronda.")

    col1, col2, col3 = st.columns(3)
    with col1:
        n_sims = st.select_slider("Simulaciones", [1000,5000,10000,25000,50000], value=10000)
    with col2:
        usar_forma = st.toggle("Forma reciente", value=True)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        correr = st.button("Simular torneo", type="primary", use_container_width=True)

    st.markdown("### Ajustes por bajas (opcional)")
    col_a, col_b = st.columns(2)
    equipos_mc = sorted(set(e for g in GRUPOS.values() for e in g))
    ajustes = {}
    with col_a:
        eq_baja = st.selectbox("Equipo con baja", ["Ninguno"] + equipos_mc)
        if eq_baja != "Ninguno":
            impacto = st.slider("Impacto en ataque", 0.50, 1.00, 0.85, 0.05,
                                help="0.80 = pierde 20% de ataque (baja de estrella)")
            ajustes = {eq_baja: {"ataque": impacto}}
    with col_b:
        if ajustes:
            eq = list(ajustes.keys())[0]
            factor = ajustes[eq]["ataque"]
            st.metric("Reducción ataque", f"{(1-factor)*100:.0f}%",
                      delta=f"{eq}", delta_color="inverse")

    if correr or "mc_df" in st.session_state:
        if correr:
            with st.spinner(f"Corriendo {n_sims:,} simulaciones..."):
                from monte_carlo import correr_montecarlo
                df_mc = correr_montecarlo(n_sims=n_sims, ajustes=ajustes or None,
                                          usar_forma=usar_forma, seed=None)
            st.session_state["mc_df"] = df_mc
        else:
            df_mc = st.session_state["mc_df"]

        st.markdown("---")
        # Métricas top 3
        top3 = df_mc.head(3)
        c1,c2,c3 = st.columns(3)
        for col, (_, row) in zip([c1,c2,c3], top3.iterrows()):
            col.markdown(f'<div class="metric-card"><div class="metric-lbl">#{_ +1} {row["equipo"]}</div>'
                         f'<div class="metric-val">{row["campeon_%"]}%</div>'
                         f'<div class="metric-lbl">de ganar el Mundial</div></div>',
                         unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_bar, col_tbl = st.columns([1.6, 1])

        with col_bar:
            st.markdown("#### Probabilidad de ser campeón")
            top16 = df_mc.head(16)
            fig = px.bar(top16, x="campeon_%", y="equipo", orientation="h",
                         color="campeon_%", color_continuous_scale="Blues",
                         text="campeon_%")
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(height=460, coloraxis_showscale=False,
                              xaxis=dict(showgrid=False, showticklabels=False),
                              yaxis=dict(categoryorder="total ascending"),
                              margin=dict(t=10,b=10,l=0,r=40),
                              paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col_tbl:
            st.markdown("#### Tabla completa")
            st.dataframe(
                df_mc[["equipo","pasa_grupos_%","sf_%","final_%","campeon_%"]].rename(columns={
                    "equipo":"Equipo","pasa_grupos_%":"Grupos",
                    "sf_%":"Semis","final_%":"Final","campeon_%":"Campeón %"
                }),
                use_container_width=True, hide_index=True, height=460,
            )

        # Burbujas ronda a ronda
        st.markdown("#### Probabilidades por ronda (top 12)")
        top12 = df_mc.head(12)
        rondas = ["pasa_grupos_%","r16_%","qf_%","sf_%","final_%","campeon_%"]
        labels = ["Grupos","R16","Cuartos","Semis","Final","Campeón"]
        fig2 = go.Figure()
        colors = px.colors.qualitative.Set2
        for i, (_, row) in enumerate(top12.iterrows()):
            fig2.add_trace(go.Scatter(
                x=labels, y=[row[r] for r in rondas],
                mode="lines+markers", name=row["equipo"],
                line=dict(color=colors[i % len(colors)], width=2),
                marker=dict(size=8),
            ))
        fig2.update_layout(height=360, margin=dict(t=10,b=10,l=0,r=0),
                           yaxis=dict(title="Probabilidad %"),
                           paper_bgcolor="rgba(0,0,0,0)",
                           plot_bgcolor="rgba(0,0,0,0)",
                           legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig2, use_container_width=True)


# ═════════════════════════════════════════════════════════════
#  ALERTAS EV+
# ═════════════════════════════════════════════════════════════
elif vista == "Alertas EV+" and not st.session_state.get("vista_override"):
    from alerts import obtener_momios, analizar_oportunidades

    st.markdown("# Alertas de Valor Esperado")
    st.caption("Detecta automáticamente mercados con EV positivo en los partidos de hoy.")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        stake_a = st.number_input("Apuesta ($)", 1, 5000, 100, 10)
    with col2:
        umbral_ev = st.number_input("EV mínimo ($)", 0.0, 100.0, 5.0, 1.0)
    with col3:
        umbral_edge = st.number_input("Edge mínimo (%)", 0.0, 20.0, 2.5, 0.5)
    with col4:
        odds_key = st.text_input("Odds API key", placeholder="gratis en the-odds-api.com",
                                  type="password")
        st.caption("Sin key usa momios demo")

    if st.button("Escanear oportunidades", type="primary", use_container_width=False):
        with st.spinner("Analizando mercados..."):
            partidos = obtener_momios(odds_key or None)
            ops = analizar_oportunidades(partidos, stake_a, umbral_ev, umbral_edge)
        st.session_state["alertas_ops"] = ops
        st.session_state["alertas_partidos"] = partidos

    if "alertas_ops" in st.session_state:
        ops = st.session_state["alertas_ops"]
        partidos_escan = st.session_state.get("alertas_partidos", [])

        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Partidos analizados", len(partidos_escan))
        c2.metric("Oportunidades EV+", len(ops))
        if ops:
            c3.metric("Mejor EV", f"${max(o['ev_$'] for o in ops):+.2f}")
            c4.metric("Mejor edge", f"+{max(o['edge_%'] for o in ops):.1f}%")

        if ops:
            st.markdown("---")
            st.markdown("### Oportunidades detectadas")
            for o in ops:
                ev_color = "#198754"
                st.markdown(
                    f'<div style="border:0.5px solid var(--color-border-tertiary);'
                    f'border-radius:10px;padding:14px 18px;margin-bottom:10px;">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center">'
                    f'<div><span style="font-weight:500;font-size:15px">{o["partido"]}</span>'
                    f'&nbsp;&nbsp;<span style="background:#d1e7dd;color:#0f5132;'
                    f'padding:2px 10px;border-radius:10px;font-size:12px;font-weight:600">EV+</span></div>'
                    f'<span style="font-size:1.4rem;font-weight:700;color:{ev_color}">'
                    f'${o["ev_$"]:+.2f}</span></div>'
                    f'<div style="margin-top:8px;font-size:13px;color:var(--color-text-secondary)">'
                    f'Mercado: <b>{o["mercado"]}</b> @ {o["odd"]} &nbsp;·&nbsp; '
                    f'P.Modelo: {o["prob_%"]:.1f}% &nbsp;·&nbsp; '
                    f'Implícita: {o["implied_%"]:.1f}% &nbsp;·&nbsp; '
                    f'Edge: <b>+{o["edge_%"]:.1f}%</b> &nbsp;·&nbsp; '
                    f'ROI: <b>+{o["roi_%"]:.1f}%</b></div></div>',
                    unsafe_allow_html=True
                )

            # Configurar alertas
            with st.expander("Configurar alertas automáticas"):
                col_t, col_e = st.columns(2)
                with col_t:
                    st.markdown("**Telegram**")
                    tg_token = st.text_input("Bot token", type="password", key="tg_tok")
                    tg_chat  = st.text_input("Chat ID", key="tg_chat")
                    if st.button("Probar Telegram") and tg_token and tg_chat:
                        from alerts import enviar_telegram
                        ok = enviar_telegram(tg_token, tg_chat, "Test de alerta Mundial 2026")
                        st.success("Enviado") if ok else st.error("Error")
                with col_e:
                    st.markdown("**Email (Gmail)**")
                    em_from = st.text_input("Tu Gmail", key="em_from")
                    em_pass = st.text_input("App password", type="password", key="em_pass")
                    em_to   = st.text_input("Enviar a", key="em_to")
        else:
            st.info(f"Sin oportunidades con EV≥${umbral_ev} y edge≥{umbral_edge}% ahora mismo.")



# ═════════════════════════════════════════════════════════════
#  SHARP MONEY — MOVIMIENTO DE LÍNEAS PINNACLE
# ═════════════════════════════════════════════════════════════
elif vista == "Sharp Money" and not st.session_state.get("vista_override"):
    from sharp_money import sync_and_analyze, get_movement, init_db
    init_db()

    st.markdown("# 💰 Sharp Money — Movimiento de líneas")
    st.caption("Rastreamos los momios de **Pinnacle** — la casa de referencia de los apostadores profesionales. "
               "Cuando el momio baja con poco volumen público → hay dinero sharp entrando.")

    col_k, col_r = st.columns([2,1])
    with col_k:
        odds_key = st.text_input("Odds API Key", value="f53632176b081239f863d6b9be2ebe1b",
                                  type="password", key="sharp_key")
    with col_r:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄 Actualizar líneas Pinnacle", type="primary")

    if refresh or "sharp_data" not in st.session_state:
        if odds_key:
            with st.spinner("Descargando líneas de Pinnacle..."):
                try:
                    data = sync_and_analyze(odds_key)
                    st.session_state["sharp_data"] = data
                    st.success(f"✓ {len(data)} partidos actualizados")
                except Exception as e:
                    st.error(f"Error: {e}")
                    data = []
        else:
            data = []
    else:
        data = st.session_state.get("sharp_data", [])

    if data:
        st.markdown("---")

        # ── Señales sharp detectadas
        sharps = [p for p in data if p.get("señal_sharp","").startswith("💰")]
        estables = [p for p in data if p.get("señal_sharp","").startswith("➡️")]
        publico = [p for p in data if p.get("señal_sharp","").startswith("👥")]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Partidos monitoreados", len(data))
        c2.metric("🔴 Señales sharp", len(sharps))
        c3.metric("👥 Movimiento público", len(publico))
        c4.metric("➡️ Sin movimiento", len(estables))

        st.markdown("---")

        # ── Tabla de momios actuales con señales
        st.markdown("### Momios Pinnacle actuales")
        st.caption("Pinnacle es la casa que menos margen tiene y donde apuestan los profesionales. "
                   "Sus líneas son el estándar de referencia del mercado.")

        rows_sharp = []
        for p in sorted(data, key=lambda x: x.get("odd_h", 99)):
            movs = p.get("movimientos", [])
            mov_str = " | ".join([m["señal"] for m in movs]) if movs else "Sin cambios"
            señal = p.get("señal_sharp", "—")

            rows_sharp.append({
                "Partido":     p["partido"],
                "Local (H)":   f"{p.get('odd_h','—')}",
                "Empate (D)":  f"{p.get('odd_d','—')}",
                "Visitante (A)": f"{p.get('odd_a','—')}",
                "Movimiento":  mov_str,
                "Señal":       señal,
            })

        df_sharp = pd.DataFrame(rows_sharp)

        def _color_senal(val):
            if "💰" in str(val): return "background:#d1e7dd;color:#0f5132;font-weight:700"
            if "👥" in str(val): return "background:#fff3cd;color:#664d03"
            return ""

        st.dataframe(
            df_sharp.style.map(_color_senal, subset=["Señal"]),
            use_container_width=True, hide_index=True, height=400
        )

        # ── Detalle de señales sharp
        if sharps:
            st.markdown("---")
            st.markdown("### 🔴 Partidos con dinero sharp detectado")
            for p in sharps:
                with st.expander(f"**{p['partido']}** — {p['señal_sharp']}"):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Momio local", p.get("odd_h","—"))
                    c2.metric("Momio empate", p.get("odd_d","—"))
                    c3.metric("Momio visitante", p.get("odd_a","—"))

                    if p.get("movimientos"):
                        for m in p["movimientos"]:
                            color = "#d1e7dd" if "Sharp" in m["señal"] else "#fff3cd"
                            txt = "#0f5132" if "Sharp" in m["señal"] else "#664d03"
                            st.markdown(
                                f'<div style="background:{color};color:{txt};padding:8px 14px;'
                                f'border-radius:8px;margin:4px 0;font-size:14px">'
                                f'{m["señal"]} — Momio {m["mercado"]} {m["direccion"]} '
                                f'{abs(m["cambio"]):.3f} puntos</div>',
                                unsafe_allow_html=True
                            )
                    if p.get("snapshots", 0) < 2:
                        st.info("Necesita al menos 2 snapshots para detectar movimiento. "
                               "Actualiza las líneas en 30-60 min.")

        # ── Explicación
        st.markdown("---")
        with st.expander("ℹ️ ¿Cómo interpretar el movimiento de líneas?"):
            st.markdown("""
            **Momio baja** → más dinero entrando en ese resultado → si es con poco volumen público, son sharps

            **Momio sube** → la casa está recibiendo poco dinero en ese lado → pueden ser sharps al contrario

            **Señales clave:**
            - 🔴 **Sharp**: momio bajó significativamente sin que el público lo justifique
            - 👥 **Público**: momio sube porque el público apuesta al contrario
            - ➡️ **Estable**: sin movimiento significativo

            **Pinnacle como referencia:**
            Pinnacle acepta apuestas grandes y no limita a los ganadores. Sus líneas se consideran
            el precio "justo" del mercado. Si Pinnacle mueve una línea, hay una razón.

            **Estrategia sharp:**
            Busca partidos donde Pinnacle tenga un momio significativamente mayor que Playdoit
            en el mismo resultado → ahí está el valor.
            """)

# ═════════════════════════════════════════════════════════════
#  BANKROLL TRACKER
# ═════════════════════════════════════════════════════════════
elif vista == "Bankroll" and not st.session_state.get("vista_override"):
    from bankroll import (registrar_apuesta, resolver_apuesta,
                           listar_apuestas, reporte_pnl, kelly, init_db)
    init_db()

    st.markdown("# Tracker de Bankroll")
    st.caption("Registra tus apuestas, calcula P&L real y compara con el EV esperado.")

    bankroll_ini = st.number_input("Bankroll inicial ($)", 100, 100000, 1000, 100)

    stats = reporte_pnl(bankroll_ini)
    if "error" not in stats:
        c1,c2,c3,c4,c5 = st.columns(5)
        pnl_delta = "normal" if stats["pnl_$"] >= 0 else "inverse"
        c1.metric("Bankroll actual", f"${stats['bankroll_actual_$']:,.0f}",
                  delta=f"${stats['pnl_$']:+.2f}", delta_color=pnl_delta)
        c2.metric("ROI real", f"{stats['roi_%']:+.1f}%")
        c3.metric("Tasa de acierto", f"{stats['tasa_acierto_%']:.1f}%")
        c4.metric("P&L", f"${stats['pnl_$']:+.2f}")
        c5.metric("Racha", stats["racha_actual"])
        st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["Registrar apuesta", "Resolver pendientes", "Historial"])

    with tab1:
        st.markdown("#### Nueva apuesta")
        col1, col2 = st.columns(2)
        with col1:
            partido_n = st.text_input("Partido", placeholder="Brasil vs Marruecos")
            mercado_n = st.text_input("Mercado", placeholder="LOCAL / OVER 2.5 / BTTS SI")
            odd_n     = st.number_input("Momio decimal", 1.01, 50.0, 2.00, 0.05)
        with col2:
            stake_n   = st.number_input("Apuesta ($)", 1.0, 10000.0, 100.0, 10.0)
            prob_n    = st.number_input("Prob. modelo (%)", 0.0, 100.0, 50.0, 0.5)
            notas_n   = st.text_input("Notas", placeholder="opcional")

        # Kelly en tiempo real
        if prob_n > 0 and odd_n > 1.01:
            k = kelly(prob_n, odd_n, bankroll_ini)
            ev_n = k["ev_esperado_$"]
            kc = st.columns(4)
            kc[0].metric("EV esperado", f"${ev_n:+.2f}")
            kc[1].metric("Kelly recomendado", f"${k['apuesta_recomendada_$']:.2f}")
            kc[2].metric("Kelly %", f"{k['kelly_fraccion_%']:.2f}%")
            kc[3].metric("Máx 5% bankroll", f"${k['max_apuesta_$']:.2f}")

        if st.button("Registrar apuesta", type="primary"):
            if partido_n and mercado_n:
                from bankroll import reporte_pnl as rp
                ev_est = ev_n if prob_n > 0 else None
                nuevo_id = registrar_apuesta(partido_n, mercado_n, odd_n, stake_n,
                                              prob_n or None, ev_est, notas_n)
                st.success(f"Apuesta #{nuevo_id} registrada")
                st.rerun()
            else:
                st.warning("Completa partido y mercado")

    with tab2:
        pendientes = listar_apuestas(solo_pendientes=True)
        if pendientes.empty:
            st.info("Sin apuestas pendientes")
        else:
            for _, row in pendientes.iterrows():
                col_p, col_r = st.columns([3, 1])
                with col_p:
                    st.markdown(
                        f"**#{row['id']}** {row['partido']} — {row['mercado']} "
                        f"@ {row['odd']} · ${row['stake']:.0f}"
                        f"{'  (prob: '+str(row['prob_modelo'])+'%)' if row['prob_modelo'] else ''}"
                    )
                with col_r:
                    res = st.selectbox("", ["—","ganada","perdida","void"],
                                       key=f"res_{row['id']}")
                    if res != "—" and st.button("Guardar", key=f"save_{row['id']}"):
                        r = resolver_apuesta(int(row['id']), res)
                        st.success(f"P&L: ${r['ganancia']:+.2f}")
                        st.rerun()

    with tab3:
        hist = listar_apuestas()
        if hist.empty:
            st.info("Sin historial aún")
        else:
            def color_resultado(val):
                if val == "ganada":   return "background:#d1e7dd;color:#0f5132"
                if val == "perdida":  return "background:#f8d7da;color:#842029"
                if val == "pendiente":return "background:#fff3cd;color:#664d03"
                return ""
            cols_show = ["id","fecha","partido","mercado","odd","stake",
                         "prob_modelo","ev_esperado","resultado","retorno"]
            st.dataframe(
                hist[cols_show].style.map(color_resultado, subset=["resultado"]),
                use_container_width=True, hide_index=True,
            )
            if not hist[hist["resultado"]!="pendiente"].empty:
                resueltas = hist[hist["resultado"].isin(["ganada","perdida"])]
                resueltas = resueltas.copy()
                resueltas["ganancia"] = resueltas["retorno"] - resueltas["stake"]
                resueltas["cumPnL"]   = resueltas["ganancia"].cumsum()
                fig_pnl = go.Figure(go.Scatter(
                    x=list(range(1,len(resueltas)+1)),
                    y=resueltas["cumPnL"].tolist(),
                    mode="lines+markers",
                    line=dict(color="#4361ee",width=2),
                    fill="tozeroy",
                    fillcolor="rgba(67,97,238,0.1)",
                ))
                fig_pnl.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
                fig_pnl.update_layout(
                    height=260, title="P&L acumulado",
                    margin=dict(t=40,b=20,l=0,r=0),
                    xaxis=dict(title="Apuesta #"),
                    yaxis=dict(title="P&L ($)"),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_pnl, use_container_width=True)
