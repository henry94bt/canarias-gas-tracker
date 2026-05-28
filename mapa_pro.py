import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster, Search
from datetime import datetime
import pytz
import os
import time

# 1. FUNCIÓN ROBUSTA DE MAPEO DE ISLAS
def obtener_isla(municipio):
    mun = str(municipio).upper()
    if any(x in mun for x in ['PALMAS', 'TELDE', 'AGAETE', 'AGÜIMES', 'ARTENARA', 'ARUCAS', 'FIRGAS', 'GÁLDAR', 'INGENIO', 'MOGÁN', 'MOYA', 'TIRAJANA', 'BRÍGIDA', 'LUCÍA', 'GUÍA DE GRAN CANARIA', 'TEJEDA', 'TEROR', 'VALLESECO', 'VALSEQUILLO', 'MATEO', 'ALDEA']):
        return 'Gran Canaria'
    elif any(x in mun for x in ['OLIVA', 'ANTIGUA', 'BETANCURIA', 'PÁJARA', 'PUERTO DEL ROSARIO', 'TUINEJE']):
        return 'Fuerteventura'
    elif any(x in mun for x in ['ARRECIFE', 'HARÍA', 'SAN BARTOLOMÉ', 'TEGUISE', 'TÍAS', 'TINAJO', 'YAIZA']):
        return 'Lanzarote'
    elif any(x in mun for x in ['CRUZ DE TENERIFE', 'ADEJE', 'ARAFO', 'ARICO', 'ARONA', 'BUENAVISTA', 'CANDELARIA', 'FASNIA', 'GARACHICO', 'GRANADILLA', 'GUANCHA', 'ISORA', 'ICOD', 'MATANZA', 'OROTAVA', 'PUERTO DE LA CRUZ', 'REALEJOS', 'ROSARIO', 'LAGUNA', 'RAMBLA', 'SAN MIGUEL', 'ÚRSULA', 'SANTIAGO DEL TEIDE', 'SAUZAL', 'SILOS', 'TACORONTE', 'TANQUE', 'TEGUESTE', 'VICTORIA', 'VILAFLOR']):
        return 'Tenerife'
    elif any(x in mun for x in ['BARLOVENTO', 'BREÑA', 'FUENCALIENTE', 'GARAFÍA', 'LLANOS DE ARIDANE', 'PASO', 'PUNTAGORDA', 'PUNTALLANA', 'SAN ANDRÉS', 'CRUZ DE LA PALMA', 'TAZACORTE', 'TIJARAFE', 'MAZO']):
        return 'La Palma'
    elif any(x in mun for x in ['AGULO', 'ALAJERÓ', 'HERMIGUA', 'SAN SEBASTIÁN', 'VALLE GRAN REY', 'VALLEHERMOSO']):
        return 'La Gomera'
    elif any(x in mun for x in ['FRONTERA', 'PINAR', 'VALVERDE']):
        return 'El Hierro'
    return 'Otras'


# 2. OBTENCIÓN DE DATOS — con reintentos
def obtener_datos(max_reintentos=3, espera=10):
    url = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for intento in range(1, max_reintentos + 1):
        try:
            print(f"🛰️  Intento {intento}/{max_reintentos} — conectando con la API...")
            with requests.Session() as session:
                r = session.get(url, headers=headers, timeout=30)
                r.raise_for_status()
                df = pd.DataFrame(r.json()['ListaEESSPrecio'])

                # Filtrar Canarias
                df = df[df['IDProvincia'].isin(['35', '38'])].copy()

                # Limpiar precios y coordenadas
                for c in ['Precio Gasolina 95 E5', 'Precio Gasoleo A', 'Latitud', 'Longitud (WGS84)']:
                    df[c] = pd.to_numeric(df[c].str.replace(',', '.'), errors='coerce')

                df['Isla'] = df['Municipio'].apply(obtener_isla)
                df = df.dropna(subset=['Latitud', 'Longitud (WGS84)'])

                if len(df) < 100:
                    raise ValueError(f"Datos insuficientes: solo {len(df)} estaciones. Posible respuesta parcial.")

                print(f"✅ API OK — {len(df)} estaciones obtenidas.")
                return df

        except Exception as e:
            print(f"⚠️  Error en intento {intento}: {e}")
            if intento < max_reintentos:
                print(f"   Reintentando en {espera} segundos...")
                time.sleep(espera)

    print("❌ Error crítico: la API no respondió tras todos los reintentos.")
    return pd.DataFrame()


