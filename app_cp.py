import streamlit as st
import folium
import geopandas as gpd
import os
import pandas as pd
from streamlit_folium import folium_static

# Definir la ruta de la carpeta de datos
data_path = os.path.join(os.getcwd(), "data")

# Cargar archivos GeoJSON desde la carpeta "Estados"
estados_path = os.path.join(data_path, "Estados")
archivos_geojson = [os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")]

gdf_lista = [gpd.read_file(archivo) for archivo in archivos_geojson]
gdf_total = gpd.GeoDataFrame(pd.concat(gdf_lista, ignore_index=True))

# Cargar coberturas de paqueterías
def cargar_excel(nombre_archivo, hoja=None):
    return pd.read_excel(os.path.join(data_path, "Coberturas_Paqueterias", nombre_archivo), sheet_name=hoja)

paqueterias = {
    "Estafeta": cargar_excel("COBERTURA_ESTAFETA.xlsx"),
    "Paquete_Express": cargar_excel("COBERTURA_PAQUETEXPRESS.xlsx", "COBERTURA COMERCIAL"),
    "JyT": cargar_excel("COBERTURA_J&T.xlsx", "CP"),
    "Almex": cargar_excel("COBERTURA_ALMEX.xlsx", "Hoja1"),
    "PMM": cargar_excel("COBERTURA_PMM.xlsx")
}

dic = {"C.P.": "CODIGO POSTAL", "C.P Destino": "CODIGO POSTAL", "POSTAL": "CODIGO POSTAL"}
for nombre, df in paqueterias.items():
    df.rename(columns=dic, inplace=True)
    paqueterias[nombre] = df[["CODIGO POSTAL"]]

# Interfaz en Streamlit
st.title("Mapa de Cobertura de Paqueterías")

# Selección de paquetería
paqueteria_seleccionada = st.selectbox("Selecciona una paquetería:", list(paqueterias.keys()))

# Ingreso de Código Postal
cp_manual = st.text_input("Ingresa un Código Postal:")

if cp_manual:
    # Filtrar cobertura de la paquetería seleccionada
    gdf_paqueteria = gdf_total[gdf_total["d_codigo"].astype(str).isin(
        paqueterias[paqueteria_seleccionada]["CODIGO POSTAL"].astype(str)
    )]

    # Verificar paqueterías disponibles
    paqueterias_con_cobertura = [
        nombre for nombre, df in paqueterias.items()
        if cp_manual in df["CODIGO POSTAL"].astype(str).values
    ]

    # Crear mapa
    m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

    # Agregar cobertura al mapa
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

    # Marcar ubicación del Código Postal
    gdf_cp_manual = gdf_total[gdf_total["d_codigo"].astype(str) == cp_manual]
    if not gdf_cp_manual.empty:
        centroide = gdf_cp_manual.geometry.centroid.iloc[0]
        folium.Marker(
            location=[centroide.y, centroide.x],
            popup=f"Código Postal {cp_manual}\nCobertura en: {', '.join(paqueterias_con_cobertura)}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    # Mostrar mapa en Streamlit
    folium_static(m)

    # Mostrar paqueterías con cobertura
    st.write(f"El código postal {cp_manual} tiene cobertura en: {', '.join(paqueterias_con_cobertura) if paqueterias_con_cobertura else 'Ninguna paquetería encontrada'}")
