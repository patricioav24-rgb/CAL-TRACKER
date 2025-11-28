import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------------
st.set_page_config(page_title="CalisTracker Pro", page_icon="🏋️", layout="wide")

# Colores personalizados para cada ejercicio (puedes agregar más)
COLOR_MAP = {
    "Dominadas – Pronas": "#FF5733",  # Rojo/Naranja
    "Dominadas – Supinas": "#C70039", # Rojo oscuro
    "Fondos": "#33FF57",              # Verde
    "Flexiones": "#3357FF",           # Azul
    "Remo invertido": "#F333FF",      # Magenta
    "Otro": "#808080"                 # Gris
}

SHEET_NAME = "CalisTracker"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# -------------------------------------------------------
# FUNCIONES DE BACKEND
# -------------------------------------------------------
def get_client():
    """Conecta usando las credenciales en st.secrets."""
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_client()
    sh = client.open(SHEET_NAME)
    wks = sh.sheet1
    return wks

def ensure_header(wks):
    header = [
        "fecha", "ejercicio", "metodo", "total_sets",
        "reps_por_set", "total_volumen", "descanso", "notas"
    ]
    first = wks.row_values(1)
    if first != header:
        wks.clear()
        wks.insert_row(header, 1)

def load_data():
    """Carga los datos y convierte la fecha a datetime."""
    try:
        wks = open_sheet()
        ensure_header(wks)
        rows = wks.get_all_records()
        df = pd.DataFrame(rows)
        if not df.empty:
            df["fecha"] = pd.to_datetime(df["fecha"])
        return df
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# -------------------------------------------------------
# ESTADO DE LA SESIÓN
# -------------------------------------------------------
if "sets" not in st.session_state:
    st.session_state.sets = []
if "set_count" not in st.session_state:
    st.session_state.set_count = 0

# -------------------------------------------------------
# UI PRINCIPAL
# -------------------------------------------------------
st.title("🏋️ CalisTracker Pro")
st.markdown("---")

# Usamos pestañas para separar el registro del análisis
tab1, tab2 = st.tabs(["📝 Registrar Sesión", "📊 Dashboard y Análisis"])

# =======================================================
# TAB 1: REGISTRO
# =======================================================
with tab1:
    col_main_1, col_main_2 = st.columns([1, 2])

    with col_main_1:
        st.subheader("Configuración")
        today = datetime.now().strftime("%Y-%m-%d")
        st.info(f"📅 **Fecha:** {today}")
        
        ejercicio = st.selectbox("Ejercicio", list(COLOR_MAP.keys()))
        metodo = st.selectbox("Método", ["Volumen", "Series Libres", "Lastre"])
        
        descanso = st.slider("Descanso (seg)", 0, 180, 45, step=5)
        notas = st.text_area("Notas rápidas", height=68)

    with col_main_2:
        st.subheader("Ejecución")
        
        # Sistema de métricas en vivo
        m1, m2, m3 = st.columns(3)
        m1.metric("Sets Totales", st.session_state.set_count)
        current_vol = sum(st.session_state.sets)
        m2.metric("Volumen Actual", current_vol)
        last_rep = st.session_state.sets[-1] if st.session_state.sets else 0
        m3.metric("Última serie", f"{last_rep} reps")

        st.markdown("#### Añadir Serie")
        c_rep, c_btn = st.columns([2, 1])
        with c_rep:
            reps = st.number_input("Reps realizadas:", min_value=0, value=0, label_visibility="collapsed")
        with c_btn:
            if st.button("➕ Agregar", use_container_width=True):
                if reps > 0:
                    st.session_state.set_count += 1
                    st.session_state.sets.append(reps)
                    st.rerun() # Recarga para actualizar métricas al instante

        # Visualización de las series como "tags"
        if st.session_state.sets:
            st.write("Series realizadas:")
            sets_str = " - ".join([f"**{s}**" for s in st.session_state.sets])
            st.markdown(f"> {sets_str}")
        
        st.divider()
        
        # Botón de Guardado
        if st.button("💾 Guardar Entrenamiento", type="primary", use_container_width=True):
            if st.session_state.sets:
                try:
                    wks = open_sheet()
                    ensure_header(wks)
                    row = [
                        today, ejercicio, metodo,
                        len(st.session_state.sets),
                        ",".join(map(str, st.session_state.sets)),
                        sum(st.session_state.sets),
                        descanso,
                        notas
                    ]
                    wks.append_row(row)
                    st.success("✅ ¡Entrenamiento guardado!")
                    # Reset
                    st.session_state.sets = []
                    st.session_state.set_count = 0
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("⚠️ Agrega al menos una serie antes de guardar.")

# =======================================================
# TAB 2: DASHBOARD (Mejorado con Altair)
# =======================================================
with tab2:
    df = load_data()
    
    if df.empty:
        st.info("Aún no hay datos para mostrar análisis.")
    else:
        # --- PRECESAMIENTO DE DATOS ---
        # 1. Agrupar por SEMANA y EJERCICIO
        # 'W-MON' significa que la semana empieza el Lunes
        df['semana'] = df['fecha'].dt.to_period('W-MON').apply(lambda r: r.start_time)
        
        # Agrupación semanal: Suma de volumen por semana y ejercicio
        weekly_stats = df.groupby(['semana', 'ejercicio'])['total_volumen'].sum().reset_index()

        # --- SECCIÓN 1: PROGRESO SEMANAL ---
        st.subheader("📈 Evolución Semanal de Volumen")
        st.caption("Comparativa de volumen total acumulado por semana para cada ejercicio.")

        # Gráfico de líneas con puntos usando Altair
        chart_weekly = alt.Chart(weekly_stats).mark_line(point=True).encode(
            x=alt.X('semana:T', title='Semana', axis=alt.Axis(format='%d %b')),
            y=alt.Y('total_volumen:Q', title='Volumen Total (Reps)'),
            color=alt.Color('ejercicio:N', scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values()))),
            tooltip=['semana', 'ejercicio', 'total_volumen']
        ).properties(
            height=400
        ).interactive()

        st.altair_chart(chart_weekly, use_container_width=True)

        # --- SECCIÓN 2: DATOS FILTRADOS ---
        st.divider()
        st.subheader("🔎 Análisis Detallado")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            ejercicio_filter = st.multiselect("Filtrar Ejercicios", options=df['ejercicio'].unique(), default=df['ejercicio'].unique())
        
        # Filtrar DF
        df_filtered = df[df['ejercicio'].isin(ejercicio_filter)]
        
        # Gráfico de Barras Mensual con los filtros aplicados
        st.markdown("##### Volumen Acumulado (Filtrado)")
        
        bar_chart = alt.Chart(df_filtered).mark_bar().encode(
            x=alt.X('fecha:T', title='Fecha Sesión'),
            y=alt.Y('total_volumen:Q', title='Volumen'),
            color=alt.Color('ejercicio:N', legend=None, scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values()))),
            tooltip=['fecha', 'ejercicio', 'total_volumen', 'notas']
        ).properties(height=300)
        
        st.altair_chart(bar_chart, use_container_width=True)

        with st.expander("Ver tabla de datos completa"):
            st.dataframe(df_filtered.sort_values(by="fecha", ascending=False), use_container_width=True)
