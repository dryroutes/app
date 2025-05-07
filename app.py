import streamlit as st
import networkx as nx
import requests
import gzip
import json
from io import BytesIO
import folium
from folium import Marker, PolyLine
from streamlit_folium import st_folium

st.set_page_config(page_title="DryRoutes", layout="wide")
st.title("🛟 Rutas seguras ante riesgo de inundación")

# ----------------- CARGA DEL GRAFO -----------------
@st.cache_data
def cargar_grafo_comprimido(url_nodos, url_aristas):
    G = nx.DiGraph()

    # Cargar nodos (solo con id, x, y)
    response_n = requests.get(url_nodos)
    with gzip.open(BytesIO(response_n.content), "rt", encoding="utf-8") as f:
        nodos = json.load(f)
    for nodo in nodos:
        G.add_node(nodo["id"], x=nodo["x"], y=nodo["y"])

    # Cargar aristas
    response_e = requests.get(url_aristas)
    with gzip.open(BytesIO(response_e.content), "rt", encoding="utf-8") as f:
        aristas = json.load(f)
    for arista in aristas:
        G.add_edge(arista["origen"], arista["destino"],
                   costo_total=arista["costo_total"],
                   tiempo=arista["tiempo"],
                   distancia=arista["distancia"],
                   altura_media=arista.get("altura_media", 0))

    return G

# ----------------- URLs de Hugging Face -----------------
URL_NODOS = "https://huggingface.co/datasets/dryroutes/grafo/resolve/main/nodos.json.gz"
URL_ARISTAS = "https://huggingface.co/datasets/dryroutes/grafo/resolve/main/aristas.json.gz"

# ----------------- Cargar y mostrar -----------------
with st.spinner("Cargando grafo desde Hugging Face..."):
    G = cargar_grafo_comprimido(URL_NODOS, URL_ARISTAS)
    st.success(f"Grafo cargado con {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas.")

# ----------------- Selección de nodos -----------------
nodos = list(G.nodes())
nodo_origen = st.selectbox("📍 Nodo de origen", nodos)
nodo_destino = st.selectbox("🏁 Nodo de destino", nodos, index=min(1, len(nodos)-1))
peso = st.radio("¿Qué quieres minimizar?", ["costo_total", "tiempo"], horizontal=True)

# ----------------- Cálculo y visualización de ruta -----------------
if st.button("Calcular ruta"):
    try:
        ruta = nx.shortest_path(G, source=nodo_origen, target=nodo_destino, weight=peso)
        st.success(f"Ruta encontrada con {len(ruta)} nodos.")

        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]
        dist_total = sum(G[u][v]["distancia"] for u, v in zip(ruta[:-1], ruta[1:]))
        tiempo_total = sum(G[u][v]["tiempo"] for u, v in zip(ruta[:-1], ruta[1:]))

        st.markdown(f"🛣️ **Distancia total**: `{dist_total:.1f} m`")
        st.markdown(f"⏱️ **Tiempo estimado**: `{tiempo_total:.1f} min`")

        m = folium.Map(location=coords[0], zoom_start=14)
        PolyLine(coords, color="blue", weight=5).add_to(m)
        Marker(coords[0], tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
        Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)
        st_folium(m, width=800, height=500)

    except Exception as e:
        st.error(f"No se pudo calcular la ruta: {e}")

        # Mostrar nodos aunque no haya ruta
        try:
            coord_origen = (G.nodes[nodo_origen]["y"], G.nodes[nodo_origen]["x"])
            coord_destino = (G.nodes[nodo_destino]["y"], G.nodes[nodo_destino]["x"])

            m = folium.Map(location=coord_origen, zoom_start=14)
            Marker(coord_origen, tooltip="Origen", icon=folium.Icon(color="green")).add_to(m)
            Marker(coord_destino, tooltip="Destino", icon=folium.Icon(color="red")).add_to(m)
            st_folium(m, width=800, height=500)
        except:
            st.warning("No se pudieron ubicar los nodos en el mapa.")
