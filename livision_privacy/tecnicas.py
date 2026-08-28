"""
Técnicas de anonimização.

Cada função transforma UM valor (ou uma Series, quando a técnica é estatística e
precisa da distribuição inteira). Nenhuma sabe o que é uma aba, uma planilha ou
um quase-identificador — recebem dados e devolvem dados.

As de valor único são puras e testáveis isoladamente. As que dependem de segredo
(pseudonimização) ou de aleatoriedade (ruído Laplace) recebem esse estado por
parâmetro, em vez de lê-lo de um global.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime

import numpy as np
import pandas as pd

from . import config


def _vazio(valor) -> bool:
    """NaN, None ou string só de espaços."""
    return pd.isna(valor) or not str(valor).strip()


# --------------------------------------------------------------------------
# Pseudonimização
# --------------------------------------------------------------------------

def pseudonimizar(valor, sal: bytes, prefixo: str = "ANON") -> str:
    """HMAC-SHA256(sal, valor), truncado em 12 hex.

    Estável: a mesma entrada gera a mesma saída, o que preserva o JOIN entre
    abas (o user_id de `ranking` continua batendo com o de `usuarios`).
    Irreversível sem o sal — ao contrário de um hash simples, que cairia em
    minutos para um domínio pequeno como IDs de 1 a 120.
    """
    if pd.isna(valor):
        return ""
    digest = hmac.new(sal, str(valor).encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{prefixo}-{digest[:12].upper()}"


def prefixo_para(coluna: str) -> str:
    """Prefixo legível do pseudônimo, derivado do nome da coluna."""
    alvo = coluna.lower()
    if "user" in alvo:
        return "USR"
    if "device" in alvo:
        return "DEV"
    return "ID"


# --------------------------------------------------------------------------
# Mascaramento
# --------------------------------------------------------------------------

def mascarar_nome(valor) -> str:
    """'Ana Beatriz Silva' → 'A. B. S.'

    Mantém a contagem de tokens (útil para estatística de nomes compostos) e
    descarta a identidade.
    """
    if _vazio(valor):
        return ""
    return " ".join(f"{parte[0].upper()}." for parte in str(valor).split() if parte)


def mascarar_email(valor) -> str:
    """'ana.silva@gmail.com' → 'a********@gmail.com'

    Preserva o provedor, que é informação demográfica agregada e não identifica
    ninguém; oculta o local-part, que costuma conter o nome real.
    """
    if pd.isna(valor) or "@" not in str(valor):
        return ""
    local, dominio = str(valor).rsplit("@", 1)
    visivel = local[0] if local else "*"
    # Mínimo de 3 asteriscos: um local-part de 1-2 letras revelaria o tamanho.
    return f"{visivel}{'*' * max(len(local) - 1, 3)}@{dominio}"


# --------------------------------------------------------------------------
# Generalização
# --------------------------------------------------------------------------

def generalizar_ip(valor) -> str:
    """'201.82.14.7' → '201.82.0.0/16'

    Um /16 identifica o provedor e a região aproximada, não a residência.
    """
    if pd.isna(valor):
        return ""
    partes = str(valor).split(".")
    if len(partes) != 4:
        return ""
    return f"{partes[0]}.{partes[1]}.0.0/16"


def generalizar_data(valor, granularidade: str = "mes") -> str:
    """Timestamp completo → 'YYYY-MM' (ou 'YYYY').

    A hora exata de uso é um traço comportamental: quem coleta amostras sempre
    às 23h40 é identificável pelo padrão, mesmo sem nome.
    """
    if _vazio(valor):
        return ""
    try:
        dt = pd.to_datetime(valor)
    except (ValueError, TypeError):
        return ""
    return dt.strftime("%Y-%m") if granularidade == "mes" else dt.strftime("%Y")


def faixa_etaria(valor, referencia: datetime | None = None) -> str:
    """Data de nascimento → faixa de 10 anos.

    Top-coding em 70+: acima disso há poucos indivíduos, e uma faixa com poucos
    membros volta a ser identificadora.
    """
    if _vazio(valor):
        return ""
    try:
        nascimento = pd.to_datetime(valor)
    except (ValueError, TypeError):
        return ""
    ref = referencia or config.DATA_REFERENCIA
    idade = int((ref - nascimento).days // 365.25)
    if idade < 18:
        return "menor_18"
    if idade >= 70:
        return "70+"
    base = (idade // 10) * 10
    return f"{base}-{base + 9}"


def generalizar_regiao(valor) -> str:
    """Cidade ou UF → macrorregião.

    Uma cidade pequena é quase-identificador forte; uma macrorregião tem
    dezenas de milhões de habitantes. Aceita tanto sigla de UF quanto nome de
    cidade, porque as duas colunas colapsam neste mesmo destino.
    """
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    if texto.upper() in config.REGIOES:
        return config.REGIOES[texto.upper()]
    return config.REGIOES.get(config.CIDADE_PARA_UF.get(texto, ""), "Não informado")


def generalizar_device(valor) -> str:
    """'iPhone 15 Pro' / 'Android 14' → 'iOS' / 'Android'.

    Modelo + versão de SO é uma das assinaturas de fingerprint mais fortes que
    existem: a combinação costuma ser quase única em bases desse tamanho.
    """
    if pd.isna(valor):
        return ""
    texto = str(valor).lower()
    if any(m in texto for m in ("iphone", "ios", "ipad")):
        return "iOS"
    if "android" in texto or any(m in texto for m in config.MARCAS_ANDROID):
        return "Android"
    return "Outro"


def generalizar_categoria(valor, frequencias: dict | None = None,
                          minimo: int | None = None) -> str:
    """Colapsa categorias raras em 'outro'.

    Um valor com 2 ocorrências numa coluna sensível aponta quase diretamente
    para as pessoas em questão.
    """
    if _vazio(valor):
        return "nao_informado"
    texto = str(valor).strip()
    limite = config.FREQ_MINIMA_CATEGORIA if minimo is None else minimo
    if frequencias is not None and frequencias.get(texto, 0) < limite:
        return "outro"
    return texto


# --------------------------------------------------------------------------
# Numéricas
# --------------------------------------------------------------------------

def agregar_espacial(valor, casas: int | None = None) -> float | str:
    """Arredonda lat/lon para uma grade grosseira.

    O padrão é 0 casas (~111 km). Usar 1 casa (~11 km) parece seguro mas ainda
    resolve a cidade — o par (-25.4, -49.3) é Curitiba sem ambiguidade, o que
    anularia a generalização cidade → macrorregião feita em outra coluna.
    """
    if pd.isna(valor):
        return ""
    precisao = config.CASAS_DECIMAIS_COORDENADA if casas is None else casas
    try:
        return round(float(valor), precisao)
    except (ValueError, TypeError):
        return ""


def ruido_laplace(serie: pd.Series, epsilon: float, rng: np.random.Generator,
                  sensibilidade: float | None = None) -> pd.Series:
    """Privacidade diferencial (ε-DP): adiciona ruído Laplace de escala Δf/ε.

    Aplicado às medidas biométricas da mão. Envergadura e proporção entre dedos
    são estáveis por pessoa e funcionam como impressão digital: sem ruído, dá
    para agrupar todas as amostras da mesma mão mesmo com o ID pseudonimizado.

    O ruído preserva a distribuição agregada — média e forma continuam úteis
    para treinar o modelo — mas quebra o rastreamento individual.

    Recebe `rng` por parâmetro em vez de criar um: assim o pipeline controla a
    reprodutibilidade e a função não guarda estado.
    """
    numerica = pd.to_numeric(serie, errors="coerce")
    if numerica.notna().sum() == 0:
        return serie
    if sensibilidade is None:
        # Δf ≈ amplitude interquartil: robusta a outliers, ao contrário do range.
        sensibilidade = (
            float(numerica.quantile(0.75) - numerica.quantile(0.25))
            or float(numerica.std())
            or 1.0
        )
    ruido = rng.laplace(0, sensibilidade / epsilon, size=len(numerica))
    return (numerica + ruido).round(4)


def bucketizar(serie: pd.Series, n_faixas: int | None = None) -> pd.Series:
    """Numérico contínuo → faixas por quantil, rotuladas com o intervalo.

    Quantil em vez de largura fixa: distribuições assimétricas (latência, tempo
    de sessão) produziriam faixas vazias com corte uniforme.
    """
    faixas = config.N_FAIXAS_BUCKET if n_faixas is None else n_faixas
    numerica = pd.to_numeric(serie, errors="coerce")
    if numerica.notna().sum() < faixas:
        return serie
    try:
        cortes = pd.qcut(numerica, q=faixas, duplicates="drop")
    except (ValueError, TypeError):
        return serie
    return cortes.apply(
        lambda i: "" if pd.isna(i) else f"{int(i.left)}-{int(i.right)}"
    )
