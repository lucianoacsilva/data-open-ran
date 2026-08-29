# Grupo 1 — Tema **G2: Anomalia de carga**

**Disciplina 9 · Análise de Dados em Redes de Telecom — CESAR School**
Charles Xavier · Felipe Favilla · Thiago Coelho · Luciano Campagnoli

> **Pergunta do tema.** Em que momentos a rede sai do comportamento “normal” de forma
> **sustentada** — e não num pico isolado?

Pipeline reproduzível sobre telemetria KPM/E2 da trilha offline do laboratório
`oai-cn-gnb-nonrt-nearrt`, com dois indicadores formais, quatro visualizações, decisão
com política A1 em **execução simulada (dry-run)** e limitações declaradas.

### Por onde começar

| Quero… | Abrir |
|--------|-------|
| **Ver o pipeline rodando, sem instalar nada** | [`simulador-notebooks.html`](simulador-notebooks.html) — reproduz os três notebooks célula a célula, com as saídas reais. Duplo clique, qualquer navegador. |
| Ver a apresentação | [`slides/apresentacao-g2.pdf`](slides/apresentacao-g2.pdf) |
| Executar de verdade | [Como reproduzir](#2-como-reproduzir) → `code/notebooks/`, na ordem 01 → 02 → 03 |
| Conferir os números | [Resultados](#5-resultados) · [`derived/kpi_por_fase.csv`](derived/kpi_por_fase.csv) |
| Ler o código | [`code/g2_lib.py`](code/g2_lib.py) — toda a lógica está aqui |
| Ver os checkpoints | [`docs/checkpoint1.md`](docs/checkpoint1.md) · [`docs/checkpoint2.md`](docs/checkpoint2.md) — também em PDF na mesma pasta |

---

## 1. Origem dos dados

| | |
|---|---|
| **Fonte (obrigatória)** | `code/datasets/kpm-ue-tp-sample/kpm.sqlite` |
| **Espelho bronze** | `code/datasets/kpm-ue-tp-sample/kpm.jsonl` (mesmos pontos; não reprocessado) |
| **Run** | `ue-tp-20260804-174422`, caso `ue-tp-load-anomaly` |
| **Lab de origem** | OAI `nr-softmodem` em **RFSIM** + agente E2 + **FlexRIC**; xApp assina E2SM-KPM Style 4 e grava as *Indications* |
| **Volume** | 100 amostras · 3 métricas · 3 fases (`baseline` 20 · `stress` 60 · `recovery` 20) |
| **Timezone** | Todos os `ingested_at` em **UTC** (sufixo `+00:00`) |

Como abrir:

```python
import sqlite3, pandas as pd
con = sqlite3.connect("code/datasets/kpm-ue-tp-sample/kpm.sqlite")
pd.read_sql("SELECT phase, sample_index, payload_json FROM kpm_samples LIMIT 5", con)
```

As métricas ficam serializadas em `payload_json`; `g2_lib.carregar_amostras()` faz o
parse e a tipagem.

| Métrica | Unidade | Significado |
|---------|---------|-------------|
| `RRU.PrbTotUl` | % | Ocupação de PRB no uplink |
| `DRB.UEThpUl` | kbps | Vazão do UE no uplink |
| `DRB.RlcSduDelayDl` | µs | Atraso de SDU RLC no downlink |

**A fonte não é alterada.** Todo tratamento acontece a jusante, em código, e é auditável.

---

## 2. Como reproduzir

Testado com **Python 3.12**, `pandas 3.0.5`, `matplotlib 3.11.1`.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

jupyter lab code/notebooks/         # e executar na ordem 01 → 02 → 03
```

Ou sem abrir o Jupyter:

```bash
cd code/notebooks
jupyter nbconvert --to notebook --execute --inplace 01_etl_qc.ipynb 02_kpis_g2.ipynb 03_decisao_a1.ipynb
```

| Notebook | O que faz |
|----------|-----------|
| `code/notebooks/01_etl_qc.ipynb` | Ingestão, tipagem, controle de qualidade, export da camada tratada |
| `code/notebooks/02_kpis_g2.ipynb` | Escore MAD, conferência com os artefatos do docente, os 2 indicadores, plots P1–P4 |
| `code/notebooks/03_decisao_a1.ipynb` | Janela de decisão, voto majoritário, `decision_g1.json`, política A1 em dry-run |

`code/notebooks/checkpoint1/` guarda os notebooks do Checkpoint 1 — os notebooks oficiais
do docente, executados, que serviram de ponto de partida. Não fazem parte da entrega final
e têm suas próprias dependências em `code/notebooks/requirements.txt`. As saídas deles
ficam em `code/datasets/kpm-ue-tp-sample/derived/`; as da entrega, em `derived/` na raiz.

Toda a lógica está em **`code/g2_lib.py`**; os notebooks apenas chamam, exibem e plotam.

### Sem instalar nada

[`simulador-notebooks.html`](simulador-notebooks.html) reproduz os três notebooks célula a
célula, com as **saídas reais** capturadas da execução — tabelas, textos e gráficos. Abrir
com duplo clique em qualquer navegador; não requer Python nem Jupyter. Serve para revisar
o pipeline, para quem não tem o ambiente montado e para demonstrar a análise sem depender
de execução ao vivo.

**Não é necessário** subir o laboratório E2 (Docker / FlexRIC / O-RAN SC): a fonte
avaliativa é a trilha offline, versionada neste repositório.

### Saídas geradas

```
derived/kpm_features.csv     tabela tipada, 100 linhas
derived/etl_qc.json          relatório de qualidade
derived/kpi_por_fase.csv     TAA e ISC por fase, V1 e V2
derived/decision_g1.json     decisão + política A1 (dry-run)
figures/p1..p4_*.png         as quatro visualizações
```

### Apresentação

`slides/apresentacao-g2.pdf` — deck de 12 slides apresentado na Aula 06.
`slides/apresentacao-g2.pptx` — mesma apresentação em formato editável, com as notas do
apresentador nos campos nativos do PowerPoint.

---

## 3. Qualidade dos dados — sete achados

Calculados em `01_etl_qc.ipynb`, não apenas afirmados. Definem o que é honesto concluir.

| # | Achado | Efeito na análise |
|---|--------|-------------------|
| 1 | **Não há timestamp por amostra** — 100 linhas, apenas **3** valores distintos de `ingested_at`, um por arquivo de fase | Nenhuma métrica em unidade de tempo é defensável; o eixo é `sample_index` |
| 2 | **`DRB.RlcSduDelayDl = 0` em 11/20** no baseline e 11/20 no recovery | Zero de atraso RLC não é plausível: é métrica **não reportada**. Motiva a variante V2 |
| 3 | **Duplicatas exatas** — a tupla `(0 ; 3,72 ; 2,0)` se repete 10× em cada fase calma | O baseline é menos informativo do que `n = 20` sugere |
| 4 | **MAD zero nas 3 features** do baseline | O piso de escala (1,0) assume o papel do desvio robusto; o escore vira **desvio absoluto na unidade nativa** e fica incomparável entre métricas — motiva a saturação do ISC |
| 5 | **`DRB.UEThpDl` documentado mas ausente** no dataset | Apenas 3 features disponíveis |
| 6 | **Não há `ue_id`** no payload — um único UE | Qualquer agregação “de célula” é didática, não estatística |
| 7 | **60 % das amostras são de stress** | Todo indicador é reportado **por fase**; uma taxa global ficaria inflada |

---

## 4. Os dois indicadores

### Escore base — MAD robusto

Reproduz o `ai_policy_pipeline.py` do laboratório, o que permite conferir nossos números
contra o `model.json` do docente:

```
escala_f     = max( MAD_f × 1,4826 ,  piso_f )        piso_f = 1,0
escore_f(x)  = | x_f − mediana_baseline_f | / escala_f

feature anômala  ⇔  escore_f ≥ 3,5
amostra anômala  ⇔  ao menos 2 das 3 features anômalas
```

A constante 1,4826 converte o MAD em estimativa robusta de desvio-padrão sob
normalidade. Duas variantes do mesmo modelo:

- **V1** — baseline usado como está. **Idêntico ao `model.json` do docente.**
- **V2** — `DRB.RlcSduDelayDl = 0` tratado como **ausência**, não como medida (achado 2).

### KPI 1 — Taxa de Amostras Anômalas (TAA)

```
TAA(fase) = 100 × n_amostras_anômalas(fase) / n_amostras(fase)
```

| | |
|---|---|
| **Unidade** | % de amostras |
| **Granularidade** | por fase, dentro de um `run_id` |
| **Fonte** | `kpm_samples.payload_json` + `kpm_samples.phase` |

Responde diretamente à pergunta do tema. Contrastada entre fases, mede ao mesmo tempo a
**sensibilidade** (stress) e a **taxa de falso alarme** (baseline e recovery).

### KPI 2 — Índice de Severidade de Carga (ISC)

```
ISC(amostra) = média_f [ min( escore_f / 3,5 , 10 ) ]
```

| | |
|---|---|
| **Unidade** | adimensional (múltiplos do limiar) |
| **Granularidade** | por amostra, agregado por fase (mediana, média, máximo) |
| **Fonte** | escores das 3 features |

Mede a **intensidade** do desvio, não só a contagem. Normalizado pelo limiar:
**ISC = 1,0 significa “exatamente no limiar”**.

**Por que saturar em 10.** Sem o teto, o escore de `DRB.UEThpUl` chega a **77 213**,
porque a escala degenerou para 1,0 kbps (achado 4). Uma média sem saturação vira um
termômetro só da vazão, em kbps, disfarçado de índice adimensional.

---

## 5. Resultados

| Fase | n | TAA V1 | TAA V2 | ISC médio V1 | ISC médio V2 | Flags isolados de atraso (V1 → V2) |
|------|---|--------|--------|--------------|--------------|-----------------------------------|
| `baseline` | 20 | 0,0 % | 0,0 % | 1,51 | **0,04** | 9 → 0 |
| `stress` | 60 | 100,0 % | 98,3 % | 9,91 | **6,61** | — |
| `recovery` | 20 | 5,0 % | 5,0 % | 1,76 | **0,33** | 9 → 2 |

### Conferência de reprodutibilidade

O notebook 02 **falha por `assert`** se a conferência não bater:

- Modelo V1 × `model.json` do docente: medianas e MADs **idênticos** nas 3 features.
- Escores da amostra registrada em `decision.json`: `154,88` · `77 212,84` · `97,00` —
  **idênticos**.

Logo, qualquer divergência entre V1 e V2 é **deliberada**, não um defeito de implementação.

### Os quatro insights

1. **O detector separa as fases sem ambiguidade.** 0 % contra 98,3 % de TAA, e ISC de
   0,04 contra 6,61 — mais de duas ordens de grandeza. A hipótese do lab se confirma: as
   KPMs E2 distinguem calmo de carregado.

2. **A regra “mínimo 2 features” é o que segura o falso alarme.** No baseline V1, nove
   amostras disparam a flag de atraso isoladamente e nenhuma vira decisão. Com a regra
   relaxada para 1 feature, a TAA de baseline saltaria de 0 % para **45 %**.

3. **A correção de qualidade elimina a causa raiz.** Em V2 a mediana de atraso do
   baseline sobe de 0 para 137 µs e a escala de 1,0 para 69,68: os nove flags espúrios
   por fase calma desaparecem e o ISC médio de baseline cai de 1,51 para 0,04.

4. **Sobram um falso negativo e um falso alarme, ambos com explicação física.** A amostra
   de stress não detectada tem vazão 15,16 kbps e PRB 2 % — é a rampa antes do tráfego
   subir. A amostra de recovery detectada tem pico de 172 Mbps — é a cauda do `iperf`
   drenando. Nenhum dos dois é ruído do modelo.

> **Observação honesta.** Em V2 o atraso deixa de disparar também durante o stress
> (60 flags → 0): com mediana 137 µs e escala 69,68, os ~159 µs da fase de carga ficam a
> menos de meio desvio. Isso **não muda a decisão** — vazão e PRB já bastam para a regra
> de duas features — mas mostra que, neste lab, **o atraso RLC não é um bom discriminador
> de carga**. Quem separa as fases é PRB e vazão.

### Visualizações

| Figura | Insight |
|--------|---------|
| `p1_isc_serie.png` | A anomalia é **sustentada** ao longo de 59 das 60 amostras de stress, não um transiente |
| `p2_taa_por_fase.png` | O sinal (TAA) é robusto nas duas variantes; a correção limpa o **ruído por baixo** |
| `p3_distribuicoes.png` | Só a vazão precisa de escala log — o desequilíbrio de unidades que motiva a saturação do ISC |
| `p4_matriz_features.png` | No stress, PRB e vazão disparam **juntos**; o atraso sozinho nunca basta |

---

## 6. Recomendação e política A1 (dry-run)

**Gatilho.** Quando o ISC ultrapassa 1,0 em pelo menos 3 das 5 amostras mais recentes
(janela de voto majoritário do lab) e as features em concordância incluem
`RRU.PrbTotUl`, o sinal é de **saturação de uplink sustentada** — não de um pico
transitório.

**Ação candidata.** Emitir uma política A1 de priorização para o escopo QoS afetado
(`policytype_id` 1, `scope` `{ueId: ue-any, qosId: qos-lab}`, `priorityLevel` 10),
sujeita a **validação humana** antes de qualquer aplicação real.

Varrendo a regra sobre as 100 amostras, a política seria acionada **uma única vez**, no
início da fase de stress, e **nenhuma vez** nas fases calmas. A cauda do `iperf` em
recovery dispara uma amostra isolada que a janela descarta — comportamento desejado num
laço de controle: não reagir a transiente.

Artefato gerado: `derived/decision_g1.json` (mesmo formato do `decision.json` do lab).

> ⚠️ **Execução simulada.** A política é gerada e registrada como artefato candidato.
> **Nenhuma requisição foi enviada ao Near-RT RIC e nenhum efeito físico na RAN é
> alegado.**

---

## 7. Limitações

- **RFSIM não é rede real.** Telemetria de simulação de rádio OAI, sem propagação,
  interferência ou mobilidade reais. Os valores absolutos não transferem para uma célula
  comercial.
- **Amostra curta e desbalanceada.** 100 amostras, um `run_id`, um único UE, 60 % em
  stress. Suficiente para demonstrar o método, não para caracterizar comportamento de rede.
- **Sem eixo de tempo real.** Três `ingested_at` para 100 amostras: nenhuma métrica em
  unidade de tempo é defensável. Duração é medida em amostras consecutivas.
- **Baseline degenerado.** MAD zero nas três features faz o piso de escala assumir o
  papel do desvio robusto — por isso o ISC precisa ser saturado.
- **Anomalia rotulada por construção.** As fases vêm do roteiro do experimento, não de
  rótulo independente. Verificamos concordância com o roteiro; não validamos contra
  verdade de campo.
- **Os indicadores não provam causa.** Dizem que a rede saiu do normal, não por quê. O
  ISC não é probabilidade, e é comparável entre fases do mesmo run, não entre runs.
- **Sem atuação na RAN.** A1 em dry-run. O lab não comprova O1/NETCONF no softmodem OAI
  monolítico, nem quota de PRB via E2SM-RC action 6.
- **O que o lab não mede.** Nada de core (N3/N6), transporte ou terminal. Uma degradação
  de UPF ou de fronthaul apareceria aqui como “anomalia de rádio” sem que possamos
  distinguir.

---

## 8. Ética, privacidade e licença

- **Telemetria sintética de laboratório** (OAI / RFSIM). **Não há dados pessoais**, nem
  identificador de assinante, IMSI ou localização — o payload contém apenas três
  contadores agregados de rádio.
- **Sem `ue_id`**: nenhuma reidentificação é possível a partir deste conjunto.
- Em rede real, KPM **por UE** seria dado sensível e exigiria minimização,
  pseudonimização e política de retenção explícita. Registramos isso como diferença
  relevante entre o lab e a operação.
- **Proveniência declarada**: run, caminho de origem e script gerador estão em
  `runs.notes` e em `kpm_samples.source_path`.
- **Uso acadêmico** neste módulo. Artefatos originais do docente
  (`kpm.sqlite`, `kpm.jsonl`, `model.json`, `decision.json`) redistribuídos sem
  modificação; o código deste repositório é do grupo.

---

## 9. Divisão de responsabilidades (defesa individual)

| Pessoa | Lidera | Critério da rubrica |
|--------|--------|---------------------|
| **Charles Xavier** | Origem dos dados e qualidade (seções 1, 3, 8) | Aquisição e qualidade — 2,0 |
| **Luciano Campagnoli** | ETL, `g2_lib.py` e reprodutibilidade (seção 2) | ETL e reprodutibilidade — 2,0 |
| **Thiago Coelho** | Definição e interpretação dos indicadores (seção 4) | KPIs/KQIs — 2,0 |
| **Felipe Favilla** | Análise, visualizações e decisão A1 (seções 5, 6) | Análise e recomendação — 2,0 |
| *Compartilhado* | Governança, limitações e apresentação (seção 7) | Governança e defesa — 2,0 |

---

## Referências

No repositório do docente
([`jakunzler/cesar-school-repo/data`](https://github.com/jakunzler/cesar-school-repo/tree/main/data)):

- `docs/briefing-projeto.md` · `docs/temas-grupos.md` — briefing e card do G2
- `docs/entregas-projeto-integrador.md` — entregáveis e rubrica
- `code/oai-cn-gnb-nonrt-nearrt/scripts/ai_policy_pipeline.py` — detector MAD de referência
- `docs/FASES_ORAN_LAB.md` — fases do laboratório

Bibliografia:
- TRIPATHI, N. D.; SHAH, V. K. *Fundamentals of O-RAN*. Wiley-IEEE Press, 2025.
- WONG, I. C. et al. (Eds.) *Open RAN: The Definitive Guide*. Wiley-IEEE Press, 2024.
