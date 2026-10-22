# DeliveryDispatch

Encontrar entregadores próximos a um restaurante com baixa latência exige organizar posições
geográficas e reduzir o espaço de busca sem perder precisão. O DeliveryDispatch está sendo
construído para explorar esse problema em Belo Horizonte, combinando Geohash, Trie compacta,
simulação espacial e geometria viária.

Além de avançar a solução, o desenvolvimento exercita estruturas de dados, algoritmos
geoespaciais, integração com serviços externos e testes automatizados.

## Visão geral

O fluxo implementado atualmente:

- prepara e geocodifica uma base de bares e restaurantes;
- gera uma frota sintética distribuída ao redor desses estabelecimentos;
- ajusta as posições dos entregadores à malha viária do OpenStreetMap;
- converte coordenadas em Geohashes;
- organiza estabelecimentos e entregadores em índices baseados em Trie compacta;
- pré-seleciona entregadores pelas células Geohash do restaurante e suas adjacentes;
- filtra os candidatos por distância de Haversine e destaca apenas os que estão no raio;
- oferece um painel interativo para pesquisar restaurantes e gerar a frota simulada.

## Requisitos

- Python 3.12 ou superior;
- conexão com a internet caso a base processada ou a malha viária ainda não estejam
  disponíveis localmente.

## Instalação e execução

No Windows, execute os comandos a partir da raiz do repositório:

```powershell
.\scripts\config.bat
.\scripts\run.bat
```

Abra `http://127.0.0.1:8050` no navegador. Na interface, pesquise um restaurante pelo nome
ou endereço, defina o raio de busca em quilômetros, informe a quantidade `N`
e selecione **Gerar entregadores**. Cada geração substitui a frota anterior no mapa. Ao selecionar um
restaurante, os entregadores encontrados no raio ficam verdes e os demais permanecem cinza.
Os restaurantes não selecionados ficam cinza, enquanto o restaurante selecionado é destacado em
laranja. Restaurantes usam um símbolo de alimentação, enquanto entregadores usam um símbolo de
duas rodas.

A geração da frota acontece exclusivamente no painel: o comando de execução não aceita uma
quantidade de entregadores como argumento.

Para consultar as demais opções:

```powershell
.\scripts\run.bat --help
```

<details>
<summary>Linux e macOS</summary>

```bash
python -m venv .venv
source .venv/bin/activate
python scripts/tasks.py setup
python scripts/tasks.py run
```

</details>

## Dados e cache

A base enriquecida com coordenadas fica em
`data/processed/bares_geocodificados.csv`. As respostas de geocodificação são armazenadas em
`data/cache/` para evitar consultas repetidas. A malha viária pronta para uso fica em
`data/processed/belo_horizonte_drive.graphml`, permitindo distribuí-la junto ao projeto.

A opção `--rebuild-processed` recria a base processada. Essa operação pode exigir milhares de
consultas e deve respeitar a
[política de uso do Nominatim](https://operations.osmfoundation.org/policies/nominatim/).

Na primeira geração da frota, a aplicação também pode baixar a malha viária de Belo Horizonte.
As gerações seguintes reutilizam o arquivo salvo em `data/processed/`.

Os dados geográficos utilizados são fornecidos por
[OpenStreetMap](https://www.openstreetmap.org/copyright) contributors.

## Testes

No Windows:

```powershell
.\scripts\run_tests.bat
```

Em outros ambientes:

```bash
python scripts/tasks.py test
```

## Estrutura

- `src/delivery_dispatch/`: implementação da aplicação;
- `data/`: bases original, processada e caches locais;
- `tests/`: testes automatizados;
- `experiments/`: cenários e resultados experimentais;
- `docs/`: relatório e documentação.

## Relatório

A descrição completa do problema, as decisões de implementação, a análise dos algoritmos e
os resultados experimentais ficam concentrados no relatório:

- [Fonte em LaTeX](docs/report.tex)
- [Baixar relatório em PDF](https://github.com/ChrystianMelo/DeliveryDispatch/releases/download/report/report.pdf)
