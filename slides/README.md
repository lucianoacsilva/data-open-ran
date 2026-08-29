# Apresentação — Aula 06

[`apresentacao-g2.pptx`](apresentacao-g2.pptx) — 12 slides, 16:9.

Fontes Segoe UI e Consolas (padrão do Windows, nada a instalar). As **notas do
apresentador** estão nos campos nativos: aparecem no Modo de Exibição do Apresentador
e em *Exibir → Anotações*.

Para o PDF do entregável: *Arquivo → Exportar → Criar PDF*.
Para ensaiar: *Apresentação de Slides → Ensaiar Tempos*.

## Sequência

| # | Slide |
|---|-------|
| 1 | Capa |
| 2 | Objetivo e fonte de dados |
| 3 | Achados de qualidade dos dados |
| 4 | Método de detecção |
| 5 | Definição dos indicadores |
| 6 | Resultados por fase |
| 7 | Severidade ao longo do experimento |
| 8 | Efeito da correção de qualidade |
| 9 | Erros do detector |
| 10 | Decisão e política A1 em execução simulada |
| 11 | Limitações |
| 12 | Conclusões |

A divisão dos blocos entre os integrantes **não está nos slides**, para não engessar a
apresentação. Ela permanece registrada na seção 9 do [README do pacote](../README.md),
que é o que a defesa individual exige.

## Figuras

`figuras/` contém as três imagens usadas nos slides, geradas sem título embutido — o
título fica no slide. São geradas por `_build_figuras_deck.py`, a partir do mesmo
`g2_lib.py` dos notebooks.

Os gráficos em `../figures/` são os do registro da análise (com título e legenda
próprios) e continuam sendo a referência do README e dos notebooks.

## Números a fixar antes da defesa

- 100 amostras: 20 baseline, 60 stress, 20 recovery; uma execução, um UE.
- Limiar 3,5 por métrica; mínimo de 2 métricas em concordância; janela de 5 amostras.
- TAA: 0 % em baseline, 98,3 % em stress, 5 % em recovery (variante V2).
- ISC médio: 0,04 / 6,61 / 0,33.
- Sem a regra de duas métricas, a TAA de baseline seria 45 %.
- Um único acionamento da política em 100 amostras.

Encerrar com a frase de execução simulada: nenhuma requisição foi enviada ao Near-RT RIC
e nenhum efeito físico na RAN é alegado.
