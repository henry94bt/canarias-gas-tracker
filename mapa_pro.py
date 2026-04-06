import requests
import pandas as pd
import folium

def obtener_datos_canarias():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    print("🛰️  1. Conectando con la API del Ministerio...")
    
    try:
        respuesta = requests.get(url)
        datos_sucios = respuesta.json()
        df = pd.DataFrame(datos_sucios['ListaEESSPrecio'])
        
        # Filtramos Canarias (35 y 38)
        df_canarias = df[df['IDProvincia'].isin(['35', '38'])].copy()
        
        # Limpieza de precios y coordenadas (con el fix de errores que vimos)
        df_canarias['Precio Gasolina 95 E5'] = pd.to_numeric(df_canarias['Precio Gasolina 95 E5'].str.replace(',', '.'), errors='coerce')
        df_canarias['Latitud'] = pd.to_numeric(df_canarias['Latitud'].str.replace(',', '.'), errors='coerce')
        df_canarias['Longitud (WGS84)'] = pd.to_numeric(df_canarias['Longitud (WGS84)'].str.replace(',', '.'), errors='coerce')
        
        # Quitamos filas sin datos esenciales
        df_canarias = df_canarias.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])
        return df_canarias
    except Exception as e:
        print(f"❌ Error al obtener datos: {e}")
        return None

def generar_visualizacion(df):
    if df is None: return
    
    print("🌍 2. Generando mapa y tabla de precios...")
    
    # Usamos CartoDB Positron para evitar el error 403 Access Blocked
    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')

    # Añadir los pines de colores
    for _, fila in df.iterrows():
        # Lógica de colores según precio
        if fila['Precio Gasolina 95 E5'] < 1.25:
            color_pin = "green"
        elif fila['Precio Gasolina 95 E5'] < 1.35:
            color_pin = "orange"
        else:
            color_pin = "red"
        
        texto = f"<b>{fila['Rótulo']}</b><br>Precio: {fila['Precio Gasolina 95 E5']} €"
        folium.Marker(
            location=[fila['Latitud'], fila['Longitud (WGS84)']],
            popup=folium.Popup(texto, max_width=300),
            icon=folium.Icon(color=color_pin, icon='info-sign')
        ).add_to(mapa)

    # CREAR TABLA HTML (El Top 10 más barato)
    top_10 = df[['Rótulo', 'Localidad', 'Precio Gasolina 95 E5']].nsmallest(10, 'Precio Gasolina 95 E5')
    
    # Convertimos el Top 10 a una tabla bonita de HTML
    html_tabla = top_10.to_html(classes='table table-dark table-striped', index=False, justify='center')
    
    # Unimos el mapa con la tabla en el mismo archivo
    plantilla_final = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <div style="padding: 20px; font-family: sans-serif;">
        <h1 style="text-align:center;">Canarias Gas Tracker ⛽</h1>
        <p style="text-align:center;">Análisis de precios en tiempo real</p>
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
    
    # Insertamos el diseño arriba del mapa
    mapa.get_root().html.add_child(folium.Element(plantilla_final))

    # Guardar
    mapa.save("mapa_pro.html")
    print("✅ ¡Hecho! Abre 'mapa_pro.html' para ver el resultado.")

if __name__ == "__main__":
    datos = obtener_datos_canarias()
    generar_visualizacion(datos)