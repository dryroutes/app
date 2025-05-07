import streamlit as st
import networkx as nx
import requests
import zipfile
import json
import gzip
from io import BytesIO
import folium
from folium import Marker, PolyLine
from streamlit_folium import st_folium

st.set_page_config(page_title="DryRoutes", layout="wide")
st.title("🛣️ Rutas seguras ante riesgo de inundación")

# --- CONFIGURACIÓN ---

# URL del ZIP en tu repositorio de GitHub (reemplaza si cambias el nombre)
ZIP_URL = "https://huggingface.co/datasets/dryroutes/grafo/resolve/main/grafo_tiny.zip"

# --- CARGA DEL GRAFO DESDE ZIP ---

@st.cache_data(show_spinner="Descargando y reconstruyendo el grafo...")
def cargar_grafo_desde_zip(url_zip):
    response = requests.get(url_zip)
    z = zipfile.ZipFile(BytesIO(response.content))

    G = nx.DiGraph()

    # Cargar nodos
    for filename in sorted(z.namelist()):
        if filename.startswith("nodos") and filename.endswith(".json.gz"):
            with z.open(filename) as f:
                with gzip.open(f, "rt", encoding="utf-8") as gzf:
                    nodos = json.load(gzf)
                    for nodo in nodos:
                        G.add_node(nodo["id"], x=nodo["x"], y=nodo["y"])

    # Cargar aristas
    for filename in sorted(z.namelist()):
        if filename.startswith("aristas") and filename.endswith(".json.gz"):
            with z.open(filename) as f:
                with gzip.open(f, "rt", encoding="utf-8") as gzf:
                    aristas = json.load(gzf)
                    for a in aristas:
                        G.add_edge(a["origen"], a["destino"],
                                   costo_total=a.get("costo_total", 1),
                                   tiempo=a.get("tiempo", 1),
                                   distancia=a.get("distancia", 1))

    return G

# --- CARGAR EL GRAFO ---

with st.spinner("Cargando grafo..."):
    G = cargar_grafo_desde_zip(ZIP_URL)
st.success(f"Grafo cargado con {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas.")

# --- INTERFAZ DE USUARIO ---

nodos_disponibles = list(G.nodes)
origen = st.selectbox("📍 Nodo de origen", nodos_disponibles)
destino = st.selectbox("🏁 Nodo de destino", nodos_disponibles)
criterio = st.radio("¿Qué quieres minimizar?", ["costo_total", "tiempo"])

if st.button("Calcular ruta"):
    try:
        ruta = nx.shortest_path(G, source=origen, target=destino, weight=criterio)
        longitud = nx.shortest_path_length(G, source=origen, target=destino, weight=criterio)
        st.success(f"Ruta encontrada con {len(ruta)} nodos. {criterio} total: {longitud:.2f}")

        # --- VISUALIZACIÓN DEL MAPA ---
        m = folium.Map(location=[G.nodes[origen]["y"], G.nodes[origen]["x"]], zoom_start=13)
        coordenadas = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]

        # Marcar origen y destino
        Marker(coordenadas[0], tooltip="Origen").add_to(m)
        Marker(coordenadas[-1], tooltip="Destino").add_to(m)

        # Dibujar ruta
        PolyLine(coordenadas, color="blue", weight=5).add_to(m)
        st_folium(m, width=1000, height=600)

    except nx.NetworkXNoPath:
        st.error("❌ No se pudo calcular la ruta: no hay camino entre los nodos seleccionados.")
