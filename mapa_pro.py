import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from datetime import datetime
import pytz
import os

# 1. DICCIONARIO DE ISLAS (Para el filtrado)
MUNICIPIOS_ISLAS = {
    # Provincia 35
    'Arrecife': 'Lanzarote', 'Haría': 'Lanzarote', 'San Bartolomé': 'Lanzarote', 'Teguise': 'Lanzarote', 'Tías': 'Lanzarote', 'Tinajo': 'Lanzarote', 'Yaiza': 'Lanzarote',
    'Antigua': 'Fuerteventura', 'Betancuria': 'Fuerteventura', 'La Oliva': 'Fuerteventura', 'Pájara': 'Fuerteventura', 'Puerto del Rosario': 'Fuerteventura', 'Tuineje': 'Fuerteventura',
    'Agaete': 'Gran Canaria', 'Agüimes': 'Gran Canaria', 'Artenara': 'Gran Canaria', 'Arucas': 'Gran Canaria', 'Firgas': 'Gran Canaria', 'Gáldar': 'Gran Canaria', 'Ingenio': 'Gran Canaria', 'Mogán': 'Gran Canaria', 'Moya': 'Gran Canaria', 'Las Palmas de Gran Canaria': 'Gran Canaria', 'San Bartolomé de Tirajana': 'Gran Canaria', 'Santa Brígida': 'Gran Canaria', 'Santa Lucía de Tirajana': 'Gran Canaria', 'Santa María de Guía de Gran Canaria': 'Gran Canaria', 'Tejeda': 'Gran Canaria', 'Telde': 'Gran Canaria', 'Teror': 'Gran Canaria', 'Valleseco': 'Gran Canaria', 'Valsequillo de Gran Canaria': 'Gran Canaria', 'Vega de San Mateo': 'Gran Canaria',
    # Provincia 38
    'Adeje': 'Tenerife', 'Arafo': 'Tenerife', 'Arico': 'Tenerife', 'Arona': 'Tenerife', 'Buenavista del Norte': 'Tenerife', 'Candelaria': 'Tenerife', 'Fasnia': 'Tenerife', 'Garachico': 'Tenerife', 'Granadilla de Abona': 'Tenerife', 'La Guancha': 'Tenerife', 'Guía de Isora': 'Tenerife', 'Icod de los Vinos': 'Tenerife', 'La Matanza de Acentejo': 'Tenerife', 'La Orotava': 'Tenerife', 'Puerto de la Cruz': 'Tenerife', 'Los Realejos': 'Tenerife', 'El Rosario': 'Tenerife', 'San Cristóbal de La Laguna': 'Tenerife', 'San Juan de la Rambla': 'Tenerife', 'San Miguel de Abona': 'Tenerife', 'Santa Cruz de Tenerife': 'Tenerife', 'Santa Úrsula': 'Tenerife', 'Santiago del Teide': 'Tenerife', 'El Sauzal': 'Tenerife', 'Los Silos': 'Tenerife', 'Tacoronte': 'Tenerife', 'El Tanque': 'Tenerife', 'Tegueste': 'Tenerife', 'La Victoria de Acentejo': 'Tenerife', 'Vilaflor de Chasna': 'Tenerife',
    'Agulo': 'La Gomera', 'Alajeró': 'La Gomera', 'Hermigua': 'La Gomera', 'San Sebastián de la Gomera': 'La Gomera', 'Valle Gran Rey': 'La Gomera', 'Vallehermoso': 'La Gomera',
    'Barlovento': 'La Palma', 'Breña Alta': 'La Palma', 'Breña Baja': 'La Palma', 'Fuencaliente de la Palma': 'La Palma', 'Garafía': 'La Palma', 'Los Llanos de Aridane': 'La Palma', 'El Paso': 'La Palma', 'Puntagorda': 'La Palma', 'Puntallana': 'La Palma', 'San Andrés y Sauces': 'La Palma', 'Santa Cruz de la Palma': 'La Palma', 'Tazacorte': 'La Palma', 'Tijarafe': 'La Palma', 'Villa de Mazo': 'La Palma',
    'Frontera': 'El Hierro', 'El Pinar de El Hierro': 'El Hierro', 'Valverde': 'El Hierro'
}

