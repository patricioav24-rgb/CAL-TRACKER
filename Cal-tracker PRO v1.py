import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------------
st.set_page_config(page_title="CalisTracker Pro", page_icon="📒", layout="wide")

# -------------------------------------------------------
# INYECCIÓN DE CSS (Estilo Pro / App Móvil)
# -------------------------------------------------------
def local_css():
    st.markdown("""
        <style>
        /* 1. Ocultar menú de hamburguesa superior y footer de Streamlit */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* 2. Reducir el espacio en blanco arriba (Padding) para que se vea más app */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        /* 3. Estilizar las MÉTRICAS (Tarjetas con fondo suave) */
        [data-testid="stMetric"] {
            background-color: #222222; /* Fondo oscuro tarjeta */
            border-radius: 10px;
            padding: 15px;
            border: 1px solid #333;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        }
        
        /* 4. Botones más estéticos y redondeados */
        .stButton > button {
            width: 100%;
            border-radius: 20px;
            font-weight: bold;
            border: none;
            transition: all 0.3s ease;
        }
        
        /* Efecto hover en botones (opcional) */
        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        /* 5. Pestañas (Tabs) más grandes y centradas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            border-radius: 5px;
            padding-left: 20px;
            padding-right: 20px;
            background-color: #1E1E1E;
        }
        </style>
        """, unsafe_allow_html=True)

# ¡IMPORTANTE! Llama a la función justo después de set_page_config
local_css()
# Mapeo de Colores Fijos por Ejercicio
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
# FUNCIONES DE BACKEND (Optimizadas para evitar Error 429)
# -------------------------------------------------------
def get_client():
    """Conecta usando las credenciales en st.secrets."""
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet_connection():
    """Abre la conexión con la hoja. Se mantiene en caché."""
    client = get_client()
    sh = client.open(SHEET_NAME)
    wks = sh.sheet1
    return wks

@st.cache_data(ttl=300)
def load_data():
    """
    Carga los datos y los guarda en memoria (caché) por 5 minutos.
    Esto evita saturar la API de Google (Error 429).
    """
    try:
        wks = open_sheet_connection()
        
        # Leemos todo de una vez
        rows = wks.get_all_records()
        
        # Si la hoja está vacía o es nueva, manejamos el error
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        
        # Convertir fecha a datetime si existe la columna
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"])
            
        return df
    except Exception as e:
        st.warning(f"No se pudo cargar el historial reciente (posible límite de API). Intenta en unos minutos. Error: {e}")
        return pd.DataFrame()

def ensure_header_initialization():
    """
    Función auxiliar para asegurar que existan cabeceras.
    Se debería ejecutar solo una vez o manualmente si la hoja es nueva.
    """
    try:
        wks = open_sheet_connection()
        header = ["fecha", "ejercicio", "metodo", "total_sets", "reps_por_set", "total_volumen", "descanso", "notas"]
        first = wks.row_values(1)
        if first != header:
            wks.insert_row(header, 1)
    except:
        pass

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
st.title("CalisTracker Pro")
st.markdown("---")

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
        
        # Métricas en vivo
        m1, m2, m3 = st.columns(3)
        m1.metric("Sets Totales", st.session_state.set_count)
        current_vol = sum(st.session_state.sets)
        m2.metric("Volumen Actual", current_vol)
        last_rep = st.session_state.sets[-1] if st.session_state.sets else 0
        m3.metric("Última serie", f"{last_rep} reps")

        st.markdown("#### Añadir repeticiones de la serie")
        c_rep, c_btn = st.columns([2, 1])
        with c_rep:
            reps = st.number_input("Reps realizadas:", min_value=0, value=0, label_visibility="collapsed")
        with c_btn:
            if st.button("➕ Agregar", use_container_width=True):
                if reps > 0:
                    st.session_state.set_count += 1
                    st.session_state.sets.append(reps)
                    st.rerun()

        if st.session_state.sets:
            st.write("Series realizadas:")
            sets_str = " - ".join([f"**{s}**" for s in st.session_state.sets])
            st.markdown(f"> {sets_str}")
        
        st.divider()
        
        # BOTÓN GUARDAR (Optimizado)
        if st.button("💾 Guardar Entrenamiento", type="primary", use_container_width=True):
            if st.session_state.sets:
                try:
                    wks = open_sheet_connection()
                    
                    # Preparamos la fila
                    row = [
                        today, ejercicio, metodo,
                        len(st.session_state.sets),
                        ",".join(map(str, st.session_state.sets)),
                        sum(st.session_state.sets),
                        descanso,
                        notas
                    ]
                    
                    # Escribimos (Append consume menos cuota que leer+escribir)
                    wks.append_row(row)
                    
                    st.success("✅ ¡Entrenamiento guardado!")
                    
                    # Limpiamos caché para que el gráfico se actualice al cambiar de pestaña
                    st.cache_data.clear()
                    
                    # Reset UI
                    st.session_state.sets = []
                    st.session_state.set_count = 0
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error al guardar (Google API): {e}")
            else:
                st.warning("⚠️ Agrega al menos una serie antes de guardar.")

