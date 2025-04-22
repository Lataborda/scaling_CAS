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
import numpy as np
if not hasattr(np, 'Inf'):
    np.Inf = np.inf

# Resto de tu código...


# ---------------------------
# Configuración general
# ---------------------------
st.set_page_config(page_title="Dashboard Integral", layout="wide")

# CSS personalizado para forzar un tema claro en contenedores, tarjetas y tablas
custom_css = """
<style>
/* Forzar fondo y texto en la sección principal */
.css-18e3th9, .css-1d391kg {
    background-color: #FFFFFF !important;
    color: #000000 !important;
}

/* Forzar fondo y texto en las tarjetas personalizadas de inventario */
.product-card {
    background-color: #f9f9f9 !important;
    color: #000000 !important;
    border: 1px solid #ddd !important;
    padding: 16px !important;
    border-radius: 8px !important;
    margin-bottom: 16px !important;
    box-shadow: 2px 2px 6px rgba(0,0,0,0.1) !important;
}

/* Forzar color del título dentro de las tarjetas */
.product-card h3 {
    color: #000000 !important;
}

/* Forzar fondo y texto en las tablas */
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

# Selección de vista en el Sidebar
view_option = st.sidebar.selectbox("Selecciona la vista:", 
                                   ["Inventario", "Análisis de red por cultivos","Brief: Caracterización ME"])

# ===================================================
# VISTA 1: Inventario (Productos filtrados por cultivo)
# ===================================================
if view_option == "Inventario":
    st.header("Inventario de entregables proyecto CAS", divider='blue')
    
    # Ruta al CSV de inventario
    csv_path = "data/Inventary2.csv"
    try:
        df = pd.read_csv(csv_path, delimiter=';')
    except Exception as e:
        st.error("Error al leer el CSV de inventario: " + str(e))
        st.stop()
    
    # Convertir las columnas necesarias a string
    for col in ["Componente", "Resultado", "Cultivos Asociados", "Producto N°"]:
        df[col] = df[col].astype(str)
    
    # --- Sidebar: Filtros de Inventario ---
    st.sidebar.header("Filtros de Inventario")
    
    # Filtro por Componente
    componentes = sorted(df["Componente"].dropna().unique())
    selected_componente = st.sidebar.selectbox("Selecciona un Componente", componentes)
    df_comp = df[df["Componente"] == selected_componente]
    
    # Filtro por Resultado (del componente seleccionado)
    resultados = sorted(df_comp["Resultado"].dropna().unique())
    selected_resultado = st.sidebar.selectbox("Selecciona un Resultado", resultados)
    df_comp = df_comp[df_comp["Resultado"] == selected_resultado]
    
    # Generar opciones de cultivos a partir de la columna "Cultivos Asociados"
    cultivo_options = ["todos"]
    for cell in df_comp["Cultivos Asociados"]:
        for cultivo in cell.split(","):
            cultivo_options.append(cultivo.strip().lower())
    cultivo_options = sorted(set(cultivo_options))
    
    # Selector de cultivo, con opción "todos" por defecto
    selected_cultivo = st.sidebar.selectbox(
        "Selecciona un Cultivo",
        options=cultivo_options,
        index=cultivo_options.index("todos")
    )
    
    # Filtrar por cultivo si se selecciona algo distinto de "todos"
    if selected_cultivo != "todos":
        df_filtered = df_comp[df_comp["Cultivos Asociados"].str.lower().str.contains(selected_cultivo)]
    else:
        df_filtered = df_comp
    
    st.subheader(f"Productos por sistema productivo: {selected_cultivo.capitalize() if selected_cultivo != 'todos' else 'Todos'}")
    
    if df_filtered.empty:
        st.write("No hay inventario para los filtros seleccionados.")
    else:
        # Mostrar cada producto en una tarjeta utilizando la clase .product-card
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

# ===================================================
# VISTA 2: Análisis de Red por Cultivos (con opción de visualización)
# ===================================================
elif view_option == "Análisis de red por cultivos":
    st.header("Análisis de Red por Cultivos", divider='blue')
    
    # Pestañas para alternar entre las redes
    TS = ui.tabs(options=['Banano/ASBAMA', 'Banano/Augura', 'Café', 'Arroz', 'Caña de azucar'], 
                   default_value='Banano/ASBAMA', key="network_tabs")
    
    # Selector para elegir el tipo de visualización
    viz_type = st.selectbox("Elige el tipo de visualización", 
                            ["Estática (Matplotlib)", "Interactiva (PyVis)"],
                            index=1)  # Por defecto la interactiva
    
    # Función para dibujar la red de forma estática (Matplotlib)
    def draw_network_static(csv_file, title):
        try:
            df_net = pd.read_csv(csv_file, sep=None, engine='python', on_bad_lines='skip')
        except Exception as e:
            st.error(f"Error al leer el CSV de red ({title}): " + str(e))
            st.stop()
        if 'Periodicidad de la Interacción' in df_net.columns:
            df_net.rename(columns={'Periodicidad de la Interacción': 'Peso'}, inplace=True)
        G = nx.DiGraph()
        for _, row in df_net.iterrows():
            G.add_edge(row['Origen'], row['Destino'], weight=row['Peso'], label=row['Tipo de Interacción'])
        degree = dict(G.degree(weight='weight'))
        node_size = [degree[node] * 300 for node in G.nodes()]
        pos = nx.spring_layout(G, seed=42, k=1.5)
        color_map = []
        for node in G.nodes():
            if "Productores" in node:
                color_map.append("lightblue")
            elif "Asistentes" in node or "Extensionistas" in node:
                color_map.append("lightgreen")
            elif "Investigadores" in node:
                color_map.append("plum")
            elif "CENIBANANO" in node:
                color_map.append("lightcoral")
            elif "Servicio" in node:
                color_map.append("orange")
            else:
                color_map.append("gray")
        edge_width = [G[u][v]['weight'] / 2 for u, v in G.edges()]
        def wrap_labels(labels, width=20):
            return {node: "\n".join(textwrap.wrap(node, width)) for node in labels}
        wrapped_labels = wrap_labels({node: node for node in G.nodes()})
        plt.figure(figsize=(18, 14))
        nx.draw(G, pos, with_labels=True, labels=wrapped_labels, node_color=color_map, node_size=node_size,
                font_size=10, font_weight="bold", edge_color="gray", width=edge_width)
        edge_labels = nx.get_edge_attributes(G, 'label')
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=10, font_color="darkred", rotate=True)
        plt.title(title, fontsize=16)
        st.pyplot(plt)
    
    # Función para dibujar la red interactiva usando PyVis
    def draw_network_interactive(csv_file, title):
        try:
            df_net = pd.read_csv(csv_file, sep=None, engine='python', on_bad_lines='skip')
        except Exception as e:
            st.error(f"Error al leer el CSV de red ({title}): " + str(e))
            st.stop()
        if 'Periodicidad de la Interacción' in df_net.columns:
            df_net.rename(columns={'Periodicidad de la Interacción': 'Peso'}, inplace=True)
        G = nx.DiGraph()
        for _, row in df_net.iterrows():
            G.add_edge(row['Origen'], row['Destino'], weight=row['Peso'], label=row['Tipo de Interacción'])
        net = Network(height="700px", width="100%", bgcolor="#FFFFFF", font_color="black")
        for node in G.nodes():
            net.add_node(node, label=node, title=node)
        for u, v, data in G.edges(data=True):
            net.add_edge(u, v, value=data.get('weight', 1), title=data.get('label', ''))
        net.set_options("""
        var options = {
          "physics": {
            "barnesHut": {
              "gravitationalConstant": -8000,
              "centralGravity": 0.3,
              "springLength": 95,
              "springConstant": 0.04,
              "damping": 0.09,
              "avoidOverlap": 0
            },
            "minVelocity": 0.75
          }
        }
        """)
        net.write_html("network_interactive.html", open_browser=False, notebook=False)
        with open("network_interactive.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        st.subheader(title)
        components.html(html_content, height=750, scrolling=True)
    
    # Función para mostrar la interpretación de la red
    def show_interpretation(csv_file, title):
        st.subheader(f"Interpretación del Análisis de Red ({title})")
        try:
            # Leer el CSV usando la primera fila como encabezado y separador ';'
            df_interpret = pd.read_csv(csv_file, sep=';', header=0, engine='python')
            # Si la primera fila es idéntica a los encabezados, eliminarla
            if df_interpret.iloc[0].tolist() == list(df_interpret.columns):
                df_interpret = df_interpret.iloc[1:]
                df_interpret.reset_index(drop=True, inplace=True)
        except Exception as e:
            st.error(f"Error al leer el CSV de interpretación ({title}): " + str(e))
        else:
            # Convertir el DataFrame a HTML sin índice
            html_table = df_interpret.to_html(index=False)
            st.markdown(html_table, unsafe_allow_html=True)
    
    # Mostrar según la pestaña seleccionada y el tipo de visualización
    if TS == "Banano/ASBAMA":
        if viz_type == "Estática (Matplotlib)":
            draw_network_static("data/ASBAMA.csv", "Red del Sistema de Extensión del Banano (ASBAMA) - Estática")
        else:
            draw_network_interactive("data/ASBAMA.csv", "Red del Sistema de Extensión del Banano (ASBAMA) - Interactiva")
        show_interpretation("data/ASBAMA_interpretacion_analisis_red.csv", "ASBAMA")
    elif TS == "Banano/Augura":
        if viz_type == "Estática (Matplotlib)":
            draw_network_static("data/AUGURA.csv", "Red del Sistema de Extensión del Banano (Augura) - Estática")
        else:
            draw_network_interactive("data/AUGURA.csv", "Red del Sistema de Extensión del Banano (Augura) - Interactiva")
        show_interpretation("data/interpretacion_augura.csv", "Augura")
    elif TS == "Café":
        if viz_type == "Estática (Matplotlib)":
            draw_network_static("data/red_productiva_cafe.csv", "Red Productiva del Café - Estática")
        else:
            draw_network_interactive("data/red_productiva_cafe.csv", "Red Productiva del Café - Interactiva")
        show_interpretation("data/FNC_interpretacion.csv", "Café")
    elif TS == "Arroz":
        if viz_type == "Estática (Matplotlib)":
            draw_network_static("data/redes_fedearroz.csv", "Red del Sistema de Extensión del Arroz - Estática")
        else:
            draw_network_interactive("data/redes_fedearroz.csv", "Red del Sistema de Extensión del Arroz - Interactiva")
        show_interpretation("data/Fedearroz_Centralidades.csv", "Arroz")
    elif TS == "Caña de azucar":
        if viz_type == "Estática (Matplotlib)":
            draw_network_static("data/red cana.csv", "Red del Sistema de Extensión de Caña de azucar - Estática")
        else:
            draw_network_interactive("data/red cana.csv", "Red del Sistema de Extensión de Caña de azucar - Interactiva")
        show_interpretation("data/Centralidades_Caña.csv", "Caña de azucar")

# ===================================================
# VISTA 3: Brief: caracterización 
# ===================================================
elif view_option == "Brief: Caracterización ME":
    st.header("Caracterización de modelos de extensión", divider='blue')

    tabs = ui.tabs(options=['Caña de azucar', 'Café', 'Banano', 'Arroz'], 
                   default_value='Caña de azucar', key="brief_tabs")

    images_dict = {
        'Caña de azucar': [f"data/CanaAzucar{i}.jpg" for i in range(1, 7)],
        'Café': [f"data/Cafe{i}.jpg" for i in range(1, 8)],
        'Banano': [f"data/banano{i}.jpg" for i in range(1, 7)],
        'Arroz': [f"data/Arroz{i}.jpg" for i in range(1, 6)],
    }

    if f"img_index_{tabs}" not in st.session_state:
        st.session_state[f"img_index_{tabs}"] = 0

    current_images = images_dict[tabs]
    index_key = f"img_index_{tabs}"
    current_index = st.session_state[index_key]

    # ---- Botones ARRIBA de la imagen ----
    col_top1, col_top2, col_top3 = st.columns([1, 6, 1])
    with col_top1:
        if st.button("⬅ Página anterior", key=f"top_prev_{tabs}"):
            if st.session_state[index_key] > 0:
                st.session_state[index_key] -= 1
    with col_top3:
        if st.button("Página siguiente ➡", key=f"top_next_{tabs}"):
            if st.session_state[index_key] < len(current_images) - 1:
                st.session_state[index_key] += 1

    # Imagen
    st.image(current_images[current_index], use_container_width=True, caption=f"{tabs} ({current_index + 1} / {len(current_images)})")
    
    

    # ---- Botones ABAJO de la imagen ----
    col_bot1, col_bot2, col_bot3 = st.columns([1, 6, 1])
    with col_bot1:
        if st.button("⬅ Página anterior", key=f"bot_prev_{tabs}"):
            if st.session_state[index_key] > 0:
                st.session_state[index_key] -= 1
    with col_bot3:
        if st.button("Página siguiente ➡", key=f"bot_next_{tabs}"):
            if st.session_state[index_key] < len(current_images) - 1:
                st.session_state[index_key] += 1

st.divider()
st.markdown('*Copyright (C) 2025. Alliance CIAT Bioversity*')
st.caption('**Authors: Alejandro Taborda, (latabordaa@unal.edu.co), Jeimar Tapasco, Armando Muñoz, Luisa Perez, Deissy Martinez**')
st.image('data/cas.png')
