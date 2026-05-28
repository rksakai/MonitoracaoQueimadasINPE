import azure.functions as func
import requests
import pymssql
import io
import os
import logging
from datetime import datetime, timedelta

app = func.FunctionApp()

BASE_URL = (
    "https://dataserver-coids.inpe.br"
    "/queimadas/queimadas/focos/csv/diario/Brasil/"
)

def get_connection():
    return pymssql.connect(
        server=os.environ["SQL_SERVER"],
        user=os.environ["SQL_USER"],
        password=os.environ["SQL_PASS"],
        database=os.environ["SQL_DB"]
    )

def criar_tabela_se_nao_existir(cursor):
    cursor.execute("""
        IF NOT EXISTS (
            SELECT * FROM sysobjects WHERE name='focos_queimadas'
        )
        CREATE TABLE focos_queimadas (
            id          INT IDENTITY PRIMARY KEY,
            lat         FLOAT,
            lon         FLOAT,
            municipio   NVARCHAR(100),
            estado      NVARCHAR(50),
            bioma       NVARCHAR(50),
            satelite    NVARCHAR(50),
            data_hora   DATETIME,
            coletado_em DATETIME DEFAULT GETDATE()
        )
    """)

def buscar_focos_inpe(data: str) -> list:
    """
    data: formato 'YYYY-MM-DD'
    Baixa o CSV diário do INPE e retorna lista de dicts.
    """
    data_fmt = data.replace("-", "")   # YYYYMMDD
    url = f"{BASE_URL}focos_diario_br_{data_fmt}.csv"

    logging.info(f"Baixando: {url}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    focos = []
    lines = resp.text.splitlines()
    if len(lines) < 2:
        return focos

    # Cabeçalho: id,lat,lon,data_hora_gmt,satelite,municipio,
    #            estado,pais,municipio_id,estado_id,pais_id,
    #            numero_dias_sem_chuva,precipitacao,risco_fogo,bioma,frp
    header = [h.strip() for h in lines[0].split(",")]

    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < len(header):
            continue
        row = dict(zip(header, parts))
        focos.append(row)

    return focos

def inserir_focos(cursor, focos: list):
    for foco in focos:
        try:
            cursor.execute(
                """
                INSERT INTO focos_queimadas
                    (lat, lon, municipio, estado, bioma, satelite, data_hora)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    float(foco.get("lat", 0) or 0),
                    float(foco.get("lon", 0) or 0),
                    foco.get("municipio", "").strip(),
                    foco.get("estado", "").strip(),
                    foco.get("bioma", "").strip(),
                    foco.get("satelite", "").strip(),
                    foco.get("data_hora_gmt", "").strip(),
                )
            )
        except Exception as e:
            logging.warning(f"Erro ao inserir foco: {e} | dados: {foco}")
            continue

@app.timer_trigger(schedule="0 0 */6 * * *", arg_name="myTimer",
                   run_on_startup=True)
def coleta_queimadas(myTimer: func.TimerRequest) -> None:
    logging.info("Iniciando coleta de focos de queimadas...")

    ontem = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Buscar CSV do INPE
    try:
        focos = buscar_focos_inpe(ontem)
        logging.info(f"{len(focos)} focos encontrados para {ontem}.")
    except Exception as e:
        logging.error(f"Erro ao buscar dados do INPE: {e}")
        raise

    # 2. Persistir no SQL Server
    try:
        conn   = get_connection()
        cursor = conn.cursor()
        criar_tabela_se_nao_existir(cursor)
        inserir_focos(cursor, focos)
        conn.commit()
        conn.close()
        logging.info(f"{len(focos)} focos salvos com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar no banco: {e}")
        raise
