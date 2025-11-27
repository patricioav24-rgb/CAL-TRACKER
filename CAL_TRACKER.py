import streamlit as st
import pandas as pd
import time
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------
# CONFIG
# -----------------------
st.set_page_config("CalisTracker", layout="centered")
st.title("🏋️ CalisTracker • Calistenia ")

# ---------- GOOGLE SHEETS SETUP ----------
USE_SECRETS = True
SHEET_NAME = "CalisTracker"

scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_gsheet_client():
    if USE_SECRETS:
        sa_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scopes)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scopes)

    client = gspread.authorize(creds)
    return client

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    return sh.sheet1

def ensure_header(wks):
    header = ["timestamp","date","exercise","method","set_number","reps","duration_sec","rest_sec","notes"]
    first = wks.row_values(1)
    if first != header:
        wks.delete_rows(1)
        wks.insert_row(header, 1)

# ---------- SESSION STATE ----------
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "set_count" not in st.session_state:
    st.session_state.set_count = 0

# ---------- Inputs ----------
col1, col2 = st.columns([2,1])
today = datetime.now().strftime("%Y-%m-%d")

with col1:
    st.write("**Fecha:**", today)
    exercise = st.selectbox("Ejercicio", ["Dominadas - Pronas","Dominadas - Supinas","Fondos","Flexiones","Remo invertido","Otro"])
    method = st.selectbox("Método", ["Volumen", "Cluster", "EMOM", "Series libres"])
    notes = st.text_input("Notas (opcional)")

with col2:
    rest_default = st.number_input("Descanso por serie (seg)", min_value=0, value=45)
    target_sets = st.number_input("Series objetivo", min_value=1, value=5)
    target_reps = st.number_input("Reps objetivo por serie (opcional)", min_value=0, value=0)

st.markdown("---")

# ---------- Timer Control ----------
c1, c2, c3 = st.columns([1,1,2])

with c1:
    if st.button("Iniciar sesión"):
        st.session_state.running = True
        st.session_state.start_time = time.time()
        st.session_state.set_count = 0
        st.success("Sesión iniciada")

with c2:
    if st.button("Detener sesión"):
        st.session_state.running = False
        st.session_state.start_time = None
        st.success("Sesión detenida")

with c3:
    st.write("Sets completados:", st.session_state.set_count)

if st.session_state.running:
    elapsed = int(time.time() - st.session_state.start_time)
    st.metric("Tiempo desde inicio (s)", value=elapsed)

# ---------- Registrar serie ----------
st.markdown("### Registrar Serie")
reps = st.number_input("Repeticiones realizadas (esta serie)", min_value=0, value=0)
duration = st.number_input("Duración serie (seg)", min_value=0, value=0)

if st.button("Guardar serie"):
    st.session_state.set_count += 1
    timestamp = datetime.now().isoformat()
    row = [timestamp, today, exercise, method, st.session_state.set_count, reps, duration, rest_default, notes]

    try:
        wks = open_sheet()
        ensure_header(wks)
        wks.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"Serie guardada (set {st.session_state.set_count})")
    except Exception as e:
        st.error("Error al guardar en Google Sheets: " + str(e))

# ---------- Main timer display ----------
if st.session_state.running:
    if st.session_state.start_time is not None:
        elapsed = int(time.time() - st.session_state.start_time)
        st.metric("⏱ Tiempo desde inicio (s)", elapsed)
    else:
        st.metric("⏱ Tiempo desde inicio (s)", "0")


# ---------- HISTORIAL HOY ----------
st.markdown("### Historial hoy")
try:
    wks = open_sheet()
    rows = wks.get_all_records()
    df_all = pd.DataFrame(rows)
    if not df_all.empty:
        df_today = df_all[df_all["date"] == today]
        st.dataframe(df_today)

        if not df_today.empty:
            st.write("Volumen total hoy:", int(df_today["reps"].sum()))
            st.write("Sets hoy:", int(df_today.shape[0]))
    else:
        st.info("No hay datos guardados aún.")

except Exception as e:
    st.error(f"Error al leer Google Sheets: {e}")

# ---------- EXPORT ----------
if st.button("Descargar historial (CSV)"):
    if not df_all.empty:
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", csv, "calistracker_history.csv", "text/csv")
    else:
        st.error("No hay datos para descargar.")







