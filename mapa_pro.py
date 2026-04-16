import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from datetime import datetime
import pytz
import os

MUNICIPIOS_ISLAS = {
    'Arrecife': 'Lanzarote', 'Haría': 'Lanzarote', 'San Bartolomé': 'Lanzarote', 'Teguise': 'Lanzarote', 'Tías': 'Lanzarote', 'Tinajo': 'Lanzarote', 'Yaiza': 'Lanzarote',
    'Antigua': 'Fuerteventura', 'Betancuria': 'Fuerteventura', 'La Oliva': 'Fuerteventura', 'Pájara': 'Fuerteventura', 'Puerto del Rosario': 'Fuerteventura', 'Tuineje': 'Fuerteventura',
    'Agaete': 'Gran Canaria', 'Agüimes': 'Gran Canaria', 'Artenara': 'Gran Canaria', 'Arucas': 'Gran Canaria', 'Firgas': 'Gran Canaria', 'Gáldar': 'Gran Canaria', 'Ingenio': 'Gran Canaria', 'Mogán': 'Gran Canaria', 'Moya': 'Gran Canaria', 'Las Palmas de Gran Canaria': 'Gran Canaria', 'San Bartolomé de Tirajana': 'Gran Canaria', 'Santa Brígida': 'Gran Canaria', 'Santa Lucía de Tirajana': 'Gran Canaria', 'Santa María de Guía de Gran Canaria': 'Gran Canaria', 'Tejeda': 'Gran Canaria', 'Telde': 'Gran Canaria', 'Teror': 'Gran Canaria', 'Valleseco': 'Gran Canaria', 'Valsequillo de Gran Canaria': 'Gran Canaria', 'Vega de San Mateo': 'Gran Canaria',
    'Adeje': 'Tenerife', 'Arafo': 'Tenerife', 'Arico': 'Tenerife', 'Arona': 'Tenerife', 'Buenavista del Norte': 'Tenerife', 'Candelaria': 'Tenerife', 'Fasnia': 'Tenerife', 'Garachico': 'Tenerife', 'Granadilla de Abona': 'Tenerife', 'La Guancha': 'Tenerife', 'Guía de Isora': 'Tenerife', 'Icod de los Vinos': 'Tenerife', 'La Matanza de Acentejo': 'Tenerife', 'La Orotava': 'Tenerife', 'Puerto de la Cruz': 'Tenerife', 'Los Realejos': 'Tenerife', 'El Rosario': 'Tenerife', 'San Cristóbal de La Laguna': 'Tenerife', 'San Juan de la Rambla': 'Tenerife', 'San Miguel de Abona': 'Tenerife', 'Santa Cruz de Tenerife': 'Tenerife', 'Santa Úrsula': 'Tenerife', 'Santiago del Teide': 'Tenerife', 'El Sauzal': 'Tenerife', 'Los Silos': 'Tenerife', 'Tacoronte': 'Tenerife', 'El Tanque': 'Tenerife', 'Tegueste': 'Tenerife', 'La Victoria de Acentejo': 'Tenerife', 'Vilaflor de Chasna': 'Tenerife',
    'Agulo': 'La Gomera', 'Alajeró': 'La Gomera', 'Hermigua': 'La Gomera', 'San Sebastián de la Gomera': 'La Gomera', 'Valle Gran Rey': 'La Gomera', 'Vallehermoso': 'La Gomera',
    'Barlovento': 'La Palma', 'Breña Alta': 'La Palma', 'Breña Baja': 'La Palma', 'Fuencaliente de la Palma': 'La Palma', 'Garafía': 'La Palma', 'Los Llanos de Aridane': 'La Palma', 'El Paso': 'La Palma', 'Puntagorda': 'La Palma', 'Puntallana': 'La Palma', 'San Andrés y Sauces': 'La Palma', 'Santa Cruz de la Palma': 'La Palma', 'Tazacorte': 'La Palma', 'Tijarafe': 'La Palma', 'Villa de Mazo': 'La Palma',
    'Frontera': 'El Hierro', 'El Pinar de El Hierro': 'El Hierro', 'Valverde': 'El Hierro'
}

def obtener_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    r = requests.get(url, timeout=20)
    df = pd.DataFrame(r.json()['ListaEESSPrecio'])
    df = df[df['IDProvincia'].isin(['35', '38'])].copy()
    for c in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
        df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce')
    return df.dropna(subset=['Precio Gasolina 95 E5', 'Latitud', 'Longitud (WGS84)'])

