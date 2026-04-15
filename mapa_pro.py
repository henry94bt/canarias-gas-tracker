import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster # <--- Esto es lo que evita que se "pete"
from datetime import datetime
import pytz # Para la hora exacta de Canarias

def obtener_datos_canarias():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    cabeceras = {'User-Agent': 'Mozilla/5.0'}
    print("🛰️  1. Conectando con la API del Ministerio...")
    
    try:
        respuesta = requests.get(url, headers=cabeceras)
        datos_sucios = respuesta.json()
        df = pd.DataFrame(datos_sucios['ListaEESSPrecio'])
        
        df_canarias = df[df['IDProvincia'].isin(['35', '38'])].copy()
        
        # Limpieza de datos
        df_canarias['Precio Gasolina 95 E5'] = pd.to_numeric(df_canarias['Precio Gasolina 95 E5'].str.replace(',', '.'), errors='coerce')
        df_canarias['Precio Gasoleo A'] = pd.to_numeric(df_canarias['Precio Gasoleo A'].str.replace(',', '.'), errors='coerce')
        df_canarias['Latitud'] = pd.to_numeric(df_canarias['Latitud'].str.replace(',', '.'), errors='coerce')
        df_canarias['Longitud (WGS84)'] = pd.to_numeric(df_canarias['Longitud (WGS84)'].str.replace(',', '.'), errors='coerce')
        
        df_canarias = df_canarias.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])
        return df_canarias
    except Exception as e:
        print(f"❌ Error al obtener datos: {e}")
        return None
import os

def actualizar_historico(df):
    print("💾 3. Guardando histórico de precios...")
    
    # Nos quedamos solo con las columnas clave para el análisis
    columnas_clave = ['Fecha', 'Rótulo', 'Localidad', 'IDProvincia', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']
    
    # Creamos una copia y le añadimos la fecha de la extracción
    df_historico = df.copy()
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    df_historico['Fecha'] = fecha_hoy
    
    # Filtramos para tener solo lo que nos interesa
    df_historico = df_historico[columnas_clave]
    
    # Ruta del archivo maestro
    archivo_csv = 'historico_precios.csv'
    
    # Si el archivo ya existe, lo abrimos, le pegamos los datos nuevos debajo y guardamos
    if os.path.exists(archivo_csv):
        historico_previo = pd.read_csv(archivo_csv)
        # Concatenamos y evitamos duplicados por si el robot corre dos veces el mismo día
        historico_actualizado = pd.concat([historico_previo, df_historico]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Localidad'])
    else:
        # Si es el primer día, este dataframe es nuestro archivo base
        historico_actualizado = df_historico
        
    historico_actualizado.to_csv(archivo_csv, index=False)
    print(f"📈 ¡Histórico actualizado! Total de registros: {len(historico_actualizado)}")

def generar_visualizacion(df):
    if df is None: return
    
    print("🌍 2. Generando mapa y tabla de precios...")
    
    # Configuramos la hora real de Canarias
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')

    # AGRUPAR PUNTOS (Clusters): Para que no se vea cargado
    cluster = MarkerCluster(name="Gasolineras").add_to(mapa)

    for _, fila in df.iterrows():
        # Lógica de colores dinámica (Usa el 25% más barato de la isla para el verde)
        umbral_verde = df['Precio Gasolina 95 E5'].quantile(0.25)
        
        if fila['Precio Gasolina 95 E5'] <= umbral_verde:
            color_pin = "green"
        elif fila['Precio Gasolina 95 E5'] < 1.40:
            color_pin = "orange"
        else:
            color_pin = "red"
        
        texto = f"<b>{fila['Rótulo']}</b><br>G95: {fila['Precio Gasolina 95 E5']} €<br>Diésel: {fila['Precio Gasoleo A']} €"
        
        folium.Marker(
            location=[fila['Latitud'], fila['Longitud (WGS84)']],
            popup=folium.Popup(texto, max_width=300),
            icon=folium.Icon(color=color_pin, icon='info-sign')
        ).add_to(cluster) # <--- Se añade al cluster

    # TABLA HTML
    top_10 = df[['Rótulo', 'Localidad', 'Precio Gasolina 95 E5']].nsmallest(10, 'Precio Gasolina 95 E5')
    html_tabla = top_10.to_html(classes='table table-dark table-striped', index=False, justify='center')
    
    plantilla_final = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <div style="padding: 20px; font-family: sans-serif;">
        <h1 style="text-align:center;">Canarias Gas Tracker ⛽</h1>
        <p style="text-align:center;">🕒 Última actualización: <b>{ahora} (Hora Canaria)</b></p>
        <hr>
        <div class="container">
            <div class="row">
                <div class="col-md-12">
                    <h3 class="mb-3">🏆 TOP 10 Gasolineras más económicas (G95)</h3>
                    {html_tabla}
                </div>
            </div>
        </div>
    </div>
    """
    
    mapa.get_root().html.add_child(folium.Element(plantilla_final))
    mapa.save("index.html")
    print(f"✅ Hecho a las {ahora}")

if __name__ == "__main__":
    datos = obtener_datos_canarias()
    
    # Comprobamos si realmente tenemos datos antes de seguir
    if datos is not None and not datos.empty:
        generar_visualizacion(datos)
        actualizar_historico(datos)
        print("✅ Todo actualizado correctamente.")
    else:
        print("⚠️ No se pudieron obtener datos hoy. El servidor del Ministerio no responde.")