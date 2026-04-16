import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Search
from datetime import datetime
import pytz
import os
import json

# 1. DICCIONARIO DE ISLAS (Para el filtrado de la tabla y el mapa)
MUNICIPIOS_ISLAS = {
    'Arrecife': 'Lanzarote', 'Haría': 'Lanzarote', 'San Bartolomé': 'Lanzarote', 'Teguise': 'Lanzarote', 'Tías': 'Lanzarote', 'Tinajo': 'Lanzarote', 'Yaiza': 'Lanzarote',
    'Antigua': 'Fuerteventura', 'Betancuria': 'Fuerteventura', 'La Oliva': 'Fuerteventura', 'Pájara': 'Fuerteventura', 'Puerto del Rosario': 'Fuerteventura', 'Tuineje': 'Fuerteventura',
    'Agaete': 'Gran Canaria', 'Agüimes': 'Gran Canaria', 'Artenara': 'Gran Canaria', 'Arucas': 'Gran Canaria', 'Firgas': 'Gran Canaria', 'Gáldar': 'Gran Canaria', 'Ingenio': 'Gran Canaria', 'Mogán': 'Gran Canaria', 'Moya': 'Gran Canaria', 'Las Palmas de Gran Canaria': 'Gran Canaria', 'San Bartolomé de Tirajana': 'Gran Canaria', 'Santa Brígida': 'Gran Canaria', 'Santa Lucía de Tirajana': 'Gran Canaria', 'Santa María de Guía de Gran Canaria': 'Gran Canaria', 'Tejeda': 'Gran Canaria', 'Telde': 'Gran Canaria', 'Teror': 'Gran Canaria', 'Valleseco': 'Gran Canaria', 'Valsequillo de Gran Canaria': 'Gran Canaria', 'Vega de San Mateo': 'Gran Canaria',
    'Adeje': 'Tenerife', 'Arafo': 'Tenerife', 'Arico': 'Tenerife', 'Arona': 'Tenerife', 'Buenavista del Norte': 'Tenerife', 'Candelaria': 'Tenerife', 'Fasnia': 'Tenerife', 'Garachico': 'Tenerife', 'Granadilla de Abona': 'Tenerife', 'La Guancha': 'Tenerife', 'Guía de Isora': 'Tenerife', 'Icod de los Vinos': 'Tenerife', 'La Matanza de Acentejo': 'Tenerife', 'La Orotava': 'Tenerife', 'Puerto de la Cruz': 'Tenerife', 'Los Realejos': 'Tenerife', 'El Rosario': 'Tenerife', 'San Cristóbal de La Laguna': 'Tenerife', 'San Juan de la Rambla': 'Tenerife', 'San Miguel de Abona': 'Tenerife', 'Santa Cruz de Tenerife': 'Tenerife', 'Santa Úrsula': 'Tenerife', 'Santiago del Teide': 'Tenerife', 'El Sauzal': 'Tenerife', 'Los Silos': 'Tenerife', 'Tacoronte': 'Tenerife', 'El Tanque': 'Tenerife', 'Tegueste': 'Tenerife', 'La Victoria de Acentejo': 'Tenerife', 'Vilaflor de Chasna': 'Tenerife',
    'Agulo': 'La Gomera', 'Alajeró': 'La Gomera', 'Hermigua': 'La Gomera', 'San Sebastián de la Gomera': 'La Gomera', 'Valle Gran Rey': 'La Gomera', 'Vallehermoso': 'La Gomera',
    'Barlovento': 'La Palma', 'Breña Alta': 'La Palma', 'Breña Baja': 'La Palma', 'Fuencaliente de la Palma': 'La Palma', 'Garafía': 'La Palma', 'Los Llanos de Aridane': 'La Palma', 'El Paso': 'La Palma', 'Puntagorda': 'La Palma', 'Puntallana': 'La Palma', 'San Andrés y Sauces': 'La Palma', 'Santa Cruz de la Palma': 'La Palma', 'Tazacorte': 'La Palma', 'Tijarafe': 'La Palma', 'Villa de Mazo': 'La Palma',
    'Frontera': 'El Hierro', 'El Pinar de El Hierro': 'El Hierro', 'Valverde': 'El Hierro'
}