def obtener_datos_canarias():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    cabeceras = {'User-Agent': 'Mozilla/5.0'}
    print("🛰️  1. Conectando con la API del Ministerio...")
    
    try:
        respuesta = requests.get(url, headers=cabeceras, timeout=20)
        datos_sucios = respuesta.json()
        df = pd.DataFrame(datos_sucios['ListaEESSPrecio'])
        
        df_canarias = df[df['IDProvincia'].isin(['35', '38'])].copy()
        
        # Limpieza de datos (Tu lógica original)
        for col in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
            df_canarias[col] = pd.to_numeric(df_canarias[col].str.replace(',', '.'), errors='coerce')
        
        df_canarias = df_canarias.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])
        return df_canarias
    except Exception as e:
        print(f"❌ Error al obtener datos: {e}")
        return None

def actualizar_historico(df):
    print("💾 3. Guardando histórico de precios...")
    archivo_csv = 'historico_precios.csv'
    fecha_hoy = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
    
    df_historico_dia = df[['Municipio', 'Rótulo', 'Localidad', 'IDProvincia', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
    df_historico_dia['Fecha'] = fecha_hoy
    
    if os.path.exists(archivo_csv):
        historico_previo = pd.read_csv(archivo_csv)
        historico_actualizado = pd.concat([historico_previo, df_historico_dia]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Localidad'])
    else:
        historico_actualizado = df_historico_dia
        
    historico_actualizado.to_csv(archivo_csv, index=False)
    print(f"📈 ¡Histórico actualizado! Registros totales: {len(historico_actualizado)}")

def generar_visualizacion(df):
    if df is None: return
    print("🌍 2. Generando mapa y tabla de precios...")
    
    # --- CONFIGURACIÓN HORA Y KPIs ---
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    texto_variacion = ""
    if os.path.exists('historico_precios.csv'):
        try:
            hist = pd.read_csv('historico_precios.csv')
            fechas = sorted(hist['Fecha'].unique())
            if len(fechas) > 1:
                ultima_fecha = fechas[-2]
                media_ayer = hist[hist['Fecha'] == ultima_fecha]['Precio Gasolina 95 E5'].mean()
                media_hoy = df['Precio Gasolina 95 E5'].mean()
                diff = media_hoy - media_ayer
                color_v = "red" if diff > 0 else "green"
                flecha = "▲" if diff > 0 else "▼"
                texto_variacion = f'<b style="color:{color_v}; margin-left:15px;">{flecha} {abs(diff):.3f}€ vs ayer</b>'
        except: pass

    # --- MAPA Y CAPAS POR ISLA ---
    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')
    
    islas_nombres = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    capas_islas = {}
    
    for nombre in islas_nombres:
        # Creamos la capa (FeatureGroup) y el Cluster dentro de ella
        grupo = folium.FeatureGroup(name=nombre)
        cluster = MarkerCluster().add_to(grupo)
        capas_islas[nombre] = cluster
        grupo.add_to(mapa)

    # Lógica de colores dinámica global
    umbral_verde = df['Precio Gasolina 95 E5'].quantile(0.25)

    for _, fila in df.iterrows():
        # Determinar color
        if fila['Precio Gasolina 95 E5'] <= umbral_verde:
            color_pin = "green"
        elif fila['Precio Gasolina 95 E5'] < 1.40:
            color_pin = "orange"
        else:
            color_pin = "red"
        
        texto_popup = f"<b>{fila['Rótulo']}</b><br>G95: {fila['Precio Gasolina 95 E5']} €<br>Diésel: {fila['Precio Gasoleo A']} €"
        
        marker = folium.Marker(
            location=[fila['Latitud'], fila['Longitud (WGS84)']],
            popup=folium.Popup(texto_popup, max_width=300),
            icon=folium.Icon(color=color_pin, icon='info-sign')
        )
        
        # Asignar a su isla
        isla_donde_va = MUNICIPIOS_ISLAS.get(fila['Municipio'], 'Otros')
        if isla_donde_va in capas_islas:
            marker.add_to(capas_islas[isla_donde_va])

    folium.LayerControl(collapsed=False).add_to(mapa)

    # --- TABLA Y PLANTILLA FINAL ---
    top_10 = df[['Rótulo', 'Localidad', 'Precio Gasolina 95 E5']].nsmallest(10, 'Precio Gasolina 95 E5')
    html_tabla = top_10.to_html(classes='table table-dark table-striped', index=False, justify='center')
    
    plantilla_final = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <div style="padding: 20px; font-family: sans-serif;">
        <h1 style="text-align:center;">Canarias Gas Tracker ⛽</h1>
        <p style="text-align:center;">🕒 Última actualización: <b>{ahora} (Hora Canaria)</b> {texto_variacion}</p>
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
    
    if datos is not None and not datos.empty:
        generar_visualizacion(datos)
        actualizar_historico(datos)
        print("✅ Todo actualizado correctamente.")
    else:
        print("⚠️ No se pudieron obtener datos hoy.")