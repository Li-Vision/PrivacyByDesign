"""
Fábricas de dados sintéticos — uma função por aba.

Cada fábrica recebe os geradores aleatórios explicitamente (`rng` do módulo
`random`, `npr` do numpy) em vez de usar globais. Isso torna a geração
reprodutível e permite construir uma aba isolada em teste.

A estrutura de cada aba espelha os tipos reais do app:
    features/auth/types.ts, profile/types.ts, ranking/types.ts,
    training/types.ts, learning/types.ts, services/gestureWebSocket.ts
"""

from __future__ import annotations

import hashlib
import random
import unicodedata
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from . import vocabulario as voc


# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------

def sem_acento(texto: str) -> str:
    """'João' → 'joao'. Usado para montar e-mails a partir do nome."""
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def cpf_ficticio(rng: random.Random) -> str:
    """CPF com dígitos verificadores válidos — formato correto, pessoa inexistente.

    Os DVs são calculados de verdade para que validadores de formato aceitem o
    valor; o objetivo é exercitar o pipeline com dados realistas.
    """
    base = [rng.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        peso = len(base) + 1
        soma = sum(d * (peso - i) for i, d in enumerate(base))
        dv = (soma * 10) % 11
        base.append(0 if dv == 10 else dv)
    s = "".join(map(str, base))
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


def telefone_ficticio(rng: random.Random, uf: str) -> str:
    ddd = rng.choice(voc.DDD_POR_UF.get(uf, [11]))
    return f"({ddd}) 9{rng.randint(1000, 9999)}-{rng.randint(1000, 9999)}"


def ip_ficticio(rng: random.Random) -> str:
    faixa = rng.choice(voc.FAIXAS_IP)
    return f"{faixa}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def device_id_ficticio(rng: random.Random) -> str:
    return hashlib.md5(str(rng.random()).encode()).hexdigest()[:16]


def _instante(rng: random.Random, dias_max: int) -> datetime:
    return voc.DATA_BASE + timedelta(
        days=rng.randint(0, dias_max),
        minutes=rng.randint(0, 1439),
        seconds=rng.randint(0, 59),
    )


def _texto(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


# --------------------------------------------------------------------------
# Abas
# --------------------------------------------------------------------------

def criar_usuarios(rng: random.Random, npr: np.random.Generator, n: int) -> pd.DataFrame:
    """Aba `usuarios` — cadastro. Concentra a maior parte da PII."""
    linhas = []
    emails_usados: set[str] = set()

    for i in range(1, n + 1):
        nome = f"{rng.choice(voc.PRIMEIROS_NOMES)} {rng.choice(voc.SOBRENOMES)} {rng.choice(voc.SOBRENOMES)}"
        partes = sem_acento(nome).split()

        email = f"{partes[0]}.{partes[-1]}@{rng.choice(voc.PROVEDORES_EMAIL)}"
        sufixo = 1
        while email in emails_usados:
            sufixo += 1
            email = f"{partes[0]}.{partes[-1]}{sufixo}@{rng.choice(voc.PROVEDORES_EMAIL)}"
        emails_usados.add(email)

        cidade, uf, lat, lon = rng.choice(voc.CIDADES)
        modelo, so, plataforma = rng.choice(voc.DISPOSITIVOS)
        criado = _instante(rng, 180)
        acesso = criado + timedelta(days=rng.randint(0, 60), minutes=rng.randint(0, 1439))

        linhas.append({
            "user_id": i,
            "full_name": nome,
            "email": email,
            "cpf": cpf_ficticio(rng),
            "telefone": telefone_ficticio(rng, uf),
            "data_nascimento": (
                datetime(2026, 1, 1) - timedelta(days=rng.randint(16 * 365, 70 * 365))
            ).strftime("%Y-%m-%d"),
            "genero": rng.choice(["F", "M", "Outro", "Prefiro não informar"]),
            "usa_libras": rng.choice(["surdo", "ouvinte", "interprete", "estudante"]),
            "role": rng.choice(voc.PAPEIS),
            "avatar_url": f"https://storage.li-vision.app/avatars/{partes[0]}_{i}.jpg",
            "cidade": cidade,
            "uf": uf,
            "latitude_cadastro": round(lat + npr.normal(0, 0.05), 6),
            "longitude_cadastro": round(lon + npr.normal(0, 0.05), 6),
            "ip_cadastro": ip_ficticio(rng),
            "device_id": device_id_ficticio(rng),
            "device_model": modelo,
            "os_version": so,
            "plataforma": plataforma,
            "consentimento_lgpd": rng.random() < 0.94,
            "criado_em": _texto(criado),
            "ultimo_acesso": _texto(acesso),
        })

    return pd.DataFrame(linhas)


def criar_amostras(rng: random.Random, npr: np.random.Generator,
                   usuarios: pd.DataFrame, n: int) -> pd.DataFrame:
    """Aba `amostras_coleta` — cada envio de /collect/static ou /collect/dynamic."""
    ids = usuarios["user_id"].tolist()
    indexado = usuarios.set_index("user_id")

    # Pareto: poucos colaboradores respondem pela maior parte das amostras,
    # como acontece em qualquer base de crowdsourcing real.
    pesos = npr.pareto(1.4, len(ids)) + 1
    pesos = pesos / pesos.sum()

    linhas = []
    for i in range(1, n + 1):
        uid = int(npr.choice(ids, p=pesos))
        u = indexado.loc[uid]

        dinamico = rng.random() < 0.42
        tipo = "dinamico" if dinamico else "estatico"
        label = rng.choice(voc.LABELS_DINAMICOS if dinamico else voc.LABELS_ESTATICOS)
        dataset = "GESTOS_DINAMICOS" if dinamico else "ALFABETO_LIBRAS"
        n_frames = 15 if dinamico else 1

        linhas.append({
            "sample_id": f"SMP-{i:06d}",
            "user_id": uid,
            "colaborador_nome": u["full_name"],
            "colaborador_email": u["email"],
            "dataset_name": dataset,
            "label": label,
            "tipo_sinal": tipo,
            "n_frames": n_frames,
            "n_landmarks": 21 * n_frames,
            "mao_dominante": rng.choice(["direita", "direita", "direita", "esquerda"]),
            # Medidas derivadas dos 21 landmarks: estáveis por pessoa, logo
            # funcionam como impressão digital da mão.
            "envergadura_mao_px": round(float(np.clip(npr.normal(178, 26), 95, 280)), 2),
            "comprimento_indicador_px": round(float(np.clip(npr.normal(74, 11), 40, 120)), 2),
            "razao_polegar_indicador": round(float(np.clip(npr.normal(0.72, 0.08), 0.45, 1.05)), 4),
            "wrist_x": round(float(np.clip(npr.normal(0.5, 0.13), 0.02, 0.98)), 6),
            "wrist_y": round(float(np.clip(npr.normal(0.55, 0.13), 0.02, 0.98)), 6),
            "wrist_z": round(float(npr.normal(0, 0.04)), 6),
            "delta_x_medio": round(float(npr.normal(0, 0.03)) if dinamico else 0.0, 6),
            "delta_y_medio": round(float(npr.normal(0, 0.03)) if dinamico else 0.0, 6),
            "qualidade_deteccao": round(float(np.clip(npr.normal(0.86, 0.11), 0.30, 0.999)), 4),
            "condicao_luz": rng.choice(voc.CONDICOES_LUZ),
            "device_model": u["device_model"],
            "os_version": u["os_version"],
            "device_id": u["device_id"],
            "ip_envio": ip_ficticio(rng),
            "cidade": u["cidade"],
            "uf": u["uf"],
            "latitude": round(float(u["latitude_cadastro"]) + npr.normal(0, 0.02), 6),
            "longitude": round(float(u["longitude_cadastro"]) + npr.normal(0, 0.02), 6),
            "capturado_em": _texto(_instante(rng, 200)),
            "aprovada": rng.random() < 0.91,
        })

    return pd.DataFrame(linhas).sort_values("capturado_em").reset_index(drop=True)


def criar_sessoes(rng: random.Random, npr: np.random.Generator,
                  usuarios: pd.DataFrame, n: int) -> pd.DataFrame:
    """Aba `sessoes_traducao` — resultados do WebSocket na tela de tradução."""
    ids = usuarios["user_id"].tolist()
    indexado = usuarios.set_index("user_id")

    linhas = []
    for i in range(1, n + 1):
        uid = rng.choice(ids)
        u = indexado.loc[uid]
        modo = rng.choice(voc.MODOS_DETECCAO)
        dinamico = modo == "dynamic_ml"

        linhas.append({
            "session_id": f"WS-{i:06d}",
            "user_id": uid,
            "usuario_nome": u["full_name"],
            "usuario_email": u["email"],
            "gesture": rng.choice(voc.LABELS_DINAMICOS if dinamico else voc.LABELS_ESTATICOS),
            # Beta(7,2) concentra a confiança perto de 1, como um modelo treinado.
            "confidence": round(float(np.clip(npr.beta(7, 2), 0.35, 0.999)), 4),
            "detection_mode": modo,
            "modelo_ativo": "gru_bi_v3" if dinamico else "mlp_static_v2",
            "latencia_ms": int(np.clip(npr.gamma(5, 12), 18, 900)),
            "frames_enviados": rng.randint(15, 450),
            "tts_acionado": rng.random() < 0.63,
            "idioma_tts": rng.choice(["pt-BR", "pt-BR", "pt-BR", "en-US", "es-ES"]),
            "device_id": u["device_id"],
            "device_model": u["device_model"],
            "ip_sessao": ip_ficticio(rng),
            "cidade": u["cidade"],
            "uf": u["uf"],
            "duracao_sessao_s": int(np.clip(npr.gamma(3, 40), 5, 1800)),
            "iniciada_em": _texto(_instante(rng, 210)),
        })

    return pd.DataFrame(linhas).sort_values("iniciada_em").reset_index(drop=True)


def criar_ranking(usuarios: pd.DataFrame, amostras: pd.DataFrame) -> pd.DataFrame:
    """Aba `ranking` — /collect/ranking.

    Derivada das amostras, não sorteada: o total precisa bater com a contagem
    real para que a planilha seja internamente consistente.
    """
    contagem = amostras.groupby("user_id").size().rename("samples").reset_index()
    df = contagem.merge(
        usuarios[["user_id", "full_name", "email", "cidade", "uf", "role"]],
        on="user_id", how="left",
    ).sort_values("samples", ascending=False).reset_index(drop=True)
    df.insert(0, "position", df.index + 1)
    return df[["position", "user_id", "full_name", "email",
               "cidade", "uf", "role", "samples"]]


def criar_progresso(rng: random.Random, npr: np.random.Generator,
                    usuarios: pd.DataFrame) -> pd.DataFrame:
    """Aba `progresso_aprendizado` — módulo Aprender."""
    # Probabilidade decrescente: quase todos começam o alfabeto, poucos chegam
    # ao nível avançado.
    adesao = {"iniciante": 0.9, "intermediario": 0.5, "avancado": 0.25}

    linhas = []
    for _, u in usuarios.iterrows():
        for nivel, categoria in voc.CATEGORIAS.items():
            if rng.random() > adesao[nivel]:
                continue
            total = 26 if nivel == "iniciante" else 20
            aprendidos = int(np.clip(npr.binomial(total, rng.uniform(0.15, 0.95)), 0, total))
            linhas.append({
                "user_id": int(u["user_id"]),
                "usuario_nome": u["full_name"],
                "usuario_email": u["email"],
                "level": nivel,
                "category": categoria,
                "gestos_totais": total,
                "gestos_aprendidos": aprendidos,
                "progresso_pct": round(100 * aprendidos / total, 1),
                "tempo_estudo_min": int(np.clip(npr.gamma(4, 22), 3, 900)),
                "ultima_atividade": _texto(
                    voc.DATA_BASE + timedelta(days=rng.randint(0, 210))
                ),
            })
    return pd.DataFrame(linhas)


def criar_modelos(rng: random.Random, npr: np.random.Generator) -> pd.DataFrame:
    """Aba `modelos_treinados` — ML Studio."""
    linhas = []
    for i, (nome, arquitetura, tipo) in enumerate(voc.VERSOES_MODELO, start=1):
        # Acurácia crescente por versão: simula a evolução do treinamento.
        acc = float(np.clip(0.70 + i * 0.032 + npr.normal(0, 0.015), 0.60, 0.985))
        linhas.append({
            "model_id": f"MDL-{i:03d}",
            "name": nome,
            "arquitetura": arquitetura,
            "tipo_sinal": tipo,
            "is_active": nome in voc.MODELOS_ATIVOS,
            "amostras_treino": rng.randint(1800, 14000),
            "epocas": rng.randint(40, 250),
            "acuracia_treino": round(min(acc + 0.045, 0.998), 4),
            "acuracia_validacao": round(acc, 4),
            "f1_score": round(acc - npr.uniform(0.005, 0.03), 4),
            "treinado_por_user_id": rng.randint(1, 10),
            "created_at": _texto(voc.DATA_BASE + timedelta(days=25 * i)),
        })
    return pd.DataFrame(linhas)
