import os
import pandas as pd
import geopandas as gpd

# Simulación de las rutas necesarias (ajustar según entorno real)
data_path = os.path.join(os.getcwd(), "data")
estados_path = os.path.join(data_path, "Estados")
archivos_geojson = [os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")]

# Cargar los geojson optimizado con cacheo
@st.cache_data
def cargar_geometria_total():
    gdf_lista = [gpd.read_file(archivo) for archivo in archivos_geojson]
    return gpd.GeoDataFrame(pd.concat(gdf_lista, ignore_index=True))

# Cargar coberturas
@st.cache_data
def cargar_excel(nombre_archivo, hoja=None):
    ruta = os.path.join(data_path, "Coberturas_Paqueterias", nombre_archivo)
    if not os.path.exists(ruta):
        return pd.DataFrame()
    try:
        df = pd.read_excel(ruta, sheet_name=hoja)
        if isinstance(df, dict):
            return pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

# Renombrar y limpiar cobertura
@st.cache_data
def preparar_coberturas():
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
        if not df.empty:
            df.rename(columns=dic, inplace=True, errors="ignore")
            if "CODIGO POSTAL" in df.columns:
                paqueterias[nombre] = df[["CODIGO POSTAL"]]
    return paqueterias

# Ejecutar para validar
gdf_total = cargar_geometria_total()
paqueterias = preparar_coberturas()

import streamlit as st
import folium
from streamlit_folium import folium_static

st.title("📦 Mapa de Cobertura de Paqueterías (Optimizado)")

# Selección
paqueteria_seleccionada = st.selectbox("Selecciona una paquetería:", list(paqueterias.keys()))
cp_manual = st.text_input("Ingresa un Código Postal:")

if cp_manual:
    # Obtener solo CP de la paquetería seleccionada
    df_cobertura = paqueterias[paqueteria_seleccionada]
    codigos_paquete = set(df_cobertura["CODIGO POSTAL"].astype(str))

    # Mostrar solo si el CP está dentro
    paqueterias_con_cobertura = [nombre for nombre, df in paqueterias.items()
                                 if cp_manual in df["CODIGO POSTAL"].astype(str).values]

    # Crear mapa
    m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

    # Filtrar geodataframe solo para ese CP
    gdf_cp = gdf_total[gdf_total["d_codigo"].astype(str) == cp_manual]
    if not gdf_cp.empty:
        # Centrar en el CP ingresado
        centroide = gdf_cp.geometry.to_crs(epsg=4326).centroid.iloc[0]
        folium.Marker(
            location=[centroide.y, centroide.x],
            popup=f"Código Postal {cp_manual}\nCobertura en: {', '.join(paqueterias_con_cobertura)}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

        # Mostrar polígono si pertenece a la paquetería
        if cp_manual in codigos_paquete:
            folium.GeoJson(
                gdf_cp,
                name=f"Cobertura {paqueteria_seleccionada}",
                style_function=lambda x: {
                    'fillColor': 'blue',
                    'color': 'black',
                    'weight': 0.5,
                    'fillOpacity': 0.3
                }
            ).add_to(m)

    folium_static(m)

    # Mostrar texto resumen
    st.success(f"📍 El código postal **{cp_manual}** tiene cobertura en: {', '.join(paqueterias_con_cobertura) if paqueterias_con_cobertura else 'Ninguna'}")
