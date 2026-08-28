"""
Vocabulário fictício para a geração de dados sintéticos.

Só listas — nenhuma lógica. Todos os nomes, e-mails e documentos produzidos a
partir daqui são inventados; nenhum dado real de usuário é utilizado.
"""

from __future__ import annotations

from datetime import datetime

#: Início da janela temporal simulada.
DATA_BASE = datetime(2026, 1, 15, 8, 0, 0)

SEED = 42

PRIMEIROS_NOMES = [
    "Ana", "Bruno", "Carla", "Daniel", "Eduarda", "Felipe", "Gabriela", "Henrique",
    "Isabela", "João", "Karina", "Lucas", "Mariana", "Nicolas", "Olívia", "Pedro",
    "Queila", "Rafael", "Sofia", "Thiago", "Ursula", "Vinícius", "Wanessa", "Yuri",
    "Beatriz", "Caio", "Débora", "Enzo", "Fernanda", "Gustavo", "Helena", "Igor",
]

SOBRENOMES = [
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Almeida", "Lopes", "Soares", "Fernandes", "Vieira", "Barbosa", "Rocha",
    "Dias", "Nascimento", "Andrade", "Moreira", "Nunes", "Marques", "Machado",
]

PROVEDORES_EMAIL = [
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com.br",
    "uol.com.br", "protonmail.com", "icloud.com",
]

#: (cidade, uf, latitude, longitude) — centro urbano aproximado.
CIDADES = [
    ("São Paulo", "SP", -23.5505, -46.6333),
    ("Rio de Janeiro", "RJ", -22.9068, -43.1729),
    ("Belo Horizonte", "MG", -19.9167, -43.9345),
    ("Curitiba", "PR", -25.4284, -49.2733),
    ("Porto Alegre", "RS", -30.0346, -51.2177),
    ("Recife", "PE", -8.0476, -34.8770),
    ("Salvador", "BA", -12.9777, -38.5016),
    ("Fortaleza", "CE", -3.7319, -38.5267),
    ("Manaus", "AM", -3.1190, -60.0217),
    ("Brasília", "DF", -15.7939, -47.8828),
    ("Campinas", "SP", -22.9099, -47.0626),
    ("Florianópolis", "SC", -27.5954, -48.5480),
]

#: (modelo, versão de SO, plataforma)
DISPOSITIVOS = [
    ("Samsung Galaxy S23", "Android 14", "android"),
    ("Samsung Galaxy A54", "Android 13", "android"),
    ("Motorola Edge 40", "Android 14", "android"),
    ("Xiaomi Redmi Note 12", "Android 13", "android"),
    ("Google Pixel 7", "Android 15", "android"),
    ("iPhone 13", "iOS 17.4", "ios"),
    ("iPhone 15 Pro", "iOS 18.1", "ios"),
    ("iPhone SE 2022", "iOS 17.2", "ios"),
]

#: Proporção intencional: a maioria dos cadastros é de colaboradores comuns.
PAPEIS = ["colaborador"] * 22 + ["pesquisador"] * 6 + ["admin"] * 2

#: DDDs por UF, para telefones fictícios coerentes com a cidade.
DDD_POR_UF = {
    "SP": [11, 19], "RJ": [21], "MG": [31], "PR": [41], "RS": [51],
    "PE": [81], "BA": [71], "CE": [85], "AM": [92], "DF": [61], "SC": [48],
}

#: Sinais estáticos: alfabeto datilológico.
LABELS_ESTATICOS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

#: Sinais dinâmicos: gestos com trajetória temporal.
LABELS_DINAMICOS = [
    "OBRIGADO", "BOM-DIA", "BOA-NOITE", "POR-FAVOR", "DESCULPA", "TUDO-BEM",
    "AJUDA", "SIM", "NAO", "AMIGO", "FAMILIA", "TRABALHO", "ESCOLA", "CASA",
    "AGUA", "COMER", "APRENDER", "SURDO", "INTERPRETE", "LIBRAS",
]

#: Níveis do módulo Aprender → categoria correspondente.
CATEGORIAS = {
    "iniciante": "alfabeto",
    "intermediario": "cumprimentos",
    "avancado": "conversacao",
}

CONDICOES_LUZ = ["natural", "artificial_quente", "artificial_fria",
                 "baixa_luz", "contraluz"]

#: Modos aceitos pelo WebSocket de inferência (services/gestureWebSocket.ts).
MODOS_DETECCAO = ["hybrid", "ml", "dynamic_ml", "rules"]

#: Faixas de IP públicas usadas no Brasil, para endereços fictícios plausíveis.
FAIXAS_IP = [177, 179, 186, 187, 189, 200, 201]

#: Versões de modelo simuladas: (nome, arquitetura, tipo de sinal).
VERSOES_MODELO = [
    ("mlp_static_v1", "MLP", "estatico"),
    ("mlp_static_v2", "MLP", "estatico"),
    ("mlp_static_v3", "MLP", "estatico"),
    ("gru_bi_v1", "GRU-Bidirecional", "dinamico"),
    ("gru_bi_v2", "GRU-Bidirecional", "dinamico"),
    ("gru_bi_v3", "GRU-Bidirecional", "dinamico"),
]

#: Modelos marcados como ativos na aba `modelos_treinados`.
MODELOS_ATIVOS = ("mlp_static_v3", "gru_bi_v3")
