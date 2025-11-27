import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------------
# CONFIGURACIÓN DE LA APP
# -----------------------------
st.set_page_config("CalisTracker", layout="centered")
st.title("🏋️ CalisTracker – Registro simple de calistenia")

st.write("Registra tus series de forma rápida y sin distracciones.")

# -----------------------------
# GOOGLE SHEETS
# -----------------------------
USE_SECRETS = True   # Streamlit Cloud usa secrets
SHEET_NAME = "CalisTracker"

scopes = ["https://spreadsheets.google.com/feeds",
          "https://www.googleapis.com/auth/drive"]

def get_client():
    if USE_SECRETS:
        sa = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(sa, scopes)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scopes)
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_client()
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def ensure_header(sheet):
    header = ["timestamp","date","exercise","method","set","reps","target_reps","target_sets","rest","notes"]
    first = sheet.row_values(1)
    if first != header:
        try:
            sheet.delete_rows(1)
        except: pass
        sheet.insert_row(header, 1)

# -----------------------------
# INTERFAZ
# -----------------------------
today = datetime.now().strftime("%Y-%m-%d")
st.write("📅 Fecha:", today)

exercise = st.selectbox(
    "Ejercicio:",
    ["Dominadas pronas", "Dominadas supinas", "Fondos", "Flexiones", "Remo invertido", "Otro"]
)

method = st.selectbox("Método:", ["Volumen", "Series Libres"])

target_reps = st.number_input("Reps objetivo por serie", min_value=0, value=4)
target_sets = st.number_input("Series objetivo", min_value=0, value=10)
rest = st.number_input("Descanso (seg)", min_value=0, value=45)
notes = st.text_input("Notas (opcional)")

st.markdown("---")

# Estado de la sesión
if "set_count" not in st.session_state:
    st.session_state.set_count = 0

st.write("### 🔢 Sets completados:", st.session_state.set_count)

# -----------------------------
# GUARDAR SERIE
# -----------------------------
reps = st.number_input("Repeticiones en esta serie:", min_value=0, value=0)

if st.button("💾 Guardar esta serie"):
    st.session_state.set_count += 1

    timestamp = datetime.now().isoformat()
    row = [
        timestamp, today, exercise, method,
        st.session_state.set_count,
        reps, target_reps, target_sets, rest, notes
    ]

    try:
        sheet = open_sheet()
        ensure_header(sheet)
        sheet.append_row(row, value_input_option="USER_ENTERED")
        st.success(f"Serie {st.session_state.set_count} guardada.")
    except Exception as e:
        st.error("Error guardando en Google Sheets: " + str(e))

st.markdown("---")

# -----------------------------
# HISTORIAL DEL DÍA
# -----------------------------
st.write("## 📘 Historial de hoy")

try:
    sheet = open_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty:
        df_today = df[df["date"] == today]
        if df_today.empty:
            st.info("Aún no hay registros hoy.")
        else:
            st.dataframe(df_today, use_container_width=True)
            st.write("**Sets hoy:**", df_today.shape[0])
            st.write("**Volumen total (reps):**", int(df_today["reps"].sum()))
    else:
        st.info("No hay datos aún.")

except Exception as e:
    st.error("Error leyendo historial: " + str(e))
