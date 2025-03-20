import streamlit as st
import folium
import geopandas as gpd
import os
import pandas as pd
from streamlit_folium import folium_static

# Definir la ruta de la carpeta de datos
data_path = os.path.join(os.getcwd(), "data")

# Cargar archivos GeoJSON en caché (sin generar mapas)
@st.cache_data
def cargar_geojson():
    estados_path = os.path.join(data_path, "Estados")
    archivos_geojson = [os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")]
    return {archivo: gpd.read_file(archivo) for archivo in archivos_geojson}

@st.cache_data
def cargar_excel(nombre_archivo, hoja=None):
    ruta = os.path.join(data_path, "Coberturas_Paqueterias", nombre_archivo)
    if not os.path.exists(ruta):
        return pd.DataFrame()
    try:
        df = pd.read_excel(ruta, sheet_name=hoja)
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    except Exception:
        return pd.DataFrame()

@st.cache_data
def cargar_paqueterias():
    paqueterias = {}
    archivos = [
        ("Estafeta", "COBERTURA_ESTAFETA.xlsx", "Hoja1"),
        ("Paquete_Express", "COBERTURA_PAQUETEXPRESS.xlsx", "Hoja1"),
        ("JyT", "COBERTURA_J&T.xlsx", "Hoja1"),
        ("Almex", "COBERTURA_ALMEX.xlsx", "Hoja1"),
        ("PMM", "COBERTURA_PMM.xlsx", "Hoja1")
    ]
    dic = {"C.P.": "CODIGO POSTAL", "C.P Destino": "CODIGO POSTAL", "POSTAL": "CODIGO POSTAL"}
    for nombre, archivo, hoja in archivos:
        df = cargar_excel(archivo, hoja)
        df.rename(columns=dic, inplace=True, errors="ignore")
        if "CODIGO POSTAL" in df.columns:
            paqueterias[nombre] = df[["CODIGO POSTAL"]]
    return paqueterias

# Cargar datos en caché
geojson_data = cargar_geojson()
paqueterias = cargar_paqueterias()

# Interfaz en Streamlit
st.title("Mapa de Cobertura de Paqueterías")

# Selección de paquetería con botones
paqueteria_seleccionada = st.radio("Selecciona una paquetería:", list(paqueterias.keys()), horizontal=True)

# Ingreso de Código Postal
cp_manual = st.text_input("Ingresa un Código Postal:")

# Crear mapa base vacío
m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

# Agregar cobertura de la paquetería seleccionada dinámicamente
if paqueteria_seleccionada in paqueterias:
    gdf_total = gpd.GeoDataFrame(pd.concat(geojson_data.values(), ignore_index=True))
    gdf_paqueteria = gdf_total[gdf_total["d_codigo"].astype(str).isin(
        paqueterias[paqueteria_seleccionada]["CODIGO POSTAL"].astype(str)
    )]

    folium.GeoJson(
        gdf_paqueteria,
        name=f"Cobertura {paqueteria_seleccionada}",
        style_function=lambda x: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.3
        }
    ).add_to(m)

# Si hay código postal, solo agregar el marcador sin regenerar el mapa
if cp_manual:
    gdf_cp_manual = gdf_total[gdf_total["d_codigo"].astype(str) == cp_manual]
    if not gdf_cp_manual.empty:
        centroide = gdf_cp_manual.geometry.to_crs(epsg=4326).centroid.iloc[0]
        folium.Marker(
            location=[centroide.y, centroide.x],
            popup=f"Código Postal {cp_manual}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

# Mostrar el mapa en Streamlit
folium_static(m)
