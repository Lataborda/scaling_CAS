import warnings
warnings.filterwarnings("ignore", message="The use_column_width parameter has been deprecated")

import streamlit as st
import pandas as pd
import os
import networkx as nx
import matplotlib.pyplot as plt
import textwrap
import streamlit_shadcn_ui as ui
from pyvis.network import Network
import streamlit.components.v1 as components
import base64
from PIL import Image

# Función para la galería paginada (Folleto)
def paginated_gallery(image_prefix, num_pages, caption_prefix, state_key="page"):
    if state_key not in st.session_state:
        st.session_state[state_key] = 1
    col_prev, col_mid, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("Página anterior", key=f"{state_key}_prev") and st.session_state[state_key] > 1:
            st.session_state[state_key] -= 1
            st.experimental_rerun()
    with col_mid:
        st.write(f"Página {st.session_state[state_key]} de {num_pages}")
    with col_next:
        if st.button("Página siguiente", key=f"{state_key}_next") and st.session_state[state_key] < num_pages:
            st.session_state[state_key] += 1
            st.experimental_rerun()
    image_path = f"data/{image_prefix}{st.session_state[state_key]}.jpg"
    st.image(image_path, caption=f"{caption_prefix} {st.session_state[state_key]}", use_container_width=True)

# ---------------------------
# Configuración general
# ---------------------------
st.set_page_config(page_title="Dashboard Integral", layout="wide")

# CSS personalizado
custom_css = """
<style>
.css-18e3th9, .css-1d391kg {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}
.product-card {
    background-color: #f9f9f9 !important;
    color: #000000 !important;
    border: 1px solid #ddd !important;
    padding: 16px !important;
    border-radius: 8px !important;
    margin-bottom: 16px !important;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.1) !important;
}
.product-card h3 {
    color: #000000 !important;
}
table, th, td {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Título principal
st.title("Construcción: Estrategia escalonamiento")
st.divider()

# Selección de vista
view_option = st.sidebar.selectbox("Selecciona la vista:", 
                                   ["Inventario", "Análisis de red por cultivos", "Brief: Caracterización ME", "Folleto Banano"])

# ---------------------------------------------------
# VISTA: Inventario (sección ya existente)
# ---------------------------------------------------
if view_option == "Inventario":
    st.header("Inventario de entregables proyecto CAS")
    csv_path = "data/Inventary2.csv"
    try:
        df = pd.read_csv(csv_path, delimiter=';')
    except Exception as e:
        st.error("Error al leer el CSV de inventario: " + str(e))
        st.stop()
    for col in ["Componente", "Resultado", "Cultivos Asociados", "Producto N°"]:
        df[col] = df[col].astype(str)
    st.sidebar.header("Filtros de Inventario")
    componentes = sorted(df["Componente"].dropna().unique())
    selected_componente = st.sidebar.selectbox("Selecciona un Componente", componentes)
    df_comp = df[df["Componente"] == selected_componente]
    resultados = sorted(df_comp["Resultado"].dropna().unique())
    selected_resultado = st.sidebar.selectbox("Selecciona un Resultado", resultados)
    df_comp = df_comp[df_comp["Resultado"] == selected_resultado]
    cultivo_options = ["todos"]
    for cell in df_comp["Cultivos Asociados"]:
        for cultivo in cell.split(","):
            cultivo_options.append(cultivo.strip().lower())
    cultivo_options = sorted(set(cultivo_options))
    selected_cultivo = st.sidebar.selectbox("Selecciona un Cultivo", options=cultivo_options, index=cultivo_options.index("todos"))
    if selected_cultivo != "todos":
        df_filtered = df_comp[df_comp["Cultivos Asociados"].str.lower().str.contains(selected_cultivo)]
    else:
        df_filtered = df_comp
    st.subheader(f"Productos por sistema productivo: {selected_cultivo.capitalize() if selected_cultivo != 'todos' else 'Todos'}")
    if df_filtered.empty:
        st.write("No hay inventario para los filtros seleccionados.")
    else:
        for idx, row in df_filtered.iterrows():
            card_html = f"""
            <div class="product-card">
                <h3 style="margin-bottom: 8px;">Producto N° {row['Producto N°']}</h3>
                <p style="margin: 4px 0;"><strong>Descripción:</strong> {row['Descripción']}</p>
                <p style="margin: 4px 0;"><strong>Cultivos Asociados:</strong> {row['Cultivos Asociados']}</p>
                <p style="margin: 4px 0;"><strong>Avance Identificado:</strong> {row['Avance Identificado']}</p>
                <p style="margin: 4px 0;"><strong>Estado:</strong> {row['Estado']}</p>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

