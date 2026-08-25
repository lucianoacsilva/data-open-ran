# data-open-ran
Projeto de aplicações de inteligência artificial para Open RAN - Disciplina Análise de Dados Telecom - CESAR SCHOOL

# Início

A pasta **notebooks** contém códigos Python com documentação no formato Markdown (**.md**) para análise de dados obtidos a partir da execução do laboratório canônico UERANSIM presente em https://github.com/jakunzler/cesar-school-repo/tree/main/data/code/oai-cn-gnb-nonrt-nearrt. Totalizando três arquivos, são listados abaixo com suas respectivas funções:

- **eda_kpm.ipynb:** Análise exploratória de dados (do inglês *Exploratory Data Analysis*), consistindo em observação inicial dos conjuntos de dados a partir de técnicas de análise estatística descritiva, como medidas de tendência central (média, mediana, moda) e quartis. Para esta tarefa, foi utilizada a biblioteca **Pandas** da linguagem Python, que gera *dataframes*, estruturas de dados com  capacidade de organização e recursos para as análises anteriormente descritas.
- **etl_kpm.ipynb:** pré-processamento dos dados iniciais do diretório *datasets* para prepará-los para modelos de aprendizado de máquina para apoio de decisões, presentes no *notebook* **inferencia_decisao.ipynb**
- **inferencia_decisao.ipynb:**

Para executar os *notebooks* de análise de dados presentes na pasta , deve-se instalar primeiro as dependências Pythons por eles utilizadas com o comando:

```bash
pip install -r requirements.txt
```

Concluída a instalação, deve-se executar os *notebooks** na sequência **eda_kpm.ipynb**, **etl_kpm.ipynb** e **inferencia_decisao.ipynb**. Cada um deles é dividido em células (pequenos pedaços de código ou documentação), podendo ser executadas todas automaticamente (apertando o botão ***Run all***) ou isoladamente ao selecionar uma delas e pressionar o botão de execução ao lado esquerdo (ou usando o atalho **Ctrl + Enter**).
