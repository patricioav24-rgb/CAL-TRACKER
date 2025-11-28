import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------
# 1. CONFIGURACIÓN DE PÁGINA
# -------------------------------------------------------
st.set_page_config(page_title="CalisTracker Pro", page_icon="📒", layout="wide")

# -------------------------------------------------------
# 2. INYECCIÓN CSS (ESTILO VISUAL)
# -------------------------------------------------------
def local_css():
    st.markdown("""
        <style>
        /* Quitar menú hamburguesa y footer para que parezca App */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Ajustar padding superior para móviles */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }

        /* ESTILO DE TARJETAS (Métricas) */
        [data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #444;
            padding: 15px;
            border-radius: 10px;
            color: white;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
        }
        
        /* ESTILO DE PESTAÑAS (Tabs) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            border-radius: 8px;
            background-color: #1E1E1E;
            color: white;
            border: 1px solid #333;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FF4B4B !important; /* Color activo rojo/naranja */
            color: white !important;
            border-color: #FF4B4B !important;
        }

        /* ESTILO DE BOTONES */
        .stButton > button {
            border-radius: 20px;
            border: none;
            background-color: #FF4B4B;
            color: white;
            font-weight: bold;
            padding: 10px 20px;
            transition: all 0.3s;
        }
        .stButton > button:hover {
            background-color: #FF2B2B;
            transform: scale(1.02);
            box-shadow: 0 4px 10px rgba(255, 75, 75, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# -------------------------------------------------------
# 3. VARIABLES Y COLORES
# -------------------------------------------------------
COLOR_MAP = {
    "Dominadas – Pronas": "#FF5733",
    "Dominadas – Supinas": "#C70039",
    "Fondos": "#33FF57",
    "Flexiones": "#3357FF",
    "Remo invertido": "#F333FF",
    "Otro": "#808080"
}

SHEET_NAME = "CalisTracker"
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# -------------------------------------------------------
# 4. BACKEND
# -------------------------------------------------------
def get_client():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet_connection():
    client = get_client()
    sh = client.open(SHEET_NAME)
    wks = sh.sheet1
    return wks

@st.cache_data(ttl=300)
def load_data():
    try:
        wks = open_sheet_connection()
        rows = wks.get_all_records()
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Aseguramos que 'fecha' sea datetime y manejamos errores de conversión
        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors='coerce')
            df = df.dropna(subset=['fecha']) # Eliminar filas con fechas invalidas
        return df
    except Exception as e:
        return pd.DataFrame()

def ensure_header_initialization():
    try:
        wks = open_sheet_connection()
        header = ["fecha", "ejercicio", "metodo", "total_sets", "reps_por_set", "total_volumen", "descanso", "notas"]
        first = wks.row_values(1)
        if first != header:
            wks.insert_row(header, 1)
    except:
        pass

# -------------------------------------------------------
# 5. ESTADO
# -------------------------------------------------------
if "sets" not in st.session_state: st.session_state.sets = []
if "set_count" not in st.session_state: st.session_state.set_count = 0

# -------------------------------------------------------
# 6. UI PRINCIPAL
# -------------------------------------------------------
st.title("📒CalisTracker Pro")

tab1, tab2 = st.tabs(["📝 Registrar Sesión", "📊 Dashboard"])

with tab1:
    col_main_1, col_main_2 = st.columns([1, 2])

    with col_main_1:
        st.markdown("### ⚙️ Configurar") 
        today = datetime.now().strftime("%Y-%m-%d")
        st.caption(f"Fecha: {today}")
        
        ejercicio = st.selectbox("Ejercicio", list(COLOR_MAP.keys()))
        metodo = st.selectbox("Método", ["Volumen", "Series Libres", "Lastre"])
        descanso = st.slider("Descanso (seg)", 0, 180, 45, step=5)
        notas = st.text_area("Notas", height=100)

    with col_main_2:
        st.markdown("### ⚡ Ejecución")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Sets", st.session_state.set_count)
        m2.metric("Volumen", sum(st.session_state.sets))
        last_rep = st.session_state.sets[-1] if st.session_state.sets else 0
        m3.metric("Última Rep", last_rep)

        st.markdown("---")
        
        c1, c2 = st.columns([2, 1])
        with c1:
            reps = st.number_input("Reps realizadas", min_value=0, value=0)
        with c2:
            st.write("") 
            st.write("") 
            if st.button("➕ AGREGAR SERIE", use_container_width=True):
                if reps > 0:
                    st.session_state.set_count += 1
                    st.session_state.sets.append(reps)
                    st.rerun()

        if st.session_state.sets:
            st.markdown("#### Historial sesión:")
            badges = "".join([f"<span style='background:#444; padding:5px 10px; border-radius:15px; margin:2px; display:inline-block; font-size:0.9em'>{s}</span>" for s in st.session_state.sets])
            st.markdown(badges, unsafe_allow_html=True)
        
        st.markdown("---")
        
        if st.button("💾 GUARDAR ENTRENAMIENTO", type="primary", use_container_width=True):
            if st.session_state.sets:
                try:
                    wks = open_sheet_connection()
                    row = [
                        today, ejercicio, metodo,
                        len(st.session_state.sets),
                        ",".join(map(str, st.session_state.sets)),
                        sum(st.session_state.sets),
                        descanso,
                        notas
                    ]
                    wks.append_row(row)
                    st.success("✅ Guardado")
                    st.cache_data.clear()
                    st.session_state.sets = []
                    st.session_state.set_count = 0
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Agrega series primero.")

with tab2:
    df = load_data()
    if df.empty:
        st.info("Sin datos. Registra un entrenamiento para ver los gráficos.")
        if st.button("Inicializar Hoja"): ensure_header_initialization()
    else:
        # Preproceso
        df['semana'] = df['fecha'].dt.to_period('W-MON').apply(lambda r: r.start_time)
        weekly_stats = df.groupby(['semana', 'ejercicio'])['total_volumen'].sum().reset_index()

        st.markdown("### 📈 Progreso Semanal")
        
        # --- CORRECCIÓN GRÁFICO 1: BARRAS ANCHAS Y TEXTO BLANCO ---
        # Aumentamos size=50 para que sean mucho más anchas
        chart_weekly = alt.Chart(weekly_stats).mark_bar(size=50, cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
            x=alt.X('semana:T', title='Semana', axis=alt.Axis(format='%d %b', labelAngle=0, grid=False, tickCount="week")),
            y=alt.Y('total_volumen:Q', title='Volumen', axis=alt.Axis(grid=True, gridDash=[5,5])),
            color=alt.Color('ejercicio:N', scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values()))),
            tooltip=['semana', 'ejercicio', 'total_volumen']
        ).configure_axis(
            labelColor='white', # Fuerza texto blanco en ejes
            titleColor='white', # Fuerza título blanco
            gridColor='#444'    # Rejilla gris suave
        ).configure_legend(
            labelColor='white', # Leyenda blanca
            titleColor='white'
        ).configure_view(
            stroke=None         # Quita el borde feo del cuadro
        ).properties(height=350, background='transparent').interactive()
        
        st.altair_chart(chart_weekly, use_container_width=True)

        st.markdown("---")
        st.markdown("### 📅 Detalle Diario")
        ejercicio_filter = st.multiselect("Filtrar:", df['ejercicio'].unique(), default=df['ejercicio'].unique())
        df_filtered = df[df['ejercicio'].isin(ejercicio_filter)]
        
        if not df_filtered.empty:
            # --- CORRECCIÓN GRÁFICO 2: BARRAS DIARIAS ANCHAS ---
            # size=30 para días individuales
            bar_chart = alt.Chart(df_filtered).mark_bar(size=30, cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X('fecha:T', timeUnit='yearmonthdate', title='Fecha', axis=alt.Axis(format='%d/%m')),
                y=alt.Y('total_volumen:Q', title='Volumen'),
                color=alt.Color('ejercicio:N', legend=None, scale=alt.Scale(domain=list(COLOR_MAP.keys()), range=list(COLOR_MAP.values()))),
                tooltip=['fecha', 'total_volumen', 'notas']
            ).configure_axis(
                labelColor='white',
                titleColor='white',
                gridColor='#444'
            ).configure_view(
                stroke=None
            ).properties(height=300, background='transparent').interactive()
            
            st.altair_chart(bar_chart, use_container_width=True)
            
            with st.expander("Ver tabla de datos"):
                st.dataframe(df_filtered.sort_values("fecha", ascending=False), use_container_width=True)
