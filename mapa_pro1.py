import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from datetime import datetime
import pytz
import os

# 1. DICCIONARIO DE ISLAS (Para el filtrado)
MUNICIPIOS_ISLAS = {
    'Arrecife': 'Lanzarote', 'Haría': 'Lanzarote', 'San Bartolomé': 'Lanzarote', 'Teguise': 'Lanzarote', 'Tías': 'Lanzarote', 'Tinajo': 'Lanzarote', 'Yaiza': 'Lanzarote',
    'Antigua': 'Fuerteventura', 'Betancuria': 'Fuerteventura', 'La Oliva': 'Fuerteventura', 'Pájara': 'Fuerteventura', 'Puerto del Rosario': 'Fuerteventura', 'Tuineje': 'Fuerteventura',
    'Agaete': 'Gran Canaria', 'Agüimes': 'Gran Canaria', 'Artenara': 'Gran Canaria', 'Arucas': 'Gran Canaria', 'Firgas': 'Gran Canaria', 'Gáldar': 'Gran Canaria', 'Ingenio': 'Gran Canaria', 'Mogán': 'Gran Canaria', 'Moya': 'Gran Canaria', 'Las Palmas de Gran Canaria': 'Gran Canaria', 'San Bartolomé de Tirajana': 'Gran Canaria', 'Santa Brígida': 'Gran Canaria', 'Santa Lucía de Tirajana': 'Gran Canaria', 'Santa María de Guía de Gran Canaria': 'Gran Canaria', 'Tejeda': 'Gran Canaria', 'Telde': 'Gran Canaria', 'Teror': 'Gran Canaria', 'Valleseco': 'Gran Canaria', 'Valsequillo de Gran Canaria': 'Gran Canaria', 'Vega de San Mateo': 'Gran Canaria',
    'Adeje': 'Tenerife', 'Arafo': 'Tenerife', 'Arico': 'Tenerife', 'Arona': 'Tenerife', 'Buenavista del Norte': 'Tenerife', 'Candelaria': 'Tenerife', 'Fasnia': 'Tenerife', 'Garachico': 'Tenerife', 'Granadilla de Abona': 'Tenerife', 'La Guancha': 'Tenerife', 'Guía de Isora': 'Tenerife', 'Icod de los Vinos': 'Tenerife', 'La Matanza de Acentejo': 'Tenerife', 'La Orotava': 'Tenerife', 'Puerto de la Cruz': 'Tenerife', 'Los Realejos': 'Tenerife', 'El Rosario': 'Tenerife', 'San Cristóbal de La Laguna': 'Tenerife', 'San Juan de la Rambla': 'Tenerife', 'San Miguel de Abona': 'Tenerife', 'Santa Cruz de Tenerife': 'Tenerife', 'Santa Úrsula': 'Tenerife', 'Santiago del Teide': 'Tenerife', 'El Sauzal': 'Tenerife', 'Los Silos': 'Tenerife', 'Tacoronte': 'Tenerife', 'El Tanque': 'Tenerife', 'Tegueste': 'Tenerife', 'La Victoria de Acentejo': 'Tenerife', 'Vilaflor de Chasna': 'Tenerife',
    'Agulo': 'La Gomera', 'Alajeró': 'La Gomera', 'Hermigua': 'La Gomera', 'San Sebastián de la Gomera': 'La Gomera', 'Valle Gran Rey': 'La Gomera', 'Vallehermoso': 'La Gomera',
    'Barlovento': 'La Palma', 'Breña Alta': 'La Palma', 'Breña Baja': 'La Palma', 'Fuencaliente de la Palma': 'La Palma', 'Garafía': 'La Palma', 'Los Llanos de Aridane': 'La Palma', 'El Paso': 'La Palma', 'Puntagorda': 'La Palma', 'Puntallana': 'La Palma', 'San Andrés y Sauces': 'La Palma', 'Santa Cruz de la Palma': 'La Palma', 'Tazacorte': 'La Palma', 'Tijarafe': 'La Palma', 'Villa de Mazo': 'La Palma',
    'Frontera': 'El Hierro', 'El Pinar de El Hierro': 'El Hierro', 'Valverde': 'El Hierro'
}

def obtener_datos_canarias():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    cabeceras = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=cabeceras, timeout=20)
        df = pd.DataFrame(r.json()['ListaEESSPrecio'])
        df_can = df[df['IDProvincia'].isin(['35', '38'])].copy()
        for col in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
            df_can[col] = pd.to_numeric(df_can[col].str.replace(',', '.'), errors='coerce')
        return df_can.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])
    except Exception as e:
        print(f"❌ Error API: {e}"); return None

