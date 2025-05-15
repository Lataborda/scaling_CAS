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
st.set_page_config(page_title="Scaling CAS", layout="wide")

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
                                   ["Capacidad de Modelos de extensión", "Inventario", "Análisis de red por cultivos","Brief: Caracterización ME"])

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
    st.image(current_images[current_index], width=700, caption=f"{tabs} ({current_index + 1} / {len(current_images)})")
    
    
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
# ===================================================
# VISTA 4: Capacidad modelos de extensión 
# ===================================================

elif view_option == "Capacidad de Modelos de extensión":
    st.header("Capacidad de Modelos de extensión")

    # ==== CSS para tarjetas y paneles ====
    st.markdown("""
    <style>
      /* …tus reglas .info-card y .progress-bar… */
    
      /* NÚMEROS SIEMPRE EN NEGRO */
      div.info-card h1,
      div.info-card h2 {
          color: #000000 !important;
      }
      /* CAFÉ: texto en tarjetas de panel-izquierdo y panel-derecho */
      .panel-left .card p,
      .panel-left .card p strong {
          color: #000000 !important;
      }
      .panel-right .card p,
      .panel-right .card p strong {
          color: #FFFFFF !important;
      }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("""
    <style>
    /* Estilos generales de tarjetas */
    div.info-card {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: 1px solid #dddddd !important;
        border-radius: 8px !important;
        padding: 16px !important;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.1) !important;
        margin-bottom: 16px !important;
    }
    div.info-card h2, div.info-card h1 { margin: 0 !important; }
    div.info-card p { margin: 4px 0 8px !important; font-size:14px !important; color:#555 !important; }
    div.info-card small { display:block !important; margin-top:4px !important; font-size:12px !important; color:#777 !important; }
    div.info-card .progress-bar-container { background:#eee !important; border-radius:4px !important; overflow:hidden !important; height:20px !important; margin-top:6px !important; }
    div.info-card .progress-bar { height:100% !important; background:#4CAF50 !important; text-align:right !important; padding-right:4px !important; color:#fff !important; font-size:12px !important; line-height:20px !important; }

    /* Estilos panel café (FNC) */
    .panel-left, .panel-right { padding:20px; border-radius:12px; margin-bottom:24px; }
    .panel-left { background:#FFF3E0; } .panel-left h3 { color:#BF360C; font-size:24px; margin-bottom:16px; }
    .panel-right { background:#33691E; } .panel-right h3 { color:#F1F8E9; font-size:24px; margin-bottom:16px; }
    .card { display:flex; align-items:center; margin-bottom:12px; }
    .card .icon { font-size:32px; margin-right:12px; }
    .panel-left .icon { color:#BF360C; } .panel-right .icon { color:#F1F8E9; }
    .panel-left p, .panel-right p { margin:0; line-height:1.3; }
    .panel-right p { color:#F1F8E9; }
    </style>
    """, unsafe_allow_html=True)

    # ==== Pestañas para alternar vistas ====
    import streamlit_shadcn_ui as ui
    TF = ui.tabs(
        options=['Café','Banano/ASBAMA', 'Banano/Augura', 'Arroz', 'Caña de azucar'],
        default_value='Banano/ASBAMA',
        key='network_tabs'
    )

    if TF == "Banano/ASBAMA":
        # ==== CSS específico para Banano ====
        st.markdown("""
        <style>
        /* Tarjetas Banano: fondo crema suave */
        .banana-card {
          background-color: #FFFDE7 !important;
          border: 1px solid #FFEE58 !important;
        }
        .banana-card h2 {
          font-size: 28px !important;
          margin-bottom: 4px !important;
        }
        .banana-card p {
          font-size: 13px !important;
          color: #666 !important;
        }
        .banana-card small {
          color: #999 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        st.subheader("🍌 Potenciales beneficiarios y áreas sembradas – ASBAMA")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            <div class="info-card banana-card">
              <h2>🍌 142</h2>
              <p>Pot. beneficiarios:<br><strong>4 Comercializadoras</strong></p>
              <small>• 4 especialistas (16)<br>• 2–3 ingenieros c/u (48)<br>• 1 admin/100 ha (78)</small>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
            <div class="info-card banana-card">
              <h2>👩‍🌾 1 733</h2>
              <p>Pot. beneficiarios:<br><strong>Pequeños Prod.</strong></p>
              <small>• 1–5 ha p/ productor (prom.)<br>• Cooperativas locales</small>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown("""
            <div class="info-card banana-card">
              <h2>📋 1 875</h2>
              <p>Total pot. beneficiarios</p>
              <small>Suma: comercializadoras + pequeños productores</small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            st.markdown("""
            <div class="info-card">
              <h2>7 800 ha</h2>
              <p>Área sembrada<br>Grandes Comercializadoras</p>
              <small>7 800 ha gestionadas por 4 empresas</small>
            </div>
            """, unsafe_allow_html=True)
        with a2:
            st.markdown("""
            <div class="info-card">
              <h2>5 200 ha</h2>
              <p>Área sembrada<br>Pequeños Productores</p>
              <small>5 200 ha gestionadas por productores pequeños</small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        mc = st.columns(1)[0]
        with mc:
            st.markdown("""
            <div class="info-card">
              <p style="font-size:14px; color:#555; margin-bottom:4px;">Meta anual de productores</p>
              <h1 style="font-size:48px; line-height:1; margin-bottom:4px;">500 <span style="font-size:16px; vertical-align:super;">Productores</span></h1>
              <small>Base 100% = 500 productores</small>

              <div style="margin-top:12px;">
                <label style="font-size:14px; color:#333;">• Grandes Comercializadoras (142/500)</label>
                <div class="progress-bar-container">
                  <div class="progress-bar" style="width:26.8%;">26.8%</div>
                </div>
              </div>
              <div style="margin-top:12px;">
                <label style="font-size:14px; color:#333;">• Pequeños Productores (358/500)</label>
                <div class="progress-bar-container">
                  <div class="progress-bar" style="width:73.2%;">73.2%</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        # … justo después de tus 3 tarjetas banana-card …

         # — luego de tus 3 banana-cards …
        st.markdown("<br>", unsafe_allow_html=True)

        # ==== Tarjeta Meta hectáreas año 1 (estilo igual a meta de productores) ====
        meta_area = 3459
        total_area = 7800 + 5200  # = 13_000
        pct = meta_area / total_area * 100  # ≈26.6

        mcol = st.columns(1)[0]
        with mcol:
            st.markdown(f"""
            <div class="info-card banana-card">
              <p style="font-size:14px; color:#555555; margin-bottom:4px;">
                Meta: Total hectáreas a cubrir en el proyecto
              </p>
              <h1 style="font-size:48px; line-height:1; margin-bottom:4px;">
                {meta_area:,} <span style="font-size:16px; vertical-align:super;">ha</span>
              </h1>
              <small>Base 100% area total de ASBAMA= {total_area:,} ha</small>

              <div style="margin-top:12px;">
                <div class="progress-bar-container">
                  <div class="progress-bar" style="width:{pct:.1f}%;">{pct:.1f}%</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            

    elif TF == "Banano/Augura":
        st.info("🔨 En construcción para Banano/Augura")

    elif TF == "Café":
        # --- Panel FNC (Café) ---
        colA, colB = st.columns(2)
        with colA:
            st.markdown("""
            <div class="panel-left">
              <h3>Meta anual de beneficiarios: Campañas planeadas por FNC en CSICAP</h3>
              <div class="card"><div class="icon">🎯</div><p><strong>80 000 productores</strong> (20 000/año)</p></div>
              <div class="card"><div class="icon">👥</div><p><strong>1 000 extensionistas</strong> / campaña</p></div>
              <div class="card"><div class="icon">📈</div><p><strong>20 productores</strong> / extensionista/año</p></div>
            </div>
            """, unsafe_allow_html=True)

        with colB:
            st.markdown("""
            <div class="panel-right">
              <h3>Índice: Capacidad-cobertura total de extensionistas de FNC</h3>
              <div class="card"><div class="icon">🤝</div><p><strong>1 450 extensionistas</strong></p></div>
              <div class="card"><div class="icon">☕</div><p><strong>550 000 productores</strong> en territorio nacional</p></div>
              <div class="card"><div class="icon">⏰</div><p><strong>Dedicados full-time</strong> a extensión</p></div>
              <div class="card"><div class="icon">👨‍🌾</div><p><strong>379 productores</strong> por extensionista</p></div>
            </div>
            """, unsafe_allow_html=True)

        # --- Tarjeta adicional de área total a cubrir ---
        st.markdown("""
        <style>
        /* Forzar texto en negro sobre la tarjeta de proyecto CSICAP */
        div.project-meta-card h3,
        div.project-meta-card p,
        div.project-meta-card p strong,
        div.project-meta-card em {
            color: #000000 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card project-meta-card"
             style="border-radius:12px;
                    border:2px solid #ccc;
                    padding:20px;
                    background-color:#f5f5f5;
                    width:100%;max-width:700px;
                    box-shadow:2px 2px 10px rgba(0,0,0,0.1);
                    font-family:Arial,sans-serif;
                    margin:30px auto;">
        
          <h3 style="margin-top:0;">Meta: Área total a cubrir en proyecto CSICAP</h3>
        
          <p><strong>Año 1:</strong><br>
          📍 <span style="font-size:1.5em;
                         font-weight:bold;
                         color:#2E7D32;">
            31 200 ha estimadas
          </span><br>
          <span style="font-size:0.9em; color:#555;">
            (Meta de <strong>20 000 productores</strong> × 1,56 ha promedio)<br>
            <em>Nota: 1,56 ha es el promedio del área por productor</em>
          </span></p>
        
          <p><strong>Proyección a 4 años:</strong><br>
          📈 <span style="font-size:1.3em;
                         font-weight:bold;
                         color:#33691E;">
            124 800 ha estimadas
          </span><br>
          <span style="font-size:0.9em; color:#555;">
            (Valor estimado al término del proyecto)
          </span></p>
        
          <p><strong>Meta oficial del proyecto:</strong><br>
          🎯 <span style="font-size:1.2em;
                         font-weight:bold;
                         color:#D84315;">
            254 400 hectáreas
          </span></p>
        
          <p><strong>Avance estimado:</strong> 49,1%</p>
          <div style="background-color:#ddd;
                      border-radius:20px;
                      overflow:hidden;
                      height:20px;
                      margin-top:5px;">
            <div style="width:49.1%;
                        background-color:#E53935;
                        height:100%;
                        text-align:center;
                        color:white;
                        font-weight:bold;">
              49.1%
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info(f"🔨 En construcción para {TF}")
    

st.divider()
st.markdown('*Copyright (C) 2025. Alliance CIAT Bioversity*')
st.caption('**Authors: Alejandro Taborda, (latabordaa@unal.edu.co), Jeimar Tapasco, Armando Muñoz, Luisa Perez, Deissy Martinez**')
st.image('data/cas.png', width=250)
