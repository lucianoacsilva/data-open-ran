"""Detecção de anomalia de carga em telemetria KPM/E2 — Grupo 1, Tema G2.

Reproduz o detector MAD do laboratório (`scripts/ai_policy_pipeline.py` do repositório
do docente) e acrescenta os dois indicadores do grupo: TAA e ISC.

Fonte: code/datasets/kpm-ue-tp-sample/kpm.sqlite (trilha offline, run ue-tp-20260804-174422).

Uso típico:

    from g2_lib import *
    amostras = carregar_amostras(caminho_db())
    modelo   = treinar(amostras[amostras.phase == "baseline"])
    escorado = escorar_df(amostras, modelo)
    kpis     = kpis_por_fase(escorado)
"""

from __future__ import annotations

import json
import sqlite3
import statistics
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Parâmetros do detector — herdados de model.json para permitir conferência
# --------------------------------------------------------------------------

FEATURES = ["DRB.RlcSduDelayDl", "DRB.UEThpUl", "RRU.PrbTotUl"]

UNIDADES = {
    "DRB.RlcSduDelayDl": "us",
    "DRB.UEThpUl": "kbps",
    "RRU.PrbTotUl": "%",
}

ORDEM_FASES = ["baseline", "stress", "recovery"]

SCORE_THRESHOLD = 3.5          # limiar por feature (model.json)
MIN_ANOMALOUS_FEATURES = 2     # nº mínimo de features em concordância (model.json)
MAD_FLOOR = 1.0                # piso de escala, evita divisão por zero (model.json)
ESCALA_MAD = 1.4826            # MAD -> desvio-padrão robusto sob normalidade
ISC_CAP = 10.0                 # saturação do ISC, em múltiplos do limiar
JANELA = 5                     # tamanho da janela de decisão (decision.json)


def caminho_db(base: Path | str | None = None) -> Path:
    """Caminho do SQLite da amostra, relativo a code/notebooks/ ou a code/."""
    aqui = Path(base) if base is not None else Path.cwd()
    for candidato in (
        aqui / "datasets" / "kpm-ue-tp-sample" / "kpm.sqlite",
        aqui / ".." / "datasets" / "kpm-ue-tp-sample" / "kpm.sqlite",
        aqui / "code" / "datasets" / "kpm-ue-tp-sample" / "kpm.sqlite",
    ):
        if candidato.is_file():
            return candidato.resolve()
    raise FileNotFoundError(f"kpm.sqlite não encontrado a partir de {aqui.resolve()}")


# --------------------------------------------------------------------------
# Extração
# --------------------------------------------------------------------------

