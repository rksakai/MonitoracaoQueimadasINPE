import os
import pymssql
import folium
from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Monitor de Queimadas</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        h2   { color: #007A33; }
        .info { background: #E8F5E9; padding: 10px; border-radius: 6px;
                display: inline-block; margin-bottom: 12px; }
    </style>
</head>
<body>
    <h2>🔥 Monitor de Focos de Queimadas — Últimas 24h</h2>
    <div class="info">
        Total de focos exibidos: <b>{{ total }}</b>
    </div>
    {{ mapa | safe }}
</body>
</html>
"""

def get_connection():
    return pymssql.connect(
        server=os.environ["SQL_SERVER"],      # ex: sql-queimadas.database.windows.net
        user=os.environ["SQL_USER"],          # ex: adminuser
        password=os.environ["SQL_PASS"],      # ex: SuaSenha@123
        database=os.environ["SQL_DB"]         # ex: db-queimadas
    )

@app.route("/")
def index():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TOP 500 lat, lon, municipio, estado, bioma
        FROM focos_queimadas
        ORDER BY coletado_em DESC
    """)
    rows = cursor.fetchall()
    conn.close()

    # Mapa centrado no Brasil
    mapa = folium.Map(location=[-15.0, -55.0], zoom_start=4)

    for lat, lon, municipio, estado, bioma in rows:
        if lat is not None and lon is not None:
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                color="red",
                fill=True,
                fill_opacity=0.7,
                popup=folium.Popup(
                    f"<b>{municipio}</b> — {estado}<br>Bioma: {bioma}",
                    max_width=200
                )
            ).add_to(mapa)

    return render_template_string(HTML,
                                  mapa=mapa._repr_html_(),
                                  total=len(rows))

@app.route("/health")
def health():
    """Endpoint de health check para o ACI."""
    return {"status": "ok"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