# ---------------------------------------------------
# VISTA: Análisis de red por cultivos (sección ya existente)
# ---------------------------------------------------
elif view_option == "Análisis de red por cultivos":
    st.header("Análisis de Red por Cultivos")
    TS = ui.tabs(options=['Banano/ASBAMA', 'Banano/Augura', 'Café', 'Arroz', 'Caña de azucar'], default_value='Banano/ASBAMA', key="network_tabs")
    viz_type = st.selectbox("Elige el tipo de visualización", ["Estática (Matplotlib)", "Interactiva (PyVis)"], index=1)
    # (Aquí incluirías el resto de las funciones de red e interpretación que ya tienes implementadas...)
    # Se omite aquí por brevedad, ya que no afecta la funcionalidad del folleto.

# ---------------------------------------------------
# VISTA: Brief: Caracterización ME (sección ya existente)
# ---------------------------------------------------
elif view_option == "Brief: Caracterización ME":
    st.header("Caracterización de modelos de extensión", divider='blue')
    st.write("Brief: Caracterización ME")
    tabs = ui.tabs(options=['Caña de azucar', 'Café', 'Banano', 'Arroz'], default_value='Caña de azucar', key="brief_tabs")
    if tabs == 'Caña de azucar':
        image_names = [f"Caña de azucar {i}" for i in range(1, 7)]
        image_files = [f"data/CanaAzucar{i}.jpg" for i in range(1, 7)]
        st.write("## Galería de Caña de azucar")
        cols = st.columns(3)
        for idx, img in enumerate(image_files):
            st.image(img, caption=image_names[idx], use_container_width=True)
    elif tabs == 'Café':
        image_names = [f"Café {i}" for i in range(1, 8)]
        image_files = [f"data/Cafe{i}.jpg" for i in range(1, 8)]
        st.write("## Galería de Café")
        cols = st.columns(3)
        for idx, img in enumerate(image_files):
            st.image(img, caption=image_names[idx], use_container_width=True)
    elif tabs == 'Banano':
        image_names = [f"Banano {i}" for i in range(1, 7)]
        image_files = [f"data/banano{i}.jpg" for i in range(1, 7)]
        st.write("## Galería de Banano")
        cols = st.columns(3)
        for idx, img in enumerate(image_files):
            st.image(img, caption=image_names[idx], use_container_width=True)
    elif tabs == 'Arroz':
        image_names = [f"Arroz {i}" for i in range(1, 6)]
        image_files = [f"data/Arroz{i}.jpg" for i in range(1, 6)]
        st.write("## Galería de Arroz")
        cols = st.columns(3)
        for idx, img in enumerate(image_files):
            st.image(img, caption=image_names[idx], use_container_width=True)

# ---------------------------------------------------
# VISTA: Folleto Banano (nueva opción)
# ---------------------------------------------------
elif view_option == "Folleto Banano":
    st.header("Folleto Banano")
    paginated_gallery("Banano", 6, "Banano", state_key="banano_page")

st.divider()
st.markdown('*Copyright (C) 2025. Alliance CIAT Bioversity*')
st.caption('**Authors: Alejandro Taborda, (latabordaa@unal.edu.co), Jeimar Tapasco, Armando Muñoz, Luisa Perez, Deissy Martinez**')
st.image('data/cas.png', use_container_width=True)
