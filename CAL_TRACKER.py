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
st.title("🏋️ CalisTracker • Calistenia (registro en Google Sheets)")

# ---------- GOOGLE SHEETS SETUP ----------
# LOCAL: coloca service_account.json en la misma carpeta
# PRODUCTION (streamlit cloud): guarda el JSON en Secrets y usa st.secrets["gcp_service_account"]
USE_SECRETS = False  # True si quieres leer JSON desde st.secrets (Streamlit Cloud)
SHEET_NAME = "CalisTracker"

def get_gsheet_client():
    if USE_SECRETS:
        # cuando uses Streamlit Cloud, pega el JSON en Secrets (key name e.g. gcp_service_account)
        sa_info = st.secrets["gcp_service_account"]
        # write JSON to temp file or use oauth2client.from_json_keyfile_dict
        from oauth2client.service_account import ServiceAccountCredentials
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa_info, scopes)
    else:
        # archivo local service_account.json
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scopes)
    client = gspread.authorize(creds)
    return client

scopes = ["https://spreadsheets.google.com/feeds",
          "https://www.googleapis.com/auth/drive"]

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    wks = sh.sheet1
    return wks

# Ensure sheet exists and has header row
def ensure_header(wks):
    header = ["timestamp","date","exercise","method","set_number","reps","duration_sec","rest_sec","notes"]
    try:
        first = wks.row_values(1)
        if first != header:
            wks.delete_rows(1)
            wks.insert_row(header,1)
    except Exception:
        wks.insert_row(header,1)

# ---------- UI: session config ----------
if "running" not in st.session_state:
    st.session_state.running = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "set_count" not in st.session_state:
    st.session_state.set_count = 0

# ---------- Inputs ----------
col1, col2 = st.columns([2,1])
with col1:
    today = datetime.now().strftime("%Y-%m-%d")
    st.write("**Fecha:**", today)

    exercise = st.selectbox("Ejercicio", ["Dominadas - Pronas","Dominadas - Supinas","Fondos","Flexiones","Remo invertido","Otro"])
    method = st.selectbox("Método", ["Volumen", "Cluster", "EMOM", "Series libres"])
    notes = st.text_input("Notas (opcional)")

with col2:
    rest_default = st.number_input("Descanso por serie (seg)", min_value=0, value=45)
    target_sets = st.number_input("Series objetivo", min_value=1, value=5)
    target_reps = st.number_input("Reps objetivo por serie (opcional)", min_value=0, value=0)

st.markdown("---")

# ---------- Timer / control ----------
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

# ---------- Main timer display ----------
if st.session_state.running:
    elapsed = int(time.time() - st.session_state.start_time)
    st.metric("Tiempo desde inicio (s)", value=elapsed)

# ---------- Record a set ----------
st.markdown("### Registrar Serie")
reps = st.number_input("Repeticiones realizadas (esta serie)", min_value=0, value=0)
duration = st.number_input("Duración serie (seg)", min_value=0, value=0)
if st.button("Guardar serie"):
    st.session_state.set_count += 1
    timestamp = datetime.now().isoformat()
    row = [timestamp, today, exercise, method, st.session_state.set_count, reps, duration, rest_default, notes]

    # append to google sheets
    try:
        wks = open_sheet()
        ensure_header(wks)
        wks.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"Serie guardada (set {st.session_state.set_count})")
    except Exception as e:
        st.error("Error al guardar en Google Sheets: " + str(e))

# ---------- Quick auto-cluster helper ----------
st.markdown("### Herramienta rápida: Cluster timer")
cluster_cols = st.columns(3)
cluster_reps = cluster_cols[0].number_input("Reps por mini-set", min_value=1, value=4, key="cr")
cluster_sets = cluster_cols[1].number_input("Mini-sets (por cluster)", min_value=1, value=3, key="cs")
cluster_rest = cluster_cols[2].number_input("Descanso (s) entre mini-sets", min_value=5, value=45, key="crt")

if st.button("Iniciar Cluster"):
    st.session_state.running = True
    # run cluster loop (blocking) - streamlit reruns so we simulate with while
    for s in range(cluster_sets):
        st.info(f"Mini-set {s+1}: haz {cluster_reps} repeticiones")
        # wait for user to press 'Siguiente' - simple approach: block with sleep but better UX would be callback
        for sec in range(cluster_rest,0,-1):
            st.write(f"Descanso: {sec}s", end="\r")
            time.sleep(1)
    st.success("Cluster finalizado - recuerda guardar cada serie manualmente si quieres detalle por serie.")

st.markdown("---")

# ---------- View today's data ----------
st.markdown("### Historial hoy")
try:
    wks = open_sheet()
    rows = wks.get_all_records()
    df_all = pd.DataFrame(rows)
    if not df_all.empty:
        df_today = df_all[df_all["date"] == today]
        st.dataframe(df_today)
        # simple stats
        if not df_today.empty:
            st.write("Volumen total hoy:", int(df_today["reps"].sum()))
            st.write("Sets hoy:", int(df_today.shape[0]))
    else:
        st.info("No hay datos guardados aún.")
except Exception as e:
    st.error("Error al leer Google Sheets: " + str(e))

# ---------- Export CSV ----------
if st.button("Descargar historial (CSV)"):
    try:
        csv = df_all.to_csv(index=False).encode("utf-8")
        st.download_button("Descargar CSV", data=csv, file_name="calistracker_history.csv", mime="text/csv")
    except Exception:
        st.error("No hay datos para descargar.")
