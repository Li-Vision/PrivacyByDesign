"""
Classificação de risco das colunas.

Responsabilidade única: dado um nome de coluna, decidir QUAL a classe de risco e
QUAL técnica aplicar. Não transforma valores — devolve apenas a decisão, que o
pipeline usa para escolher a implementação no `registry`.

Manter isto separado permite auditar a política de privacidade lendo um arquivo
só, e testar a classificação sem tocar em dados.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Risco(str, Enum):
    """Classe de risco de identificação de uma coluna.

    Herda de str para serializar direto no log em Excel sem conversão.
    """

    #: Identifica sozinho uma pessoa: nome, CPF, e-mail, device_id.
    DIRETO = "identificador_direto"

    #: Não identifica sozinho, mas o cruzamento sim (cidade + idade + aparelho).
    QUASE = "quase_identificador"

    #: Art. 5º II da LGPD: saúde, biometria, origem, convicção.
    SENSIVEL = "dado_sensivel"

    #: Não identificável. Preservado integralmente.
    TECNICO = "nao_identificavel"


@dataclass(frozen=True)
class Decisao:
    """Resultado da classificação de uma coluna."""

    coluna: str
    risco: Risco
    tecnica: str


def _termos(*termos: str) -> str:
    """Monta um regex que casa termos como tokens de um nome snake_case.

    NÃO usar \\b aqui: em regex Python '_' conta como caractere de palavra, então
    r"\\bnome\\b" NÃO casa com "colaborador_nome" — e a coluna vazaria intacta.
    A fronteira real em snake_case é o início da string, o fim, ou '_'.
    """
    return r"(?:^|_)(?:" + "|".join(termos) + r")(?:_|$)"


def _exatos(*nomes: str) -> str:
    """Regex que casa apenas o nome de coluna inteiro."""
    return r"^(?:" + "|".join(nomes) + r")$"


# --------------------------------------------------------------------------
# Política de classificação
# --------------------------------------------------------------------------
# A ordem importa: a PRIMEIRA regra que casa vence. A allowlist vem primeiro
# justamente para proteger colunas cujo nome lembra PII mas não é.
#
# Duas armadilhas que estas âncoras evitam, ambas já observadas neste dataset:
#   - substring solta: 'rg' casaria com "enve[rg]adura_mao_px", suprimindo uma
#     medida biométrica como se fosse um documento de identidade;
#   - 'name' solto casaria com "dataset_name", mascarando o nome do dataset
#     como se fosse o nome de uma pessoa.

REGRAS: tuple[tuple[str, Risco, str], ...] = (
    # -- allowlist: nome parece PII, conteúdo é do domínio -------------------
    # 'name' puro NÃO entra aqui: na aba ranking é o nome da pessoa.
    (_exatos("dataset_name", "model_name", "modelo_ativo", "label",
             "gesture", "arquitetura", "tipo_sinal"), Risco.TECNICO, "manter"),

    # -- identificadores diretos -------------------------------------------
    (r"^(?:user_)?id$|_id$",                      Risco.DIRETO, "pseudonimizar"),
    (_termos("full_name", "nome", "name"),        Risco.DIRETO, "mascarar_nome"),
    (_termos("email", "e_mail"),                  Risco.DIRETO, "mascarar_email"),
    (_termos("cpf", "rg", "cnpj", "documento"),   Risco.DIRETO, "suprimir"),
    (_termos("telefone", "celular", "phone"),     Risco.DIRETO, "suprimir"),
    (_termos("avatar", "foto", "imagem_perfil", "photo"),
                                                  Risco.DIRETO, "suprimir"),
    (r"^ip_|_ip$|" + _termos("ip", "ip_address"), Risco.DIRETO, "generalizar_ip"),
    (_termos("device_id", "installation_id", "uuid"),
                                                  Risco.DIRETO, "pseudonimizar"),

    # -- quase-identificadores ---------------------------------------------
    (_termos("data_nascimento", "birth", "nascimento"),
                                                  Risco.QUASE, "faixa_etaria"),
    (_termos("latitude", "longitude", "lat", "lon", "lng"),
                                                  Risco.QUASE, "agregar_espacial"),
    (_termos("cidade", "city", "municipio"),      Risco.QUASE, "generalizar_regiao"),
    (_termos("uf", "estado", "state"),            Risco.QUASE, "generalizar_regiao"),
    (_termos("device_model", "os_version", "modelo_aparelho"),
                                                  Risco.QUASE, "generalizar_device"),
    (_termos("criado_em", "created_at", "ultima", "ultimo", "capturado",
             "iniciada", "atividade") + r"|_em$|_at$",
                                                  Risco.QUASE, "generalizar_data"),
    (r"^(?:envergadura|comprimento|razao|wrist)_",
                                                  Risco.QUASE, "ruido_laplace"),
    (_termos("duracao", "latencia", "tempo") + r"|^(?:duracao|latencia|tempo)_",
                                                  Risco.QUASE, "bucketizar"),

    # -- dados sensíveis ---------------------------------------------------
    (_termos("genero", "sexo", "gender"),         Risco.SENSIVEL, "generalizar_categoria"),
    (_termos("usa_libras", "deficiencia", "saude", "condicao_auditiva"),
                                                  Risco.SENSIVEL, "generalizar_categoria"),
    # Biometria de cardinalidade 2 (direita/esquerda): não reidentifica sozinha.
    (_termos("mao_dominante"),                    Risco.SENSIVEL, "manter"),
)

#: Compilado uma vez na importação — `classificar` roda por coluna, por aba.
_REGRAS_COMPILADAS = tuple(
    (re.compile(padrao), risco, tecnica) for padrao, risco, tecnica in REGRAS
)


def classificar_coluna(nome: str) -> Decisao:
    """Classifica uma coluna. Sem correspondência → técnico, preservado."""
    alvo = nome.lower()
    for padrao, risco, tecnica in _REGRAS_COMPILADAS:
        if padrao.search(alvo):
            return Decisao(nome, risco, tecnica)
    return Decisao(nome, Risco.TECNICO, "manter")


def classificar(colunas: list[str]) -> list[Decisao]:
    """Classifica uma lista de colunas, preservando a ordem original."""
    return [classificar_coluna(c) for c in colunas]
