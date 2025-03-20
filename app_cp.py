import streamlit as st
import folium
import geopandas as gpd
import os
import pandas as pd
from streamlit_folium import folium_static

# Definir la ruta de la carpeta de datos
data_path = os.path.join(os.getcwd(), "data")

@st.cache_data
def listar_archivos_geojson():
    """ Lista los archivos GeoJSON disponibles por estado """
    estados_path = os.path.join(data_path, "Estados")
    return {f.split(".")[0]: os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")}

@st.cache_data
def cargar_paqueterias():
    """ Carga los códigos postales de cada paquetería en caché """
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
        ruta = os.path.join(data_path, "Coberturas_Paqueterias", archivo)
        if os.path.exists(ruta):
            df = pd.read_excel(ruta, sheet_name=hoja)
            df.rename(columns=dic, inplace=True, errors="ignore")
            if "CODIGO POSTAL" in df.columns:
                paqueterias[nombre] = df[["CODIGO POSTAL"]]
    return paqueterias

@st.cache_data
def cargar_tabla_cp_estado():
    """ Carga la tabla que asocia códigos postales con estados """
    ruta = os.path.join(data_path, "codigos_postales_estados.xlsx")  # Asegúrate de tener este archivo
    if os.path.exists(ruta):
        return pd.read_excel(ruta)  # Debe tener columnas: 'CODIGO POSTAL' y 'ESTADO'
    return pd.DataFrame()

@st.cache_data
def cargar_estado(archivo_geojson):
    """ Carga solo el GeoJSON del estado relevante """
    return gpd.read_file(archivo_geojson)

# Cargar lista de estados, paqueterías y tabla de CP-Estado
archivos_geojson = listar_archivos_geojson()
paqueterias = cargar_paqueterias()
tabla_cp_estado = cargar_tabla_cp_estado()

# Interfaz en Streamlit
st.title("Mapa de Cobertura de Paqueterías")

# Selección de paquetería con botones
paqueteria_seleccionada = st.radio("Selecciona una paquetería:", list(paqueterias.keys()), horizontal=True)

# Ingreso de Código Postal
cp_manual = st.text_input("Ingresa un Código Postal:")

# Crear mapa base vacío
m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

# Procesar solo si hay código postal ingresado
if cp_manual:
    # Buscar en qué paqueterías está disponible
    paqueterias_con_cobertura = [nombre for nombre, df in paqueterias.items() if cp_manual in df["CODIGO POSTAL"].astype(str).values]

    if paqueterias_con_cobertura:
        # Buscar el estado correspondiente al CP
        estado_fila = tabla_cp_estado[tabla_cp_estado["CODIGO POSTAL"].astype(str) == cp_manual]

        if not estado_fila.empty:
            estado = estado_fila["ESTADO"].values[0]  # Nombre del estado asociado

            # Verificar si el estado tiene un GeoJSON
            estado_archivo = archivos_geojson.get(estado)

            if estado_archivo:
                # Cargar solo el estado relevante
                gdf_estado = cargar_estado(estado_archivo)

                # Filtrar códigos postales de la paquetería seleccionada dentro del estado
                gdf_paqueteria = gdf_estado[gdf_estado["d_codigo"].astype(str).isin(paqueterias[paqueteria_seleccionada]["CODIGO POSTAL"].astype(str))]

                # Agregar la cobertura al mapa
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

                # Agregar marcador del CP ingresado
                gdf_cp_manual = gdf_estado[gdf_estado["d_codigo"].astype(str) == cp_manual]
                if not gdf_cp_manual.empty:
                    centroide = gdf_cp_manual.geometry.to_crs(epsg=4326).centroid.iloc[0]
                    folium.Marker(
                        location=[centroide.y, centroide.x],
                        popup=f"Código Postal {cp_manual}\nCobertura en: {', '.join(paqueterias_con_cobertura)}",
                        icon=folium.Icon(color="red", icon="info-sign")
                    ).add_to(m)
            else:
                st.error(f"⚠️ No se encontró un GeoJSON para el estado '{estado}' asociado al CP {cp_manual}.")
        else:
            st.error(f"⚠️ No se encontró un estado para el código postal {cp_manual}.")
    else:
        st.error(f"⚠️ El código postal {cp_manual} no tiene cobertura en ninguna paquetería.")

# Mostrar el mapa en Streamlit
folium_static(m)