def carregar_amostras(db: Path | str) -> pd.DataFrame:
    """Lê kpm_samples e expande payload_json em uma coluna por feature."""
    con = sqlite3.connect(str(db))
    try:
        bruto = pd.read_sql(
            """
            SELECT id, run_id, phase, sample_index, ingested_at, source_path, payload_json
            FROM kpm_samples
            ORDER BY phase, sample_index
            """,
            con,
        )
    finally:
        con.close()

    metricas = bruto["payload_json"].apply(
        lambda p: pd.Series({f: json.loads(p).get(f) for f in FEATURES})
    )
    df = bruto.drop(columns=["payload_json"]).join(metricas)
    df[FEATURES] = df[FEATURES].astype("float64")
    df["phase"] = df["phase"].astype(
        pd.CategoricalDtype(ORDEM_FASES, ordered=True)
    )
    return df.sort_values(["phase", "sample_index"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Qualidade — os sete achados, calculados e não apenas afirmados
# --------------------------------------------------------------------------

def relatorio_qc(df: pd.DataFrame) -> dict:
    """Controle de qualidade da amostra. Cada chave sustenta uma frase do README."""
    delay = "DRB.RlcSduDelayDl"
    chaves = ["phase", "sample_index"] + FEATURES

    zeros_delay = (
        df.assign(zero=df[delay].eq(0))
        .groupby("phase", observed=True)["zero"]
        .agg(["sum", "count"])
    )

    duplicatas = (
        df.groupby(["phase"] + FEATURES, observed=True)
        .size()
        .reset_index(name="repeticoes")
        .query("repeticoes > 1")
        .sort_values("repeticoes", ascending=False)
    )

    return {
        "linhas": int(len(df)),
        "runs": sorted(df["run_id"].unique().tolist()),
        "amostras_por_fase": df["phase"].value_counts().reindex(ORDEM_FASES).to_dict(),
        # 1. sem eixo de tempo real
        "timestamps_distintos": int(df["ingested_at"].nunique()),
        # 2. delay zero = ausência disfarçada
        "delay_zero_por_fase": {
            fase: {"zeros": int(linha["sum"]), "total": int(linha["count"])}
            for fase, linha in zeros_delay.iterrows()
        },
        # 3. duplicatas exatas
        "maior_repeticao_de_payload": (
            int(duplicatas["repeticoes"].max()) if len(duplicatas) else 0
        ),
        "linhas_duplicadas": int((duplicatas["repeticoes"] - 1).sum()) if len(duplicatas) else 0,
        # 5. coluna documentada mas ausente
        "fracao_nula": df[FEATURES].isna().mean().round(4).to_dict(),
        "DRB.UEThpDl_presente": False,
        # 6. um único UE
        "coluna_ue_id_presente": "ue_id" in df.columns,
        # 7. desbalanceamento
        "fracao_stress": round(float(df["phase"].eq("stress").mean()), 4),
        "colunas": chaves,
        "gerado_em": datetime.now(timezone.utc).isoformat(),
    }


# --------------------------------------------------------------------------
# Treino e escoragem
# --------------------------------------------------------------------------

def treinar(baseline: pd.DataFrame, tratar_delay_zero: bool = False) -> dict:
    """Treina o baseline robusto (mediana + MAD) sobre a fase calma.

    tratar_delay_zero=False  -> variante V1, idêntica ao model.json do docente.
    tratar_delay_zero=True   -> variante V2, com a correção de qualidade do grupo:
                                DRB.RlcSduDelayDl == 0 é ausência, não medida.
    """
    features = {}
    for f in FEATURES:
        valores = baseline[f].dropna()
        if tratar_delay_zero and f == "DRB.RlcSduDelayDl":
            valores = valores[valores > 0]
        valores = valores.tolist()
        mediana = statistics.median(valores)
        mad = statistics.median([abs(v - mediana) for v in valores])
        features[f] = {
            "median": mediana,
            "mad": mad,
            "min": min(valores),
            "max": max(valores),
            "n": len(valores),
            "escala": max(mad * ESCALA_MAD, MAD_FLOOR),
        }
    return {
        "algorithm": "robust-baseline-mad",
        "features": features,
        "score_threshold": SCORE_THRESHOLD,
        "min_anomalous_features": MIN_ANOMALOUS_FEATURES,
        "mad_floor": MAD_FLOOR,
        "tratar_delay_zero_como_nulo": tratar_delay_zero,
        "sample_count": int(len(baseline)),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }


def escorar(amostra: dict, modelo: dict) -> dict:
    """Escore robusto de uma amostra. Devolve escores, features anômalas, decisão e ISC."""
    escores = {}
    for f, params in modelo["features"].items():
        valor = amostra.get(f)
        if valor is None or pd.isna(valor):
            continue
        if modelo["tratar_delay_zero_como_nulo"] and f == "DRB.RlcSduDelayDl" and valor == 0:
            continue  # métrica não reportada — não escoramos ausência
        escores[f] = abs(float(valor) - params["median"]) / params["escala"]

    anomalas = [f for f, s in escores.items() if s >= modelo["score_threshold"]]
    isc = (
        statistics.mean(
            min(s / modelo["score_threshold"], ISC_CAP) for s in escores.values()
        )
        if escores
        else 0.0
    )
    return {
        "scores": escores,
        "anomalous_features": anomalas,
        "decision": (
            "apply" if len(anomalas) >= modelo["min_anomalous_features"] else "observe"
        ),
        "isc": isc,
        "sample": {f: amostra.get(f) for f in FEATURES},
    }


def escorar_df(df: pd.DataFrame, modelo: dict) -> pd.DataFrame:
    """Aplica escorar() linha a linha e devolve o DataFrame com as colunas de saída."""
    saidas = [escorar(linha, modelo) for linha in df[FEATURES].to_dict("records")]
    fora = df.copy()
    for f in FEATURES:
        fora[f"escore.{f}"] = [s["scores"].get(f) for s in saidas]
        fora[f"anomala.{f}"] = [f in s["anomalous_features"] for s in saidas]
    fora["n_features_anomalas"] = [len(s["anomalous_features"]) for s in saidas]
    fora["isc"] = [s["isc"] for s in saidas]
    fora["anomala"] = [s["decision"] == "apply" for s in saidas]
    return fora


# --------------------------------------------------------------------------
# Indicadores do grupo
# --------------------------------------------------------------------------

def kpis_por_fase(escorado: pd.DataFrame) -> pd.DataFrame:
    """KPI 1 (TAA, %) e KPI 2 (ISC, adimensional) agregados por fase."""
    g = escorado.groupby("phase", observed=True)
    kpis = pd.DataFrame(
        {
            "n": g.size(),
            "n_anomalas": g["anomala"].sum(),
            "TAA_pct": (g["anomala"].mean() * 100).round(1),
            "ISC_mediana": g["isc"].median().round(2),
            "ISC_medio": g["isc"].mean().round(2),
            "ISC_max": g["isc"].max().round(2),
        }
    )
    for f in FEATURES:
        kpis[f"flags.{f}"] = g[f"anomala.{f}"].sum()
    return kpis.reindex(ORDEM_FASES)


# --------------------------------------------------------------------------
# Decisão e política A1 (dry-run)
# --------------------------------------------------------------------------

def decidir_janela(escorado: pd.DataFrame, janela: int = JANELA) -> dict:
    """Voto majoritário nas últimas `janela` amostras — mecânica do lab."""
    ultimas = escorado.tail(janela)
    votos = int(ultimas["anomala"].sum())
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "window_size": int(len(ultimas)),
        "apply_votes": votos,
        "decision": "apply" if votos > len(ultimas) / 2 else "observe",
        "latest": {
            "phase": str(ultimas.iloc[-1]["phase"]),
            "sample_index": int(ultimas.iloc[-1]["sample_index"]),
            "sample": {f: float(ultimas.iloc[-1][f]) for f in FEATURES},
            "scores": {
                f: (None if pd.isna(v) else round(float(v), 2))
                for f in FEATURES
                for v in [ultimas.iloc[-1][f"escore.{f}"]]
            },
            "isc": round(float(ultimas.iloc[-1]["isc"]), 2),
            "anomalous_features": [
                f for f in FEATURES if bool(ultimas.iloc[-1][f"anomala.{f}"])
            ],
        },
    }


def construir_politica(avaliacao: dict, modelo: dict) -> dict | None:
    """Política A1 candidata, no formato do lab. Dry-run: nada é enviado ao RIC."""
    if avaliacao["decision"] != "apply":
        return None
    sufixo = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return {
        "ric_id": "ric-oran",
        "policy_id": f"g2-load-anomaly-{sufixo}",
        "service_id": "grupo-01-g2-rapp",
        "policytype_id": "1",
        "policy_data": {
            "scope": {"ueId": "ue-any", "qosId": "qos-lab"},
            "qosObjectives": {"priorityLevel": 10},
        },
        "actuation": {"mode": "dry-run", "real": {}},
        "lab_context": {
            "intencao": "reduzir congestionamento UL",
            "gatilho": (
                f"{avaliacao['apply_votes']}/{avaliacao['window_size']} amostras da janela "
                f"com >= {modelo['min_anomalous_features']} features anômalas"
            ),
            "anomalous_features": avaliacao["latest"]["anomalous_features"],
            "isc_ultima_amostra": avaliacao["latest"]["isc"],
            "aviso": (
                "Execução simulada. Nenhuma requisição foi enviada ao Near-RT RIC "
                "e nenhum efeito físico na RAN é alegado."
            ),
        },
    }


# --------------------------------------------------------------------------
# Conferência contra os artefatos do docente
# --------------------------------------------------------------------------

def conferir_com_docente(modelo: dict, pasta_amostra: Path | str) -> pd.DataFrame:
    """Compara o modelo V1 treinado aqui com o model.json do lab, feature a feature.

    Serve de prova de reprodutibilidade: se as medianas e MADs baterem, o nosso
    detector é o mesmo do docente e as divergências posteriores são deliberadas.
    """
    oficial = json.loads((Path(pasta_amostra) / "model.json").read_text(encoding="utf-8"))
    linhas = []
    for f in FEATURES:
        nosso, deles = modelo["features"][f], oficial["features"][f]
        linhas.append(
            {
                "feature": f,
                "mediana_nossa": nosso["median"],
                "mediana_docente": deles["median"],
                "mad_nosso": nosso["mad"],
                "mad_docente": deles["mad"],
                "confere": (
                    nosso["median"] == deles["median"] and nosso["mad"] == deles["mad"]
                ),
            }
        )
    return pd.DataFrame(linhas)


def conferir_escores_docente(modelo: dict, pasta_amostra: Path | str) -> pd.DataFrame:
    """Reescora a amostra registrada em decision.json e compara com os escores do lab."""
    oficial = json.loads((Path(pasta_amostra) / "decision.json").read_text(encoding="utf-8"))
    ultima = oficial["evaluation"]["latest"]
    nosso = escorar(ultima["sample"], modelo)
    return pd.DataFrame(
        [
            {
                "feature": f,
                "valor": ultima["sample"][f],
                "escore_nosso": round(nosso["scores"][f], 2),
                "escore_docente": round(ultima["scores"][f], 2),
                "confere": abs(nosso["scores"][f] - ultima["scores"][f]) < 0.01,
            }
            for f in FEATURES
        ]
    )


def salvar_json(obj, caminho: Path | str) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    return caminho