def generar_web(df):
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    # Cargar histórico para las variaciones individuales
    hist = pd.read_csv('historico_precios.csv') if os.path.exists('historico_precios.csv') else None
    u_fecha = sorted(hist['Fecha'].unique())[-2] if hist is not None and len(hist['Fecha'].unique()) > 1 else None

    # Variación Global para el título
    texto_global = ""
    if u_fecha:
        m_ayer = hist[hist['Fecha'] == u_fecha]['Precio Gasolina 95 E5'].mean()
        diff_g = df['Precio Gasolina 95 E5'].mean() - m_ayer
        color_g = "red" if diff_g > 0 else "green"
        texto_global = f'<span style="color:{color_g}; font-weight:bold; margin-left:10px;">{"▲" if diff_g > 0 else "▼"} {abs(diff_g):.3f}€ vs ayer</span>'

    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')
    
    # Capas por isla
    islas = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    grupos = {i: MarkerCluster(name=i).add_to(mapa) for i in islas}
    
    q25 = df['Precio Gasolina 95 E5'].quantile(0.25)

    for _, f in df.iterrows():
        # Lógica de variación por cada gasolinera (Lo que pediste)
        v_loc = ""
        if hist is not None and u_fecha:
            p_est = hist[(hist['Fecha'] == u_fecha) & (hist['Rótulo'] == f['Rótulo']) & (f['Municipio'] == f['Municipio'])]
            if not p_est.empty:
                diff_l = f['Precio Gasolina 95 E5'] - p_est['Precio Gasolina 95 E5'].values[0]
                if diff_l != 0:
                    c_l = "#e74c3c" if diff_l > 0 else "#27ae60"
                    v_loc = f'<br><b style="color:{c_l};">{ "▲" if diff_l > 0 else "▼"} {abs(diff_l):.3f}€</b>'

        color = "green" if f['Precio Gasolina 95 E5'] <= q25 else "orange" if f['Precio Gasolina 95 E5'] < 1.45 else "red"
        
        # HTML del Popup mejorado
        html_pop = f"""
        <div style="font-family: Arial; width: 160px;">
            <div style="background:#2c3e50; color:white; padding:5px; border-radius:3px; font-size:12px;"><b>{f['Rótulo']}</b></div>
            <div style="padding:8px; border: 1px solid #ccc; border-top:none;">
                <b>G95:</b> {f['Precio Gasolina 95 E5']}€ {v_loc}<br>
                <b>Diésel:</b> {f['Precio Gasoleo A']}€
            </div>
        </div>
        """
        
        isla_f = MUNICIPIOS_ISLAS.get(f['Municipio'], 'Otros')
        if isla_f in grupos:
            folium.Marker([f['Latitud'], f['Longitud (WGS84)']], 
                          popup=folium.Popup(html_pop, max_width=200),
                          icon=folium.Icon(color=color, icon='info-sign')).add_to(grupos[isla_f])

    folium.LayerControl(collapsed=False).add_to(mapa)

    # Arreglar nombres de columnas para las tablas
    df_t = df.rename(columns={'Precio Gasolina 95 E5': 'G95 (€)', 'Precio Gasoleo A': 'Diésel (€)'})
    t_g95 = df_t.nsmallest(10, 'G95 (€)')[['Rótulo', 'Municipio', 'G95 (€)']].to_html(classes='table table-sm table-hover text-center', index=False)
    t_die = df_t.nsmallest(10, 'Diésel (€)')[['Rótulo', 'Municipio', 'Diésel (€)']].to_html(classes='table table-sm table-hover text-center', index=False)

    estilo_y_tablas = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body {{ background-color: #f4f7f6; }}
        .header-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .table {{ background: white; border-radius: 8px; overflow: hidden; font-size: 0.9em; }}
        .thead-dark th {{ background-color: #343a40; color: white; }}
    </style>
    <div class="container-fluid p-4">
        <div class="header-box text-center">
            <h1 class="display-6">Canarias Gas Tracker ⛽</h1>
            <p class="text-muted">🕒 Actualizado: {ahora} {texto_global}</p>
        </div>
        <div class="row g-4 mb-4">
            <div class="col-lg-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-primary text-white text-center">🏆 Top 10 Baratas: Gasolina 95</div>
                    <div class="card-body p-0">{t_g95}</div>
                </div>
            </div>
            <div class="col-lg-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-success text-white text-center">🏆 Top 10 Baratas: Diésel</div>
                    <div class="card-body p-0">{t_die}</div>
                </div>
            </div>
        </div>
    </div>
    """
    mapa.get_root().html.add_child(folium.Element(estilo_y_tablas))
    mapa.save("index.html")

if __name__ == "__main__":
    datos = obtener_datos()
    # Guardar histórico ANTES de generar web para tener la comparación lista
    fecha = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
    df_h = datos[['Municipio', 'Rótulo', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
    df_h['Fecha'] = fecha
    if os.path.exists('historico_precios.csv'):
        p = pd.read_csv('historico_precios.csv')
        df_h = pd.concat([p, df_h]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Municipio'])
    df_h.to_csv('historico_precios.csv', index=False)
    
    generar_web(datos)