# 2. OBTENCIÓN DE DATOS (CON CAMUFLAJE ANTI-BLOQUEO)
def obtener_datos():
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        with requests.Session() as session:
            r = session.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            df = pd.DataFrame(r.json()['ListaEESSPrecio'])
            
            # Filtrar Canarias
            df = df[df['IDProvincia'].isin(['35', '38'])].copy()
            
            # Limpiar precios y coordenadas
            for c in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
                df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce')
            
            df['Isla'] = df['Municipio'].map(MUNICIPIOS_ISLAS).fillna('Otras')
            # Mantenemos las gasolineras aunque no tengan precio (para el mapa)
            return df.dropna(subset=['Latitud', 'Longitud (WGS84)'])
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        return pd.DataFrame()

# 3. GENERACIÓN DE LA WEB
def generar_web(df):
    if df.empty: return
    
    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")
    
    # Cargar Histórico para tendencias
    hist = pd.read_csv('historico_precios.csv') if os.path.exists('historico_precios.csv') else None
    u_fecha = sorted(hist['Fecha'].unique())[-2] if (hist is not None and len(hist['Fecha'].unique()) > 1) else None

    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')
    
    islas_list = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    grupos = {i: folium.FeatureGroup(name=i).add_to(mapa) for i in islas_list}
    clusters = {i: MarkerCluster().add_to(grupos[i]) for i in islas_list}
    
    q25 = df['Precio Gasolina 95 E5'].quantile(0.25)

    for _, f in df.iterrows():
        # Tendencias individuales
        v_g95, v_die = "", ""
        if hist is not None and u_fecha:
            p_est = hist[(hist['Fecha'] == u_fecha) & (hist['Rótulo'] == f['Rótulo']) & (hist['Municipio'] == f['Municipio'])]
            if not p_est.empty:
                dg = f['Precio Gasolina 95 E5'] - p_est['Precio Gasolina 95 E5'].values[0]
                dd = f['Precio Gasoleo A'] - p_est['Precio Gasoleo A'].values[0]
                if dg != 0: v_g95 = f' <small style="color:{"red" if dg>0 else "green"}">{"▲" if dg>0 else "▼"}{abs(dg):.3f}</small>'
                if dd != 0: v_die = f' <small style="color:{"red" if dd>0 else "green"}">{"▲" if dd>0 else "▼"}{abs(dd):.3f}</small>'

        p_g95 = f"{f['Precio Gasolina 95 E5']:.3f}€" if pd.notnull(f['Precio Gasolina 95 E5']) else "N/A"
        p_die = f"{f['Precio Gasoleo A']:.3f}€" if pd.notnull(f['Precio Gasoleo A']) else "N/A"

        color = "green" if f['Precio Gasolina 95 E5'] <= q25 else "orange" if f['Precio Gasolina 95 E5'] < 1.45 else "red"
        
        pop_html = f"<b>{f['Rótulo']}</b><br>G95: {p_g95}{v_g95}<br>Diésel: {p_die}{v_die}"
        
        marker = folium.Marker(
            [f['Latitud'], f['Longitud (WGS84)']], 
            popup=folium.Popup(pop_html, max_width=200),
            icon=folium.Icon(color=color, icon='info-sign'),
            name=f"{f['Rótulo']} ({f['Municipio']})"
        )
        if f['Isla'] in clusters: marker.add_to(clusters[f['Isla']])

    Search(layer=grupos['Gran Canaria'], geom_type='Point', placeholder='Buscar gasolinera...', collapsed=False, search_label='name').add_to(mapa)
    folium.LayerControl(collapsed=False).add_to(mapa)

    # Datos para la tabla interactiva
    json_data = df[['Rótulo', 'Municipio', 'Isla', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].rename(
        columns={'Precio Gasolina 95 E5': 'g95', 'Precio Gasoleo A': 'diesel'}
    ).to_json(orient='records')

    html_layout = f"""
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.3/dist/css/bootstrap.min.css">
    <style>
        body {{ background: #f4f7f6; }}
        .header-box {{ background: white; padding: 15px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .interactive-card {{ background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .table-responsive {{ max-height: 450px; overflow-y: auto; }}
        th {{ position: sticky; top: 0; background: #212529 !important; color: white; z-index: 10; }}
    </style>
    
    <div class="container-fluid p-3">
        <div class="header-box text-center">
            <h2 class="fw-bold mb-1">Canarias Gas Tracker ⛽</h2>
            <small class="text-muted">🕒 Actualizado: {ahora}</small>
        </div>

        <div class="interactive-card">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-3">
                <h6 class="m-0">🏆 TOP 10 BARATAS</h6>
                <div class="d-flex gap-2">
                    <select id="selIsla" class="form-select form-select-sm" style="width:140px" onchange="actualizarTabla()">
                        <option value="Todas">Canarias (Todas)</option>
                        {"".join([f'<option value="{i}">{i}</option>' for i in islas_list])}
                    </select>
                    <select id="selComb" class="form-select form-select-sm" style="width:120px" onchange="actualizarTabla()">
                        <option value="g95">Gasolina 95</option>
                        <option value="diesel">Diésel</option>
                    </select>
                </div>
            </div>
            <div class="table-responsive">
                <table class="table table-hover m-0">
                    <thead class="text-center">
                        <tr>
                            <th style="width: 50px">#</th>
                            <th class="text-start">Estación</th>
                            <th>Municipio</th>
                            <th style="width: 100px">Precio</th>
                        </tr>
                    </thead>
                    <tbody id="tablaCuerpo" class="text-center"></tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        const datos = {json_data};
        
        function actualizarTabla() {{
            const isla = document.getElementById('selIsla').value;
            const comb = document.getElementById('selComb').value;
            const cuerpo = document.getElementById('tablaCuerpo');
            
            let filtrados = datos.filter(d => (isla === 'Todas' || d.Isla === isla) && d[comb] !== null);
            filtrados.sort((a, b) => a[comb] - b[comb]);
            
            const top10 = filtrados.slice(0, 10);
            cuerpo.innerHTML = top10.map((d, i) => `
                <tr>
                    <td><span class="badge ${{i < 3 ? 'bg-success' : 'bg-secondary'}}">${{i+1}}</span></td>
                    <td class="text-start"><b>${{d.Rótulo}}</b></td>
                    <td><small>${{d.Municipio}}</small></td>
                    <td class="fw-bold text-primary">${{d[comb].toFixed(3)}}€</td>
                </tr>
            `).join('');
            
            if(top10.length === 0) cuerpo.innerHTML = '<tr><td colspan="4" class="p-4 text-muted">No hay datos para esta selección</td></tr>';
        }}

        document.addEventListener('DOMContentLoaded', () => {{
            actualizarTabla();
            setTimeout(() => {{
                const control = document.querySelector('.leaflet-control-layers-list');
                if(control) {{
                    control.insertAdjacentHTML('beforeend', '<div class="d-flex gap-1 p-2 border-top"><button class="btn btn-dark btn-sm w-100" onclick="tg(true)" style="font-size:10px">Todas</button><button class="btn btn-outline-dark btn-sm w-100" onclick="tg(false)" style="font-size:10px">Ninguna</button></div>');
                }}
            }}, 1500);
        }});
        function tg(s) {{ document.querySelectorAll('.leaflet-control-layers-selector').forEach(i => {{ if(i.checked !== s) i.click(); }}); }}
    </script>
    """
    mapa.get_root().html.add_child(folium.Element(html_layout))
    mapa.save("index.html")

if __name__ == "__main__":
    df_raw = obtener_datos()
    if not df_raw.empty:
        # Guardar histórico
        fecha = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
        df_h = df_raw[['Municipio', 'Rótulo', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
        df_h['Fecha'] = fecha
        if os.path.exists('historico_precios.csv'):
            p = pd.read_csv('historico_precios.csv')
            df_h = pd.concat([p, df_h]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Municipio'])
        df_h.to_csv('historico_precios.csv', index=False)
        
        generar_web(df_raw)
        print("✅ Web generada con éxito.")