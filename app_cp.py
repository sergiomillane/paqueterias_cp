import streamlit as st
import folium
import geopandas as gpd
import os
import pandas as pd
from streamlit_folium import folium_static

# ================== CONFIGURACIÓN DE RUTA =====================
data_path = os.path.join(os.getcwd(), "data")
estados_path = os.path.join(data_path, "Estados")

# ================== FUNCIÓN: Cargar GeoJSON de forma optimizada =====================
@st.cache_data
def cargar_geojson_simplificado():
    archivos_geojson = [os.path.join(estados_path, f) for f in os.listdir(estados_path) if f.endswith(".geojson")]
    gdfs = []
    for archivo in archivos_geojson:
        gdf = gpd.read_file(archivo)
        gdf["geometry"] = gdf["geometry"].simplify(tolerance=0.002, preserve_topology=True)
        gdfs.append(gdf)
    return gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))

gdf_total = cargar_geojson_simplificado()

# ================== FUNCIÓN: Cargar Excel =====================
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

# ================== Cargar coberturas de paqueterías =====================
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
    if not df.empty:
        df.rename(columns={"C.P.": "CODIGO POSTAL", "C.P Destino": "CODIGO POSTAL", "POSTAL": "CODIGO POSTAL"}, inplace=True, errors="ignore")
        if "CODIGO POSTAL" in df.columns:
            paqueterias[nombre] = df[["CODIGO POSTAL"]]
        else:
            st.error(f"⚠️ {nombre} no contiene la columna 'CODIGO POSTAL'.")
    else:
        st.error(f"⚠️ {nombre} no tiene datos válidos.")

# ================== INTERFAZ STREAMLIT =====================
st.title("📦 Mapa de Cobertura de Paqueterías")

# Selección de paquetería
paqueteria_seleccionada = st.selectbox("Selecciona una paquetería:", list(paqueterias.keys()))

# Ingreso de Código Postal
cp_manual = st.text_input("Ingresa un Código Postal:")

if cp_manual and paqueteria_seleccionada:
    codigos_cp = paqueterias[paqueteria_seleccionada]["CODIGO POSTAL"].astype(str)
    
    # Combina los CP de cobertura con el CP manual para evitar errores
    codigos_a_mostrar = pd.Series(codigos_cp.tolist() + [cp_manual]).dropna().unique()

    gdf_paqueteria = gdf_total[gdf_total["d_codigo"].astype(str).isin(codigos_a_mostrar)]

    # Verificar en qué paqueterías hay cobertura
    paqueterias_con_cobertura = [
        nombre for nombre, df in paqueterias.items()
        if cp_manual in df["CODIGO POSTAL"].astype(str).values
    ]

    # Crear mapa
    m = folium.Map(location=[23.6345, -102.5528], zoom_start=5)

    # Agregar capa de cobertura con sombreado optimizado
    folium.GeoJson(
        gdf_paqueteria,
        name=f"Cobertura {paqueteria_seleccionada}",
        style_function=lambda x: {
            'fillColor': 'blue',
            'color': 'black',
            'weight': 0.3,
            'fillOpacity': 0.2
        }
    ).add_to(m)

    # Agregar marcador del CP ingresado
    gdf_cp_manual = gdf_total[gdf_total["d_codigo"].astype(str) == cp_manual]
    if not gdf_cp_manual.empty:
        centroide = gdf_cp_manual.geometry.to_crs(epsg=4326).centroid.iloc[0]
        folium.Marker(
            location=[centroide.y, centroide.x],
            popup=f"Código Postal {cp_manual}\nCobertura en: {', '.join(paqueterias_con_cobertura)}",
            icon=folium.Icon(color="red", icon="info-sign")
        ).add_to(m)

    # Mostrar mapa
    folium_static(m)

    # Mostrar info adicional
    st.write(f"📍 El código postal **{cp_manual}** tiene cobertura en: {', '.join(paqueterias_con_cobertura) if paqueterias_con_cobertura else 'Ninguna paquetería encontrada'}")