def actualizar_historico(df):
    archivo = 'historico_precios.csv'
    fecha = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
    df_h = df[['Municipio', 'Rótulo', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
    df_h['Fecha'] = fecha
    if os.path.exists(archivo):
        prev = pd.read_csv(archivo)
        df_h = pd.concat([prev, df_h]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Municipio'])
    df_h.to_csv(archivo, index=False)

def generar_visualizacion(df):
    if df is None: return
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    # 1. CÁLCULO DE VARIACIÓN GLOBAL (Lo que tenías antes)
    texto_variacion = ""
    hist = pd.read_csv('historico_precios.csv') if os.path.exists('historico_precios.csv') else None
    if hist is not None:
        fechas = sorted(hist['Fecha'].unique())
        if len(fechas) > 1:
            u_fecha = fechas[-2]
            m_ayer = hist[hist['Fecha'] == u_fecha]['Precio Gasolina 95 E5'].mean()
            m_hoy = df['Precio Gasolina 95 E5'].mean()
            diff_g = m_hoy - m_ayer
            c_v = "red" if diff_g > 0 else "green"
            f_v = "▲" if diff_g > 0 else "▼"
            texto_variacion = f'<b style="color:{c_v}; margin-left:15px;">{f_v} {abs(diff_g):.3f}€ vs ayer (Media)</b>'

    # 2. MAPA Y CLUSTERS POR ISLA
    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')
    islas_nombres = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    capas = {nom: MarkerCluster().add_to(folium.FeatureGroup(name=nom).add_to(mapa)) for nom in islas_nombres}
    
    u_verde = df['Precio Gasolina 95 E5'].quantile(0.25)

    for _, fila in df.iterrows():
        # Variación individual (Local)
        var_local = ""
        if hist is not None and len(fechas) > 1:
            prev_est = hist[(hist['Fecha'] == fechas[-2]) & (hist['Rótulo'] == fila['Rótulo']) & (hist['Municipio'] == fila['Municipio'])]
            if not prev_est.empty:
                d_l = fila['Precio Gasolina 95 E5'] - prev_est['Precio Gasolina 95 E5'].values[0]
                if d_l != 0:
                    c_l = "red" if d_l > 0 else "green"
                    f_l = "▲" if d_l > 0 else "▼"
                    var_local = f'<br><span style="color:{c_l}; font-size: 0.85em;">{f_l} {abs(d_l):.3f}€</span>'

        color = "green" if fila['Precio Gasolina 95 E5'] <= u_verde else "orange" if fila['Precio Gasolina 95 E5'] < 1.40 else "red"
        pop_html = f"<b>{fila['Rótulo']}</b><hr style='margin:5px 0;'>G95: {fila['Precio Gasolina 95 E5']}€ {var_local}<br>Diésel: {fila['Precio Gasoleo A']}€"
        
        isla = MUNICIPIOS_ISLAS.get(fila['Municipio'], 'Otros')
        if isla in capas:
            folium.Marker(
                [fila['Latitud'], fila['Longitud (WGS84)']],
                popup=folium.Popup(pop_html, max_width=250),
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(capas[isla])

    folium.LayerControl(collapsed=False).add_to(mapa)

    # 3. TABLAS DUALES (GASOLINA Y DIÉSEL)
    t_g95 = df.nsmallest(10, 'Precio Gasolina 95 E5')[['Rótulo', 'Municipio', 'Precio Gasolina 95 E5']].to_html(classes='table table-sm table-dark table-striped', index=False)
    t_die = df.nsmallest(10, 'Precio Gasoleo A')[['Rótulo', 'Municipio', 'Precio Gasoleo A']].to_html(classes='table table-sm table-dark table-striped', index=False)

    plantilla = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <div style="padding: 20px; background-color: #f8f9fa;">
        <h1 style="text-align:center;">Canarias Gas Tracker ⛽</h1>
        <p style="text-align:center;">🕒 Actualizado: <b>{ahora}</b> {texto_variacion}</p>
        <div class="container-fluid">
            <div class="row mt-4">
                <div class="col-md-6">
                    <h5 class="text-center text-primary">🏆 Top 10 Económicas (G95)</h5>
                    {t_g95}
                </div>
                <div class="col-md-6">
                    <h5 class="text-center text-success">🏆 Top 10 Económicas (Diésel)</h5>
                    {t_die}
                </div>
            </div>
        </div>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(plantilla))
    mapa.save("index.html")

if __name__ == "__main__":
    datos = obtener_datos_canarias()
    if datos is not None:
        generar_visualizacion(datos)
        actualizar_historico(datos)