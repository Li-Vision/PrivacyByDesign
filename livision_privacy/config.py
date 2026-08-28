"""
Parâmetros e constantes do pipeline.

Só dados — nenhuma lógica. Ajustar o comportamento do sistema (adicionar uma UF,
mudar o k padrão, incluir uma aba) deve ser possível aqui, sem tocar em código.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# --------------------------------------------------------------------------
# Parâmetros de privacidade
# --------------------------------------------------------------------------

K_ANONIMATO_PADRAO = 5
EPSILON_PADRAO = 1.0

#: Precisão de arredondamento de lat/lon, em casas decimais.
#: 0 = grade de ~111 km. Ver `tecnicas.agregar_espacial` para o porquê de não ser 1.
CASAS_DECIMAIS_COORDENADA = 0

#: Abaixo desta frequência, um valor categórico sensível vira "outro".
FREQ_MINIMA_CATEGORIA = 5

#: Número de faixas na bucketização de numéricos contínuos.
N_FAIXAS_BUCKET = 5

#: Data de referência para o cálculo de idade. Fixa para tornar a saída
#: reprodutível — usar `datetime.now()` faria as faixas mudarem com o tempo.
DATA_REFERENCIA = datetime(2026, 8, 28)

#: Seed do gerador de ruído Laplace. Fixa pelo mesmo motivo.
SEED_RUIDO = 20260828

#: Variável de ambiente que fornece o sal do HMAC. Sem ela, um sal aleatório é
#: gerado a cada execução (pseudônimos não se mantêm entre rodadas).
ENV_SAL = "LIVISION_ANON_SALT"


# --------------------------------------------------------------------------
# Nomes de arquivo
# --------------------------------------------------------------------------

ARQUIVO_BRUTO = "li_vision_dados_brutos.xlsx"
ARQUIVO_ANONIMIZADO = "li_vision_dados_anonimizados.xlsx"

ABA_LOG = "_log_anonimizacao"
ABA_METRICAS = "_metricas_privacidade"


# --------------------------------------------------------------------------
# Mapas de generalização geográfica
# --------------------------------------------------------------------------

REGIOES: dict[str, str] = {
    "SP": "Sudeste", "RJ": "Sudeste", "MG": "Sudeste", "ES": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
    "PE": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "RN": "Nordeste", "AL": "Nordeste", "SE": "Nordeste",
    "PI": "Nordeste",
    "AM": "Norte", "PA": "Norte", "AC": "Norte", "RO": "Norte",
    "RR": "Norte", "AP": "Norte", "TO": "Norte",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
}

CIDADE_PARA_UF: dict[str, str] = {
    "São Paulo": "SP", "Campinas": "SP", "Rio de Janeiro": "RJ",
    "Belo Horizonte": "MG", "Curitiba": "PR", "Porto Alegre": "RS",
    "Florianópolis": "SC", "Recife": "PE", "Salvador": "BA",
    "Fortaleza": "CE", "Manaus": "AM", "Brasília": "DF",
}

#: Marcas cujo nome comercial implica Android (usadas por `generalizar_device`).
MARCAS_ANDROID = ("samsung", "motorola", "xiaomi", "redmi", "pixel")


# --------------------------------------------------------------------------
# Configuração por aba
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ConfiguracaoAba:
    """Como tratar uma aba específica da planilha.

    `quase_identificadores` são as colunas JÁ ANONIMIZADAS (nomes de destino,
    pós-renomeação) cujo cruzamento poderia reidentificar alguém. É sobre elas
    que o k-anonimato opera.

    `sensiveis` são as colunas medidas pela l-diversidade.
    """

    quase_identificadores: tuple[str, ...] = ()
    sensiveis: tuple[str, ...] = ()


ABAS: dict[str, ConfiguracaoAba] = {
    "usuarios": ConfiguracaoAba(
        quase_identificadores=("faixa_etaria", "regiao", "genero", "plataforma",
                               "latitude_cadastro", "longitude_cadastro"),
        sensiveis=("genero", "usa_libras"),
    ),
    "amostras_coleta": ConfiguracaoAba(
        quase_identificadores=("regiao", "plataforma", "condicao_luz",
                               "tipo_sinal", "latitude", "longitude"),
        sensiveis=("mao_dominante",),
    ),
    "sessoes_traducao": ConfiguracaoAba(
        quase_identificadores=("regiao", "plataforma", "detection_mode"),
    ),
    "ranking": ConfiguracaoAba(
        quase_identificadores=("regiao", "role"),
    ),
    "progresso_aprendizado": ConfiguracaoAba(
        quase_identificadores=("level", "category"),
    ),
    "modelos_treinados": ConfiguracaoAba(),
}

#: Aba desconhecida: sem k-anonimato, apenas as técnicas por coluna.
ABA_PADRAO = ConfiguracaoAba()


def config_da_aba(nome: str) -> ConfiguracaoAba:
    return ABAS.get(nome, ABA_PADRAO)


# --------------------------------------------------------------------------
# Renomeação
# --------------------------------------------------------------------------

#: Colunas distintas na origem que colapsam no MESMO destino após generalização.
#: Ex.: 'cidade' e 'uf' viram ambas a macrorregião — manter as duas guardaria a
#: mesma informação duas vezes, e 'uf' é a mais granular das duas.
#: O pipeline mantém a primeira ocorrência e descarta as seguintes.
RENOMEAR: dict[str, str] = {
    "full_name": "nome_mascarado",
    "usuario_nome": "nome_mascarado",
    "colaborador_nome": "nome_mascarado",
    "email": "email_mascarado",
    "usuario_email": "email_mascarado",
    "colaborador_email": "email_mascarado",
    "data_nascimento": "faixa_etaria",
    "cidade": "regiao",
    "uf": "regiao",
    "device_model": "plataforma",
    "os_version": "plataforma",
}
