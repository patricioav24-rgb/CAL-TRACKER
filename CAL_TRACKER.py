import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config("CalisTracker", layout="centered")
st.title("🏋️ CalisTracker – Registro de Calistenia (Versión Mejorada)")

st.write("Registra tus series temporalmente y guarda todo al final.")

# -----------------------------
# GOOGLE SHEETS SETUP
# -----------------------------
USE_SECRETS = True
SHEET_NAME = "CalisTracker"

scopes = ["https://spreadsheets.google.com/feeds",
          "https://www.googleapis.com/auth/drive"]

def get_client():
    if USE_SECRETS:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            st.secrets["gcp_service_account"], scopes)
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "service_account.json", scopes)
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_client()
    return client.open(SHEET_NAME).sheet1

def ensure_header(sheet):
    header = ["timestamp","date","exercise","method","set","reps","rest","notes"]
    first = sheet.row_values(1)
    if first != header:
        try:
            sheet.delete_rows(1)
        except:
            pass
        sheet.insert_row(header, 1)

# -----------------------------
# SESSION STATE (TEMPORAL STORAGE)
# -----------------------------
if "temp_sets" not in st.session_state:
    st.session_state.temp_sets = []  # list of {"set": n, "reps": x, "notes": y}

# -----------------------------
# INPUTS
# -----------------------------
today = datetime.now().strftime("%Y-%m-%d")
st.write("📅 Fecha:", today)

exercise = st.selectbox(
    "Ejercicio:",
    ["Dominadas pronas", "Dominadas supinas", "Fondos", "Flexiones", "Remo invertido", "Otro"]
)

method = st.selectbox("Método:", ["Volumen", "Series Libres"])

rest = st.number_input("Descanso (seg)", min_value=0, value=45)
notes_global = st.text_input("Notas generales (opcional)")

st.markdown("---")

# -----------------------------
# AGREGAR SET (TEMPORAL)
# -----------------------------
st.write("## ➕ Registrar una Serie (temporal)")

reps = st.number_input("Repeticiones de esta serie:", min_value=0, value=0)
notes_set = st.text_input("Notas del set (opcional)")

if st.button("Agregar esta serie"):
    set_number = len(st.session_state.temp_sets) + 1
    st.session_state.temp_sets.append({
        "set": set_number,
        "reps": reps,
        "notes": notes_set
    })
    st.success(f"Serie {set_number} agregada temporalmente.")

st.markdown("---")

# -----------------------------
# MOSTRAR TABLA TEMPORAL
# -----------------------------
st.write("## 📘 Series registradas (temporal)")

if st.session_state.temp_sets:
    temp_df = pd.DataFrame(st.session_state.temp_sets)
    st.dataframe(temp_df, use_container_width=True)

    # Botón para eliminar último set
    if st.button("❌ Eliminar último set"):
        st.session_state.temp_sets.pop()
        st.success("Último set eliminado.")
else:
    st.info("Aún no hay series registradas.")

st.markdown("---")

# -----------------------------
# GUARDAR TODO EN GOOGLE SHEETS
# -----------------------------
st.write("## 💾 Guardar toda la sesión en Google Sheets")

if st.button("Guardar sesión completa"):
    if not st.session_state.temp_sets:
        st.error("No hay sets registrados para guardar.")
    else:
        try:
            sheet = open_sheet()
            ensure_header(sheet)

            for set_data in st.session_state.temp_sets:
                row = [
                    datetime.now().isoformat(),
                    today,
                    exercise,
                    method,
                    set_data["set"],
                    set_data["reps"],
                    rest,
                    set_data["notes"]
                ]
                sheet.append_row(row, value_input_option="USER_ENTERED")

            st.success("Sesión guardada exitosamente en Google Sheets.")
            st.session_state.temp_sets = []  # limpiar

        except Exception as e:
            st.error("Error guardando en Sheets: " + str(e))
