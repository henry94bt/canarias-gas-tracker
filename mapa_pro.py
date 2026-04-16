import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Search
from datetime import datetime
import pytz
import os

# Diccionario de Municipios - Asegúrate de que los nombres coinciden con la API
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
    r = requests.get(url, timeout=30)
    df = pd.DataFrame(r.json()['ListaEESSPrecio'])
    df = df[df['IDProvincia'].isin(['35', '38'])].copy()
    for c in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
        df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce')
    # Solo tiramos las que no tienen coordenadas. Si no tienen precio, las dejamos para el mapa.
    return df.dropna(subset=['Latitud', 'Longitud (WGS84)'])

def generar_web(df):
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    # Historico y Variación Global
    hist = pd.read_csv('historico_precios.csv') if os.path.exists('historico_precios.csv') else None
    u_fecha = sorted(hist['Fecha'].unique())[-2] if hist is not None and len(hist['Fecha'].unique()) > 1 else None
    texto_global = ""
    if u_fecha:
        m_ayer = hist[hist['Fecha'] == u_fecha]['Precio Gasolina 95 E5'].mean()
        diff_g = df['Precio Gasolina 95 E5'].mean() - m_ayer
        texto_global = f'<span style="color:{"red" if diff_g > 0 else "green"}; font-weight:bold;">{"▲" if diff_g > 0 else "▼"} {abs(diff_g):.3f}€ vs ayer</span>'

    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')
    
    # Capas por isla
    islas_list = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    grupos = {i: folium.FeatureGroup(name=i).add_to(mapa) for i in islas_list}
    clusters = {i: MarkerCluster().add_to(grupos[i]) for i in islas_list}
    
    q25 = df['Precio Gasolina 95 E5'].quantile(0.25)

    for _, f in df.iterrows():
        # Variación individual
        v_loc = ""
        if hist is not None and u_fecha:
            p_est = hist[(hist['Fecha'] == u_fecha) & (hist['Rótulo'] == f['Rótulo']) & (hist['Municipio'] == f['Municipio'])]
            if not p_est.empty:
                d_l = f['Precio Gasolina 95 E5'] - p_est['Precio Gasolina 95 E5'].values[0]
                if d_l != 0:
                    v_loc = f'<br><b style="color:{"#e74c3c" if d_l > 0 else "#27ae60"};">{"▲" if d_l > 0 else "▼"} {abs(d_l):.3f}€</b>'

        color = "green" if f['Precio Gasolina 95 E5'] <= q25 else "orange" if f['Precio Gasolina 95 E5'] < 1.45 else "red"
        
        # Guardamos el objeto marker para el buscador
        marker = folium.Marker(
            [f['Latitud'], f['Longitud (WGS84)']], 
            popup=folium.Popup(f"<b>{f['Rótulo']}</b><br>G95: {f['Precio Gasolina 95 E5']}€{v_loc}", max_width=200),
            icon=folium.Icon(color=color, icon='info-sign'),
            name=f"{f['Rótulo']} ({f['Municipio']})" # Nombre para el buscador
        )
        
        isla_f = MUNICIPIOS_ISLAS.get(f['Municipio'], 'Otros')
        if isla_f in clusters:
            marker.add_to(clusters[isla_f])

    # 🔍 BUSCADOR DE GASOLINERAS
    Search(
        layer=grupos['Gran Canaria'], # Usamos una capa de base, pero buscará en los nombres
        geom_type='Point',
        placeholder='Buscar gasolinera...',
        collapsed=False,
        search_label='name'
    ).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    # Tablas con columnas renombradas
    df_t = df.rename(columns={'Precio Gasolina 95 E5': 'G95 (€)', 'Precio Gasoleo A': 'Diésel (€)'})
    t_g95 = df_t.nsmallest(10, 'G95 (€)')[['Rótulo', 'Municipio', 'G95 (€)']].to_html(classes='table table-sm table-hover text-center align-middle m-0', index=False)
    t_die = df_t.nsmallest(10, 'Diésel (€)')[['Rótulo', 'Municipio', 'Diésel (€)']].to_html(classes='table table-sm table-hover text-center align-middle m-0', index=False)

    # HTML y CSS Final con botones de Clear All
    plantilla = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        .header-box {{ background: #fff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; }}
        .card-header {{ font-weight: bold; font-size: 0.9rem; }}
        .table {{ font-size: 0.85rem; table-layout: fixed; }}
        th {{ background-color: #f8f9fa !important; }}
        /* Estilo para los botones de Toggle en el mapa */
        .toggle-btn-container {{ position: absolute; top: 180px; right: 10px; z-index: 1000; background: white; padding: 5px; border-radius: 4px; border: 2px solid rgba(0,0,0,0.2); }}
    </style>
    
    <div class="container-fluid p-3">
        <div class="header-box text-center">
            <h2 class="mb-1">Canarias Gas Tracker ⛽</h2>
            <small class="text-muted">🕒 {ahora} — {texto_global}</small>
        </div>
        <div class="row g-3 mb-3">
            <div class="col-md-6">
                <div class="card shadow-sm border-0">
                    <div class="card-header bg-primary text-white py-2">🏆 TOP 10 GASOLINA 95</div>
                    <div class="card-body p-0">{t_g95}</div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card shadow-sm border-0">
                    <div class="card-header bg-success text-white py-2">🏆 TOP 10 DIÉSEL</div>
                    <div class="card-body p-0">{t_die}</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // SCRIPT PARA EL BOTÓN "CLEAR ALL" EN EL SELECTOR DE CAPAS
        document.addEventListener('DOMContentLoaded', function() {{
            setTimeout(function() {{
                var controlContainer = document.querySelector('.leaflet-control-layers-list');
                if (controlContainer) {{
                    var btnHtml = '<div class="d-flex gap-1 mt-2 p-1 border-top">' +
                                  '<button class="btn btn-dark btn-sm w-100" onclick="toggleLayers(true)" style="font-size:10px">Todos</button>' +
                                  '<button class="btn btn-outline-dark btn-sm w-100" onclick="toggleLayers(false)" style="font-size:10px">Nada</button>' +
                                  '</div>';
                    controlContainer.insertAdjacentHTML('beforeend', btnHtml);
                }}
            }}, 1000);
        }});

        function toggleLayers(show) {{
            var inputs = document.querySelectorAll('.leaflet-control-layers-selector');
            inputs.forEach(input => {{
                if (input.checked !== show) {{
                    input.click();
                }}
            }});
        }}
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(plantilla))
    mapa.save("index.html")

if __name__ == "__main__":
    datos = obtener_datos()
    # Guardar historico
    fecha = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
    df_h = datos[['Municipio', 'Rótulo', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
    df_h['Fecha'] = fecha
    if os.path.exists('historico_precios.csv'):
        p = pd.read_csv('historico_precios.csv')
        df_h = pd.concat([p, df_h]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Municipio'])
    df_h.to_csv('historico_precios.csv', index=False)
    
    generar_web(datos)