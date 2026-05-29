-- Monitor de Queimadas — Script de criacao da estrutura
-- Executar conectado ao banco db-queimadas

-- Tabela principal
IF NOT EXISTS (
    SELECT * FROM sysobjects WHERE name = 'focos_queimadas'
)
BEGIN
    CREATE TABLE focos_queimadas (
        id          INT           IDENTITY(1,1)  NOT NULL,
        lat         FLOAT                         NOT NULL,
        lon         FLOAT                         NOT NULL,
        municipio   NVARCHAR(100)                     NULL,
        estado      NVARCHAR(50)                      NULL,
        bioma       NVARCHAR(50)                      NULL,
        satelite    NVARCHAR(50)                      NULL,
        data_hora   DATETIME                          NULL,
        coletado_em DATETIME      DEFAULT GETDATE()   NOT NULL,
        CONSTRAINT PK_focos_queimadas PRIMARY KEY (id)
    );

    CREATE INDEX IX_focos_queimadas_coletado_em
        ON focos_queimadas (coletado_em DESC);

    CREATE INDEX IX_focos_queimadas_estado_bioma
        ON focos_queimadas (estado, bioma);

    PRINT 'Tabela focos_queimadas criada com sucesso.';
END
ELSE
    PRINT 'Tabela focos_queimadas ja existe.';
GO

-- View auxiliar: ultimos focos das ultimas 24h
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name = 'vw_focos_recentes')
BEGIN
    EXEC('
        CREATE VIEW vw_focos_recentes AS
        SELECT id, lat, lon, municipio, estado, bioma, satelite, data_hora, coletado_em
        FROM focos_queimadas
        WHERE coletado_em >= DATEADD(HOUR, -24, GETDATE())
    ');

    PRINT 'View vw_focos_recentes criada.';
END
GO

-- Consultas uteis para validacao
SELECT COUNT(*) AS total_focos FROM focos_queimadas;

SELECT estado, COUNT(*) AS qtd
FROM focos_queimadas
GROUP BY estado ORDER BY qtd DESC;

SELECT TOP 10 * FROM focos_queimadas ORDER BY coletado_em DESC;
