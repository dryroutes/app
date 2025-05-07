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

# ----------------- CARGA DEL GRAFO DESDE HF -----------------
@st.cache_data
def cargar_grafo_comprimido(url_nodos, url_aristas):
    G = nx.DiGraph()

    # Nodos
    response_nodos = requests.get(url_nodos)
    with gzip.open(BytesIO(response_nodos.content), "rt", encoding="utf-8") as f:
        nodos = json.load(f)
    for nodo in nodos:
        G.add_node(nodo["id"], x=nodo["x"], y=nodo["y"],
                   altura=nodo["altura"], peligrosidad=nodo["peligrosidad"])

    # Aristas
    response_aristas = requests.get(url_aristas)
    with gzip.open(BytesIO(response_aristas.content), "rt", encoding="utf-8") as f:
        aristas = json.load(f)
    for arista in aristas:
        G.add_edge(arista["origen"], arista["destino"],
                   costo_total=arista["costo_total"],
                   tiempo=arista["tiempo"],
                   distancia=arista["distancia"],
                   altura_media=arista["altura_media"])
    return G

# ----------------- CARGA AUTOMÁTICA DE TU GRAFO -----------------
URL_NODOS = "https://huggingface.co/datasets/dryroutes/grafo/resolve/main/nodos.json.gz"
URL_ARISTAS = "https://huggingface.co/datasets/dryroutes/grafo/resolve/main/aristas.json.gz"

with st.spinner("Cargando grafo desde Hugging Face..."):
    G = cargar_grafo_comprimido(URL_NODOS, URL_ARISTAS)
    st.success(f"Grafo cargado con {G.number_of_nodes()} nodos y {G.number_of_edges()} aristas.")

# ----------------- INTERFAZ DE RUTAS -----------------
nodos = list(G.nodes())
nodo_origen = st.selectbox("📍 Nodo de origen", nodos)
nodo_destino = st.selectbox("🏁 Nodo de destino", nodos, index=min(1, len(nodos)-1))
peso = st.radio("¿Qué quieres minimizar?", ["costo_total", "tiempo"], horizontal=True)

if st.button("Calcular ruta segura"):
    try:
        ruta = nx.shortest_path(G, source=nodo_origen, target=nodo_destino, weight=peso)
        st.success(f"Ruta encontrada con {len(ruta)} nodos.")

        # Coordenadas de la ruta
        coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in ruta]
        total_dist = sum(G[u][v]["distancia"] for u, v in zip(ruta[:-1], ruta[1:]))
        total_tiempo = sum(G[u][v]["tiempo"] for u, v in zip(ruta[:-1], ruta[1:]))

        st.markdown(f"🛣️ **Distancia total**: `{total_dist:.1f} m`")
        st.markdown(f"⏱️ **Tiempo estimado**: `{total_tiempo:.1f} min`")

        # Mapa
        m = folium.Map(location=coords[0], zoom_start=14)
        PolyLine(coords, color="blue", weight=5).add_to(m)
        Marker(coords[0], tooltip="Origen", icon=folium.Icon(color='green')).add_to(m)
        Marker(coords[-1], tooltip="Destino", icon=folium.Icon(color='red')).add_to(m)
        st_folium(m, width=800, height=500)

    except Exception as e:
        st.error(f"No se pudo calcular la ruta: {e}")
