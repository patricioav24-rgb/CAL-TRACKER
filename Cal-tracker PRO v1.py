import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------
# 1. CONFIGURACIÓN
# -------------------------------------------------------
st.set_page_config(page_title="CalisTracker Pro", page_icon="📒", layout="wide")

# -------------------------------------------------------
# 2. CSS (ESTILO APP)
# -------------------------------------------------------
def local_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 5rem !important;
        }

        [data-testid="stMetric"] {
            background-color: #262730;
            border: 1px solid #444;
            padding: 15px;
            border-radius: 10px;
            color: white;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.5);
        }
        
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; border-radius: 8px;
            background-color: #1E1E1E; color: white; border: 1px solid #333;
        }
        .stTabs [aria-selected="true"] {
            background-color: #FF4B4B !important; color: white !important;
            border-color: #FF4B4B !important;
        }

        .stButton > button {
            border-radius: 20px; border: none; background-color: #FF4B4B;
            color: white; font-weight: bold; padding: 10px 20px; transition: all 0.3s;
        }
        .stButton > button:hover {
            background-color: #FF2B2B; transform: scale(1.02);
        }
        </style>
    """, unsafe_allow_html=True)

local_css()

# -------------------------------------------------------
# 3. VARIABLES
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
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# -------------------------------------------------------
# 4. BACKEND (CORREGIDO LECTURA DE FECHAS)
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
    return sh.sheet1

@st.cache_data(ttl=60) # Bajamos el caché a 60seg para pruebas
def load_data():
    try:
        wks = open_sheet_connection()
        rows = wks.get_all_records()
        if not rows: return pd.DataFrame()
        
        df = pd.DataFrame(rows)
        
        # --- FIX CRÍTICO: FORMATO DE FECHA ---
        if "fecha" in df.columns:
            # Convertimos a string primero para limpiar espacios
            df["fecha"] = df["fecha"].astype(str).str.strip()
            # dayfirst=True es vital para formato Latino (DD/MM/YYYY)
            df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors='coerce')
            
            # Eliminamos filas donde la fecha falló (NaT)
            df = df.dropna(subset=['fecha'])
            
        return df
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

# -------------------------------------------------------
# 5. ESTADO
# -------------------------------------------------------
if "sets" not in st.session_state: st.session_state.sets = []
if "set_count" not in st.session_state: st.session_state.set_count = 0

# -------------------------------------------------------
# 6. UI
# -------------------------------------------------------
st.title("🦾 CalisTracker Pro V3")

tab1, tab2 = st.tabs(["📝 Registrar Sesión", "📊 Dashboard"])

# --- TAB 1: REGISTRO ---
with tab1:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("### ⚙️ Configurar")
        today = datetime.now().strftime("%d-%m-%Y") # Formato latino visual
        today_iso = datetime.now().strftime("%Y-%m-%d") # Formato para guardar
        st.caption(f"Fecha: {today}")
        
        ejercicio = st.selectbox("Ejercicio", list(COLOR_MAP.keys()))
        metodo = st.selectbox("Método", ["Volumen", "Series Libres", "Lastre"])
        descanso = st.slider("Descanso (seg)", 0, 180, 45, step=5)
        notas = st.text_area("Notas", height=80)

    with col2:
        st.markdown("### ⚡ Ejecución")
        m1, m2, m3 = st.columns(3)
        m1.metric("Sets", st.session_state.set_count)
        m2.metric("Volumen", sum(st.session_state.sets))
        last_rep = st.session_state.sets[-1] if st.session_state.sets else 0
        m3.metric("Última Rep", last_rep)
        
        st.markdown("---")
        c1, c2 = st.columns([2,1])
        with c1: reps = st.number_input("Reps", 0, value=0)
        with c2: 
            st.write(""); st.write("")
            if st.button("➕ AGREGAR", use_container_width=True):
                if reps>0:
                    st.session_state.set_count+=1
                    st.session_state.sets.append(reps)
                    st.rerun()
        
        if st.session_state.sets:
            st.markdown("#### Historial:")
            badges = "".join([f"<span style='background:#444; padding:5px 10px; border-radius:15px; margin:2px; display:inline-block'>{s}</span>" for s in st.session_state.sets])
            st.markdown(badges, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("💾 GUARDAR ENTRENAMIENTO", type="primary", use_container_width=True):
            if st.session_state.sets:
                try:
                    wks = open_sheet_connection()
                    # Guardamos la fecha en formato ISO (YYYY-MM-DD) para evitar problemas
                    row = [today_iso, ejercicio, metodo, len(st.session_state.sets), ",".join(map(str, st.session_state.sets)), sum(st.session_state.sets), descanso, notas]
                    wks.append_row(row)
                    st.success("✅ Guardado")
                    st.cache_data.clear()
                    st.session_state.sets = []; st.session_state.set_count = 0
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")

# --- TAB 2: DASHBOARD ---
with tab2:
    df = load_data()
    
    if df.empty:
        st.warning("⚠️ No hay datos válidos para mostrar.")
        st.info("Asegúrate de registrar al menos un entrenamiento.")
    else:
        # Procesamiento
        df['semana'] = df['fecha'].dt.to_period('W-MON').apply(lambda r: r.start_time)
        weekly_stats = df.groupby(['semana
