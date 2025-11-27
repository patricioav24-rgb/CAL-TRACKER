import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# -------------------------------------------------------
# CONFIGURACIÓN GENERAL
# -------------------------------------------------------
st.set_page_config("CalisTracker", layout="wide")
st.title("🏋️ CalisTracker – Registro de Calistenia")

SHEET_NAME = "CalisTracker"

scopes = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_client():
    """Conecta usando las credenciales en st.secrets."""
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scopes
    )
    return gspread.authorize(creds)

@st.cache_resource(ttl=600)
def open_sheet():
    client = get_client()
    sh = client.open(SHEET_NAME)
    wks = sh.sheet1
    return wks

def ensure_header(wks):
    """Crea encabezado si no existe."""
    header = [
        "fecha", "ejercicio", "metodo", "total_sets",
        "reps_por_set", "total_volumen", "descanso", "notas"
    ]
    first = wks.row_values(1)
    if first != header:
        wks.clear()
        wks.insert_row(header, 1)

# -------------------------------------------------------
# ESTADO DE LA SESIÓN
# -------------------------------------------------------
if "sets" not in st.session_state:
    st.session_state.sets = []

if "set_count" not in st.session_state:
    st.session_state.set_count = 0

# -------------------------------------------------------
# UI – Registro de sesión
# -------------------------------------------------------
st.header("📘 Registro de Entrenamiento")

today = datetime.now().strftime("%Y-%m-%d")
st.write("**Fecha:**", today)

ejercicio = st.selectbox("Ejercicio", [
    "Dominadas – Pronas",
    "Dominadas – Supinas",
    "Fondos",
    "Flexiones",
    "Remo invertido",
    "Otro"
])

metodo = st.selectbox("Método", ["Volumen", "Series Libres"])

col1, col2 = st.columns(2)
with col1:
    descanso = st.number_input("Descanso por serie (seg)", min_value=0, value=45)
with col2:
    notas = st.text_input("Notas (opcional)")

st.subheader("➕ Registrar series")

reps = st.number_input("Reps de esta serie:", min_value=0, value=0)

if st.button("Agregar serie"):
    st.session_state.set_count += 1
    st.session_state.sets.append(reps)
    st.success(f"Serie agregada ({reps} reps). Total sets: {st.session_state.set_count}")

# Mostrar sets actuales
if st.session_state.sets:
    st.write("### Sets actuales")
    st.write(st.session_state.sets)
else:
    st.info("Aún no agregas series.")

# -------------------------------------------------------
# Guardar resumen en Google Sheets
# -------------------------------------------------------
st.markdown("---")
if st.button("💾 Guardar sesión en Google Sheets"):
    try:
        total_sets = len(st.session_state.sets)
        total_vol = sum(st.session_state.sets)
        reps_por_set = ",".join([str(r) for r in st.session_state.sets])

        wks = open_sheet()
        ensure_header(wks)

        row = [
            today, ejercicio, metodo,
            total_sets,
            reps_por_set,
            total_vol,
            descanso,
            notas
        ]
        wks.append_row(row)

        st.success("Sesión guardada exitosamente.")

        # Reset
        st.session_state.sets = []
        st.session_state.set_count = 0

    except Exception as e:
        st.error("Error al guardar en Google Sheets: " + str(e))

# -------------------------------------------------------
# HISTORIAL FILTRADO
# -------------------------------------------------------
st.markdown("---")
st.header("📚 Historial detallado (Filtrado avanzado)")

try:
    wks = open_sheet()
    ensure_header(wks)
    rows = wks.get_all_records()
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("Aún no hay historial registrado.")
    else:
        df["fecha"] = pd.to_datetime(df["fecha"])

        # ---- FILTROS ----
        st.subheader("🔎 Filtros")

        colA, colB, colC = st.columns(3)

        with colA:
            ejercicio_f = st.selectbox(
                "Ejercicio",
                ["Todos"] + sorted(df["ejercicio"].unique())
            )

        with colB:
            metodo_f = st.selectbox(
                "Método",
                ["Todos"] + sorted(df["metodo"].unique())
            )

        with colC:
            fecha_inicio = st.date_input(
                "Desde",
                value=df["fecha"].min().date()
            )

        fecha_fin = st.date_input(
            "Hasta",
            value=df["fecha"].max().date()
        )

        # ---- APLICAR FILTROS ----
        filtered_df = df.copy()

        if ejercicio_f != "Todos":
            filtered_df = filtered_df[filtered_df["ejercicio"] == ejercicio_f]

        if metodo_f != "Todos":
            filtered_df = filtered_df[filtered_df["metodo"] == metodo_f]

        filtered_df = filtered_df[
            (filtered_df["fecha"] >= pd.to_datetime(fecha_inicio)) &
            (filtered_df["fecha"] <= pd.to_datetime(fecha_fin))
        ]

        # ---- MOSTRAR TABLA ----
        st.subheader("📄 Resultados filtrados")
        st.dataframe(filtered_df, use_container_width=True)

        # ---- DESCARGAR ----
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar CSV filtrado",
            data=csv,
            file_name="historial_filtrado.csv",
            mime="text/csv"
        )

        # ---- GRAFICO DEL EJERCICIO ----
        if ejercicio_f != "Todos":
            st.subheader(f"📊 Evolución del volumen – {ejercicio_f}")
            df_plot = filtered_df.groupby("fecha")["total_volumen"].sum()
            st.line_chart(df_plot)

except Exception as e:
    st.error("Error al cargar historial: " + str(e))


# -------------------------------------------------------
# DASHBOARD – Tipo Atleta Profesional
# -------------------------------------------------------
st.markdown("---")
st.header("📊 Dashboard de Progreso")

try:
    wks = open_sheet()
    ensure_header(wks)
    rows = wks.get_all_records()
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("No hay datos registrados aún.")
    else:
        df["fecha"] = pd.to_datetime(df["fecha"])

        # ----- Gráfico Semanal -----
        st.subheader("📈 Progreso semanal (volumen total)")
        last_week = df[df["fecha"] >= datetime.now() - timedelta(days=7)]

        if not last_week.empty:
            st.line_chart(last_week.groupby("fecha")["total_volumen"].sum())
        else:
            st.info("Aún no hay datos suficientes para mostrar la semana.")

        # ----- Gráfico Mensual -----
        st.subheader("📆 Volumen total mensual")
        last_month = df[df["fecha"] >= datetime.now() - timedelta(days=30)]

        if not last_month.empty:
            st.bar_chart(last_month.groupby("ejercicio")["total_volumen"].sum())
        else:
            st.info("Aún no hay suficientes datos para el mes.")

        # ----- Comparación por método -----
        st.subheader("⚔️ Comparación entre métodos")
        st.bar_chart(df.groupby("metodo")["total_volumen"].sum())

except Exception as e:
    st.error("Error al generar dashboard: " + str(e))
