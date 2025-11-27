import streamlit as st
import time

# ---------------------------------------------------
# CONFIGURACIÓN GENERAL
# ---------------------------------------------------
st.title("⏱ Método Cluster – Timer de Entrenamiento")
st.write("Registra tus repeticiones y controla tus descansos automáticamente.")

# ---------------------------------------------------
# ENTRADAS DEL USUARIO
# ---------------------------------------------------
ejercicio = st.text_input("Nombre del ejercicio (ej. Dominadas, Fondos, Flexiones):")
series = st.number_input("Número de series:", min_value=1, step=1)
descanso = st.number_input("Descanso entre series (segundos):", min_value=5, step=5)
reps_objetivo = st.number_input("Reps objetivo por serie (opcional):", min_value=0, step=1)

st.markdown("---")

# ---------------------------------------------------
# INICIO DEL ENTRENAMIENTO
# ---------------------------------------------------
if st.button("🔥 Iniciar Entrenamiento"):
    if not ejercicio:
        st.error("Debes ingresar un nombre de ejercicio.")
        st.stop()

    st.success(f"Entrenamiento iniciado: **{ejercicio}**")
    st.write("---")

    tabla = []  # Registro interno

    for i in range(1, series + 1):
        st.subheader(f"📌 Serie {i} de {series}")

        # Reps realizadas
        reps = st.number_input(
            f"Ingrese repeticiones realizadas en la serie {i}:",
            min_value=0,
            step=1,
            key=f"reps_{i}"
        )

        st.write("Presiona para registrar esta serie:")
        if st.button(f"Registrar serie {i}", key=f"btn_{i}"):
            tabla.append({"Serie": i, "Reps": reps})
            st.success(f"Serie {i} registrada.")

        st.write("## ⏳ Timer de descanso")
        placeholder = st.empty()

        for sec in range(int(descanso), 0, -1):
            placeholder.metric("Descanso", f"{sec} s")
            time.sleep(1)

        placeholder.metric("Descanso", "✔ Terminado")
        st.write("---")

    st.success("¡Entrenamiento completado!")

    st.subheader("📄 Registro final de repeticiones:")
    st.table(tabla)

    st.info("Puedes copiar estos datos a Google Sheets para tu historial mensual.")

