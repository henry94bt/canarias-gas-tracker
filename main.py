import requests
import pandas as pd
import folium

def obtener_datos_canarias():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    print("🛰️  1. Conectando con la API...")
    respuesta = requests.get(url)
    datos_sucios = respuesta.json()
    df = pd.DataFrame(datos_sucios['ListaEESSPrecio'])
    
    # Filtramos Canarias (35 y 38)
    df_canarias = df[df['IDProvincia'].isin(['35', '38'])].copy()
    
    # Limpieza de precios y coordenadas
    df_canarias['Precio Gasolina 95 E5'] = pd.to_numeric(df_canarias['Precio Gasolina 95 E5'].str.replace(',', '.'), errors='coerce')
    df_canarias['Latitud'] = pd.to_numeric(df_canarias['Latitud'].str.replace(',', '.'), errors='coerce')
    df_canarias['Longitud (WGS84)'] = pd.to_numeric(df_canarias['Longitud (WGS84)'].str.replace(',', '.'), errors='coerce')
    
    # Quitamos las que no tienen precio o coordenadas
    df_canarias = df_canarias.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])
    
    return df_canarias

def generar_mapa(df):
    print("🌍 2. Generando el mapa interactivo...")
    
    # Creamos el mapa centrado en una zona media de las islas
    # [Latitud, Longitud]
    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8)

    # Recorremos cada gasolinera y ponemos un pin
    for _, fila in df.iterrows():
        # Lógica de colores: 
        # Verde si es menos de 1.25€, Naranja si es menos de 1.35€, Rojo el resto
        if fila['Precio Gasolina 95 E5'] < 1.25:
            color_pin = "green"
        elif fila['Precio Gasolina 95 E5'] < 1.35:
            color_pin = "orange"
        else:
            color_pin = "red"

        # Contenido de la burbuja al hacer clic
        texto_pop = f"""
        <b>{fila['Rótulo']}</b><br>
        Municipio: {fila['Localidad']}<br>
        Precio G95: {fila['Precio Gasolina 95 E5']} €
        """

        folium.Marker(
            location=[fila['Latitud'], fila['Longitud (WGS84)']],
            popup=folium.Popup(texto_pop, max_width=300),
            icon=folium.Icon(color=color_pin, icon='info-sign')
        ).add_to(mapa)

    # Guardamos el mapa como un archivo HTML
    mapa.save("mapa_canarias.html")
    print("✅ ¡LISTO! Se ha creado 'mapa_canarias.html' en tu carpeta.")

if __name__ == "__main__":
    print("🚀 Arrancando proyecto...")
    mis_datos = obtener_datos_canarias()
    generar_mapa(mis_datos)