import streamlit as st
import folium
import geopandas as gpd
import os
import pandas as pd
from streamlit_folium import folium_static

# Definir la ruta de la carpeta de datos
data_path = os.path.join(os.getcwd(), "data")

# Ruta de geojsons\estados_path = os.path.join(data_path, "Estados")

# Cargar archivos GeoJSON desde la carpeta "Estados"
@st.cache_data
def cargar_geojson():
    data_path = os.path.join(os.getcwd(), "data")
    estados_path = os.path.join(data_path, "Estados")
    archivos_geojson = [os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")]
    gdf_lista = [gpd.read_file(archivo) for archivo in archivos_geojson]
    return gpd.GeoDataFrame(pd.concat(gdf_lista, ignore_index=True))


gdf_total = cargar_geojson()

# Función para cargar archivos Excel con validación
@st.cache_data
def cargar_excel(nombre_archivo, hoja=None):
    ruta = os.path.join(data_path, "Coberturas_Paqueterias", nombre_archivo)
    if not os.path.exists(ruta):
        st.error(f"⚠️ Archivo no encontrado: {ruta}")
        return pd.DataFrame()
    try:
        df = pd.read_excel(ruta, sheet_name=hoja)
        if isinstance(df, dict):
            st.error(f"⚠️ {nombre_archivo} no tiene una hoja válida.")
            return pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"⚠️ Error al cargar {nombre_archivo}: {e}")
        return pd.DataFrame()

# Cargar coberturas de paqueterías con validación
paqueterias = {}
archivos = [
    ("Estafeta", "COBERTURA_ESTAFETA.xlsx", "Hoja1"),
    ("Paquete_Express", "COBERTURA_PAQUETEXPRESS.xlsx", "Hoja1"),
    ("JyT", "COBERTURA_J&T.xlsx", "Hoja1"),
    ("Almex", "COBERTURA_ALMEX.xlsx", "Hoja1"),
    ("PMM", "COBERTURA_PMM.xlsx", "Hoja1")
]

for nombre, archivo, hoja in archivos:
    df = cargar_excel(archivo, hoja)
    if df.empty:
        st.error(f"⚠️ {nombre} no tiene datos o falló la carga.")
    else:
        paqueterias[nombre] = df

# Renombrar columnas con validación
dic = {"C.P.": "CODIGO POSTAL", "C.P Destino": "CODIGO POSTAL", "POSTAL": "CODIGO POSTAL"}
for nombre, df in paqueterias.items():
    if df.empty:
        st.error(f"⚠️ {nombre} no tiene datos válidos.")
    else:
        df.rename(columns=dic, inplace=True, errors="ignore")
        if "CODIGO POSTAL" in df.columns:
            paqueterias[nombre] = df[["CODIGO POSTAL"]]
        else:
            st.error(f"⚠️ {nombre} no contiene la columna 'CODIGO POSTAL'.")

# Interfaz en Streamlit
st.title("Mapa de Cobertura de Paqueterías")

# Selección de paquetería
paqueteria_seleccionada = st.selectbox("Selecciona una paquetería:", list(paqueterias.keys()))

# Ingreso de Código Postal
cp_manual = st.text_input("Ingresa un Código Postal:")

if cp_manual:
    cp_manual = cp_manual.strip()

    # Convertir columna una sola vez
    gdf_total["d_codigo"] = gdf_total["d_codigo"].astype(str)

    # --- Filtrar geojson solo con los CP de esa paquetería
    codigos_paq = paqueterias[paqueteria_seleccionada]["CODIGO POSTAL"].astype(str).unique()
    gdf_paqueteria = gdf_total[gdf_total["d_codigo"].isin(codigos_paq)]

    # --- Filtrar CP manual ingresado
    gdf_cp_manual = gdf_total[gdf_total["d_codigo"] == cp_manual]

    if gdf_cp_manual.empty:
        st.warning("❌ El código postal ingresado no se encuentra en el mapa.")
    else:
        # Validar cobertura
        paqueterias_con_cobertura = [
            nombre for nombre, df in paqueterias.items()
            if cp_manual in df["CODIGO POSTAL"].astype(str).values
        ]

        # Crear mapa
        m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

        # 🔹 Cobertura total de la paquetería
        folium.GeoJson(
            gdf_paqueteria,
            name=f"Cobertura {paqueteria_seleccionada}",
            style_function=lambda x: {
                'fillColor': 'blue',
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0.2
            }
        ).add_to(m)

        # 🔸 Sombreado más fuerte del CP seleccionado
        folium.GeoJson(
            gdf_cp_manual,
            name=f"Código Postal {cp_manual}",
            style_function=lambda x: {
                'fillColor': 'red',
                'color': 'darkred',
                'weight': 1,
                'fillOpacity': 0.5
            }
        ).add_to(m)

        # 🔹 Marcador en el centro del CP
        centroide = gdf_cp_manual.geometry.to_crs(epsg=4326).centroid.iloc[0]
        folium.Marker(
            location=[centroide.y, centroide.x],
            popup=f"CP {cp_manual}\nCobertura: {', '.join(paqueterias_con_cobertura) if paqueterias_con_cobertura else 'Ninguna'}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

        folium_static(m)

        # Mostrar texto con cobertura
        st.success(f"✅ El código postal **{cp_manual}** tiene cobertura en: **{', '.join(paqueterias_con_cobertura) if paqueterias_con_cobertura else 'Ninguna'}**")