# =======================================================
# TAB 2: DASHBOARD
# =======================================================
with tab2:
    # 1. Cargamos datos (usando caché)
    df = load_data()
    
    # Verificamos si hay datos y si las columnas son correctas
    required_columns = ["fecha", "ejercicio", "total_volumen"]
    has_data = not df.empty and all(col in df.columns for col in required_columns)

    if not has_data:
        st.info("Aún no hay datos suficientes para mostrar análisis. Registra tu primer entrenamiento en la pestaña anterior.")
        # Intentamos inicializar cabeceras por si es la primera vez
        if st.button("Inicializar Hoja (Si es la primera vez)"):
            ensure_header_initialization()
            st.success("Cabeceras creadas. Intenta registrar ahora.")
    else:
        # --- PROCESAMIENTO DE DATOS ---
        # Agrupar por SEMANA y EJERCICIO
        df['semana'] = df['fecha'].dt.to_period('W-MON').apply(lambda r: r.start_time)
        weekly_stats = df.groupby(['semana', 'ejercicio'])['total_volumen'].sum().reset_index()

        # --- SECCIÓN 1: PROGRESO SEMANAL (GRÁFICO DE BARRAS) ---
        st.subheader("📊 Evolución Semanal de Volumen")
        st.caption("Barras apiladas: La altura total es tu volumen semanal, dividido por colores según ejercicio.")

        # CAMBIO REALIZADO: mark_bar() en lugar de mark_line()
        chart_weekly = alt.Chart(weekly_stats).mark_bar().encode(
            x=alt.X('semana:T', title='Semana', axis=alt.Axis(format='%d %b')),
            y=alt.Y('total_volumen:Q', title='Volumen Total (Reps)'),
            color=alt.Color('ejercicio:N', 
                            scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values())),
                            legend=alt.Legend(title="Ejercicios")),
            tooltip=['semana', 'ejercicio', 'total_volumen']
        ).properties(
            height=450
        ).interactive()

        st.altair_chart(chart_weekly, use_container_width=True)

        # --- SECCIÓN 2: HISTORIAL FILTRADO ---
        st.divider()
        st.subheader("🔎 Análisis Detallado")
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            # Filtro por ejercicio
            ejercicio_filter = st.multiselect("Filtrar Ejercicios", 
                                              options=df['ejercicio'].unique(), 
                                              default=df['ejercicio'].unique())
        
        # Aplicamos filtro
        df_filtered = df[df['ejercicio'].isin(ejercicio_filter)]
        
        if not df_filtered.empty:
            # Gráfico de Barras por Sesión (Diario)
            st.markdown("##### Detalle por Sesión")
            bar_chart = alt.Chart(df_filtered).mark_bar().encode(
                x=alt.X('fecha:T', title='Fecha Sesión'),
                y=alt.Y('total_volumen:Q', title='Volumen'),
                color=alt.Color('ejercicio:N', legend=None, 
                                scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values()))),
                tooltip=['fecha', 'ejercicio', 'total_volumen', 'notas']
            ).properties(height=300)
            
            st.altair_chart(bar_chart, use_container_width=True)

            with st.expander("Ver tabla de datos completa"):
                st.dataframe(df_filtered.sort_values(by="fecha", ascending=False), use_container_width=True)
        else:
            st.info("No hay datos para los filtros seleccionados.")
