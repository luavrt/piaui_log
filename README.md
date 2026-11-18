# Piauí Log

Roteirizador de entregas para os 224 municípios do Piauí, com as rotas em mapa real,
tempo de viagem, custo em reais, economia e roteiro para o motorista.

## Como rodar

```
pip install -r requirements.txt
streamlit run app.py
```

Precisa de internet: as distâncias, os tempos e o traçado da rota vêm do OSRM.

## Três modos no app

- **Origem → destino pelo caminho** (padrão): escolhe a partida, o destino e o algoritmo. O app acha as cidades
  que ficam na estrada entre as duas (sede a até 5 km, em `caminho.py`) e o algoritmo ordena a rota.
- **Passar por cidades escolhidas**: escolhe as cidades (ou todos os 224 municípios), as partidas e,
  se quiser, a cidade final.
- **Importar planilha de entregas**: envia um CSV ou Excel com as colunas `cidade`, `cliente` e `peso_kg`
  (cliente e peso são opcionais; há um modelo para baixar no app). O app confere os nomes dos municípios
  e monta a rota da partida até as cidades da planilha.

## O que aparece para cada rota

- distância, tempo de viagem, custo estimado (combustível + outros custos por km), tempo total com paradas
  e chegada prevista (horário de saída e tempo de parada por cidade são ajustáveis);
- economia em km, reais e tempo contra a média de 500 rotas aleatórias, e a tabela dos três algoritmos;
- roteiro parada a parada, com horários e, no modo planilha, os clientes e o peso de cada cidade;
- exportação em Excel e PDF, links do Google Maps (rotas longas são divididas em partes) e do Waze (próxima parada).

Os valores de consumo (3 km/l), combustível (R$ 6,00/l) e parada (20 min) são exemplos: ajuste na barra lateral.

## Arquivos

- `municipios_pi.json`: os 224 municípios do Piauí com latitude e longitude (código IBGE 22).
  O app não busca mais cada cidade no Nominatim; só o `main.py` ainda usa o Nominatim.
- `app.py`: a interface (Streamlit + folium).
- `dados.py`: matrizes de distância e de tempo do OSRM, em blocos de 50 x 50 quando há mais de 100 cidades
  (o servidor público aceita 100 pontos por pedido), traçado da rota pelas estradas.
- `grafo.py`: grafo (km em `weight`, minutos em `tempo`) e `desenhar_mapa`, que desenha a rota no mapa.
- `algoritmos.py`: rota aleatória e vizinho mais próximo aceitam cidade final;
  `dois_opt_rapido` dá o mesmo resultado do `dois_opt`, mas calcula só a diferença de cada inversão
  (o `dois_opt` original continua no arquivo e é o usado pelo `main.py`).
- `logistica.py`: custo, cronograma, economia, links e exportação (Excel e PDF).
- `entregas.py`: leitura e validação da planilha de entregas.
- `caminho.py`: acha as cidades que ficam perto da estrada de uma rota.
