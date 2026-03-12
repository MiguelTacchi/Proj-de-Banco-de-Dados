# Proj-de-Banco-de-Dados
Trabalho de AV1 - SLIDE https://www.canva.com/design/DAHDsVoCfT0/nqJKSAv-IF7HUiF41sfJmA/edit?utm_content=DAHDsVoCfT0&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton
# Índice Hash Estático – Simulação de Banco de Dados

Este projeto implementa uma **simulação de um índice hash estático**, utilizado em sistemas de banco de dados para acelerar a busca por registros. A aplicação foi desenvolvida em **Python** e possui **interface gráfica (Tkinter)** para visualizar as estruturas de dados e o funcionamento do índice.

## Objetivo

Demonstrar como funciona o processo de:

* Armazenamento de registros em **páginas**
* Construção de um **índice hash estático**
* Busca de registros utilizando **índice**
* Busca utilizando **table scan**
* Comparação de desempenho entre os dois métodos

## Funcionamento do Sistema

### 1. Carga de Dados

O programa lê um arquivo `.txt` contendo palavras (uma por linha).
Cada palavra é considerada uma **chave única** e armazenada em memória.

Dataset utilizado:
https://github.com/dwyl/english-words

### 2. Paginação da Tabela

Os registros são divididos em **páginas**, simulando a forma como bancos de dados armazenam dados em disco.
O **tamanho da página** é definido pelo usuário.

### 3. Construção do Índice Hash

Após a paginação, o sistema constrói um **índice hash estático**.

Para cada registro:

1. A chave passa por uma **função hash**
2. O resultado indica o **bucket** correspondente
3. A chave e o endereço da página são armazenados no bucket

O número de buckets segue a regra:

```
NB > NR / FR
```

Onde:

* **NB** = número de buckets
* **NR** = número de registros
* **FR** = capacidade do bucket

### 4. Tratamento de Colisões

Caso dois registros sejam mapeados para o mesmo bucket, ocorre **colisão**.

A resolução é feita através de **páginas de overflow**, que armazenam registros extras quando o bucket principal está cheio.

### 5. Busca de Registros

#### Busca com Índice

1. O usuário digita uma chave de busca
2. A função hash calcula o bucket
3. O sistema localiza a página correspondente

#### Table Scan

O sistema percorre **todas as páginas da tabela**, verificando registro por registro até encontrar a chave.

## Estatísticas Geradas

O sistema também calcula e exibe:

* Taxa de **colisões (%)**
* Taxa de **overflow (%)**
* **Custo da busca** (acessos a páginas)
* **Custo do table scan**
* **Diferença de tempo** entre busca com índice e table scan

## Interface Gráfica

A interface permite:

* Carregar arquivo de dados
* Definir tamanho da página
* Construir o índice hash
* Buscar registros
* Executar table scan
* Visualizar páginas e buckets
* Exibir estatísticas de desempenho

## Tecnologias Utilizadas

* Python
* Tkinter (interface gráfica)

## Conclusão

O projeto demonstra na prática como **índices hash** são utilizados para otimizar buscas em grandes volumes de dados, reduzindo significativamente o número de acessos às páginas quando comparado ao **table scan**.