# 3. ACTUALIZAR HISTÓRICO
def actualizar_historico(df):
    archivo = 'historico_precios.csv'
    fecha = datetime.now(pytz.timezone('Atlantic/Canary')).strftime("%Y-%m-%d")
    df_h = df[['Municipio', 'Rótulo', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].copy()
    df_h['Fecha'] = fecha
    if os.path.exists(archivo):
        prev = pd.read_csv(archivo)
        df_h = pd.concat([prev, df_h]).drop_duplicates(subset=['Fecha', 'Rótulo', 'Municipio'])
    df_h.to_csv(archivo, index=False)
    print(f"📁 Histórico actualizado: {len(df_h)} registros totales.")


# 4. GENERACIÓN DE LA WEB
def generar_web(df):
    if df.empty:
        return False

    canarias_tz = pytz.timezone('Atlantic/Canary')
    ahora = datetime.now(canarias_tz).strftime("%d/%m/%Y %H:%M")

    hist = pd.read_csv('historico_precios.csv') if os.path.exists('historico_precios.csv') else None
    u_fecha = sorted(hist['Fecha'].unique())[-2] if (hist is not None and len(hist['Fecha'].unique()) > 1) else None

    mapa = folium.Map(location=[28.3, -15.8], zoom_start=8, tiles='cartodbpositron')

    islas_list = ['Tenerife', 'Gran Canaria', 'Lanzarote', 'Fuerteventura', 'La Palma', 'La Gomera', 'El Hierro']
    grupos = {i: folium.FeatureGroup(name=i).add_to(mapa) for i in islas_list}
    clusters = {i: MarkerCluster().add_to(grupos[i]) for i in islas_list}

    # FIX: umbrales dinámicos por cuartiles en lugar de valor fijo
    q25 = df['Precio Gasolina 95 E5'].quantile(0.25)
    q75 = df['Precio Gasolina 95 E5'].quantile(0.75)

    marcadores = {isla: [] for isla in islas_list}

    for _, f in df.iterrows():
        v_g95, v_die = "", ""
        if hist is not None and u_fecha:
            p_est = hist[
                (hist['Fecha'] == u_fecha) &
                (hist['Rótulo'] == f['Rótulo']) &
                (hist['Municipio'] == f['Municipio'])
            ]
            if not p_est.empty:
                dg = f['Precio Gasolina 95 E5'] - p_est['Precio Gasolina 95 E5'].values[0]
                dd = f['Precio Gasoleo A'] - p_est['Precio Gasoleo A'].values[0]
                if pd.notnull(dg) and dg != 0:
                    v_g95 = f' <small style="color:{"red" if dg>0 else "green"}">{"▲" if dg>0 else "▼"}{abs(dg):.3f}</small>'
                if pd.notnull(dd) and dd != 0:
                    v_die = f' <small style="color:{"red" if dd>0 else "green"}">{"▲" if dd>0 else "▼"}{abs(dd):.3f}</small>'

        p_g95 = f"{f['Precio Gasolina 95 E5']:.3f}€" if pd.notnull(f['Precio Gasolina 95 E5']) else "N/A"
        p_die = f"{f['Precio Gasoleo A']:.3f}€" if pd.notnull(f['Precio Gasoleo A']) else "N/A"

        # FIX: umbrales dinámicos
        precio = f['Precio Gasolina 95 E5']
        if pd.notnull(precio):
            color = "green" if precio <= q25 else "red" if precio >= q75 else "orange"
        else:
            color = "gray"

        pop_html = (
            f"<b>{f['Rótulo']}</b>"
            f"<br><small>{f['Dirección']} ({f['Localidad']})</small>"
            f"<hr style='margin:5px 0'>"
            f"G95: {p_g95}{v_g95}<br>Diésel: {p_die}{v_die}"
        )

        marker = folium.Marker(
            [f['Latitud'], f['Longitud (WGS84)']],
            popup=folium.Popup(pop_html, max_width=250),
            icon=folium.Icon(color=color, icon='info-sign'),
            name=f"{f['Rótulo']} - {f['Localidad']} - {f['Municipio']}"
        )

        isla = f['Isla']
        if isla in clusters:
            marker.add_to(clusters[isla])
            marcadores[isla].append(marker)

    # FIX: buscador sobre TODAS las islas, no solo Gran Canaria
    for isla in islas_list:
        Search(
            layer=grupos[isla],
            geom_type='Point',
            placeholder=f'Buscar en {isla}...',
            collapsed=True,
            search_label='name'
        ).add_to(mapa)

    folium.LayerControl(collapsed=False).add_to(mapa)

    json_data = df[['Rótulo', 'Municipio', 'Localidad', 'Isla', 'Precio Gasolina 95 E5', 'Precio Gasoleo A']].rename(
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
                            <th>Localidad</th>
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
                    <td><small>${{d.Localidad}}</small></td>
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
    return True


# 5. MAIN
if __name__ == "__main__":
    df_raw = obtener_datos()

    if df_raw.empty:
        print("❌ Sin datos — se cancela la ejecución. No se sobreescribe nada.")
        exit(1)  # exit code 1: el workflow sabrá que falló

    actualizar_historico(df_raw)
    ok = generar_web(df_raw)

    if ok:
        print("✅ Web generada con éxito.")
    else:
        print("❌ Error generando la web.")
        exit(1)